#!/usr/bin/env python3
"""Логика моделей: активные модели и чтение API-ключей из окружения."""

import os
from typing import Any, Optional

from dotenv import load_dotenv

import db

# Подгружаем .env из корня проекта при импорте
load_dotenv()


def get_active_models() -> list[dict[str, Any]]:
    """Возвращает список активных моделей (is_active = 1) из БД."""
    return db.model_list(active_only=True)


def get_api_key(api_id: str) -> Optional[str]:
    """API-ключ из окружения по имени api_id. None если не задан."""
    value = os.getenv(api_id)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_model_with_key(model_id: int) -> Optional[dict[str, Any]]:
    """Модель по id с полем api_key из .env (или None)."""
    row = db.model_get(model_id)
    if not row:
        return None
    row = dict(row)
    row["api_key"] = get_api_key(row["api_id"])
    return row


def get_active_models_with_keys() -> list[dict[str, Any]]:
    """Активные модели с полем api_key из .env (или None)."""
    models = get_active_models()
    for m in models:
        m["api_key"] = get_api_key(m["api_id"])
    return models
