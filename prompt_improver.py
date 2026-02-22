#!/usr/bin/env python3
"""AI-ассистент для улучшения промтов: запрос к модели и парсинг ответа."""

import re
from typing import Any, Dict, List

import network


SYSTEM_PROMPT = """Ты помогаешь улучшать пользовательские промты для LLM.
Ответь строго в следующем формате (Markdown):

## Улучшенный промт
(одна улучшенная формулировка промта)

## Варианты переформулировки
1. (первый вариант)
2. (второй вариант)

Используй только эти два заголовка. Под каждым — сам промт или вариант."""


def parse_improvement_response(text: str) -> Dict[str, Any]:
    """
    Парсит ответ модели и извлекает улучшенный промт, варианты и по типам.
    Возвращает: {"improved": str, "alternatives": [str], "by_type": {"код": str, ...}}
    При неудачном разборе — весь текст в improved.
    """
    result = {
        "improved": "",
        "alternatives": [],
        "by_type": {},
    }
    if not (text or "").strip():
        return result

    text = text.strip()
    lines = text.split("\n")

    # Улучшенный промт: между "## Улучшенный промт" и следующим ##
    improved = _extract_section(lines, "## Улучшенный промт")
    result["improved"] = improved.strip() if improved else ""

    # Варианты переформулировки: только первые 2
    alt_section = _extract_section(lines, "## Варианты переформулировки")
    if alt_section:
        result["alternatives"] = _parse_numbered_list(alt_section)[:2]

    # Если ничего не распарсилось — весь ответ как улучшенный
    if not result["improved"] and not result["alternatives"]:
        result["improved"] = text
    return result


def _extract_section(lines: List[str], header: str) -> str:
    """Текст от строки с header до следующего ## или конца."""
    out = []
    found = False
    for line in lines:
        if line.strip().startswith(header):
            found = True
            continue
        if found:
            if line.strip().startswith("##"):
                break
            out.append(line)
    return "\n".join(out)


def _parse_numbered_list(text: str) -> List[str]:
    """Извлекает элементы нумерованного списка (1. ..., 2. ..., 3. ...)."""
    items = []
    for part in re.split(r"\n\s*\d+\.\s*", text):
        part = part.strip()
        if part:
            items.append(part)
    if not items and text.strip():
        items = [text.strip()]
    return items[:5]


def improve_prompt(
    prompt: str,
    model: Dict[str, Any],
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Отправляет промт на улучшение в одну модель. Возвращает структуру
    с полями improved, alternatives, by_type и при ошибке — error.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    out = network.send_messages_to_model(messages, model, timeout=timeout)
    if out.get("error"):
        return {
            "improved": "",
            "alternatives": [],
            "by_type": {},
            "error": out["error"],
        }
    response_text = out.get("response") or ""
    parsed = parse_improvement_response(response_text)
    parsed["error"] = None
    return parsed
