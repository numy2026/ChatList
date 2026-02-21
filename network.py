#!/usr/bin/env python3
"""Отправка промта в модели по API. Без записи в БД."""

import logging
from pathlib import Path

import requests
from typing import Any

# Лог запросов в файл
_LOG_DIR = Path(__file__).resolve().parent
_LOG_FILE = _LOG_DIR / "chatlist_requests.log"
_log = logging.getLogger("network")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _log.addHandler(h)

# Таймаут по умолчанию (секунды)
DEFAULT_TIMEOUT = 60

# Open Router: один endpoint для многих моделей (OpenAI, Anthropic и др.)
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def send_prompt_to_model(
    prompt: str,
    model: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    Отправляет один промт в одну модель (OpenAI-совместимый API).
    Поддерживается и Open Router: api_url=OPENROUTER_API_URL, api_id=ключ из .env,
    name=ид модели Open Router (например openai/gpt-4o).
    model: id, name, api_url, api_key.
    Возвращает: model_id, model_name, response, error (response при успехе).
    """
    model_id = model.get("id")
    model_name = model.get("name", "")
    api_url = model.get("api_url", "").strip()
    api_key = model.get("api_key")

    out = {
        "model_id": model_id,
        "model_name": model_name,
        "response": None,
        "error": None,
    }

    if not api_url:
        out["error"] = "Не задан api_url"
        return out
    if not api_key:
        out["error"] = "API-ключ не задан (проверьте .env и models.api_id)"
        return out

    _log.info("Запрос: модель=%s, длина промта=%s", model_name, len(prompt))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        r = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        out["error"] = "Таймаут запроса"
        return out
    except requests.exceptions.RequestException as e:
        out["error"] = str(e)
        return out

    if r.status_code >= 400:
        tail = r.text[:200] if r.text else ""
        out["error"] = f"HTTP {r.status_code}: {tail}"
        _log.warning("Ошибка %s: модель=%s %s", r.status_code, model_name, tail)
        return out

    try:
        data = r.json()
    except ValueError:
        out["error"] = "Ответ не JSON"
        return out

    # OpenAI-формат: choices[0].message.content
    choices = data.get("choices")
    if not choices or not isinstance(choices, list):
        out["error"] = "Неверный формат ответа (нет choices)"
        return out
    msg = choices[0].get("message") if choices else None
    if not msg or "content" not in msg:
        out["error"] = "Неверный формат ответа (нет message.content)"
        return out
    out["response"] = msg.get("content") or ""
    _log.info("Успех: модель=%s, длина ответа=%s", model_name, len(out["response"]))
    return out


def send_prompt_to_all_models(
    prompt: str,
    models: list[dict[str, Any]],
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """
    Отправляет промт во все модели. Возвращает список с полями
    model_id, model_name, response, error, selected=False.
    """
    results = []
    for model in models:
        one = send_prompt_to_model(prompt, model, timeout=timeout)
        one["selected"] = False
        results.append(one)
    return results
