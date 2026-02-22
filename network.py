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
OPENROUTER_MODEL_PREFIX = "https://openrouter.ai/"


def _extract_error_message(response: requests.Response) -> str:
    """Из ответа с ошибкой извлекает читаемое сообщение (в т.ч. из JSON)."""
    text = (response.text or "").strip()
    if not text:
        return f"HTTP {response.status_code}"
    try:
        data = response.json()
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return f"HTTP {response.status_code}: {err['message']}"
        if isinstance(err, str):
            return f"HTTP {response.status_code}: {err}"
    except ValueError:
        pass
    return f"HTTP {response.status_code}: {text[:500]}"


def _model_id_for_request(model_name: str, api_url: str) -> str:
    """
    В запрос в API передаётся только id модели (например mistralai/...).
    Если в поле name введён полный URL Open Router — убираем префикс.
    """
    name = (model_name or "").strip()
    if not name:
        return name
    url = (api_url or "").strip()
    if OPENROUTER_MODEL_PREFIX in url and name.startswith(
        OPENROUTER_MODEL_PREFIX
    ):
        name = name[len(OPENROUTER_MODEL_PREFIX) :].rstrip("/")
    return name


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

    model_for_api = _model_id_for_request(model_name, api_url)
    _log.info("Запрос: модель=%s, длина промта=%s", model_for_api, len(prompt))

    return _request_messages(
        api_url, api_key, model_for_api, model_id, model_name,
        [{"role": "user", "content": prompt}],
        timeout,
    )


def send_messages_to_model(
    messages: list,
    model: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    Отправляет список сообщений (system, user, …) в одну модель.
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
    Возвращает: model_id, model_name, response, error.
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
    model_for_api = _model_id_for_request(model_name, api_url)
    _log.info(
        "Запрос (messages): модель=%s, сообщений=%s",
        model_for_api, len(messages),
    )
    return _request_messages(
        api_url, api_key, model_for_api, model_id, model_name,
        messages,
        timeout,
    )


def _request_messages(
    api_url: str,
    api_key: str,
    model_for_api: str,
    model_id: Any,
    model_name: str,
    messages: list,
    timeout: int,
) -> dict[str, Any]:
    out = {
        "model_id": model_id,
        "model_name": model_name,
        "response": None,
        "error": None,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model_for_api, "messages": messages}
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
        err_msg = _extract_error_message(r)
        out["error"] = err_msg
        _log.warning(
            "Ошибка %s: модель=%s %s",
            r.status_code, model_name, err_msg,
        )
        return out

    try:
        data = r.json()
    except ValueError:
        out["error"] = "Ответ не JSON"
        return out

    choices = data.get("choices")
    if not choices or not isinstance(choices, list):
        out["error"] = "Неверный формат ответа (нет choices)"
        return out
    msg = choices[0].get("message") if choices else None
    if not msg or "content" not in msg:
        out["error"] = "Неверный формат ответа (нет message.content)"
        return out
    out["response"] = msg.get("content") or ""
    _log.info(
        "Успех: модель=%s, длина ответа=%s",
        model_name, len(out["response"]),
    )
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
