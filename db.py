#!/usr/bin/env python3
"""Доступ к SQLite: инициализация БД и CRUD для всех таблиц ChatList."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Путь к файлу БД в корне проекта
DB_PATH = Path(__file__).resolve().parent / "chatlist.db"


def get_connection() -> sqlite3.Connection:
    """Возвращает подключение к БД (без авто-коммита для явного контроля)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_prompts_created_at
                ON prompts(created_at);
            CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags);

            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_url TEXT NOT NULL,
                api_id TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_models_is_active
                ON models(is_active);

            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                prompt_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                response TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id),
                FOREIGN KEY (model_id) REFERENCES models(id)
            );
            CREATE INDEX IF NOT EXISTS idx_results_prompt_id
                ON results(prompt_id);
            CREATE INDEX IF NOT EXISTS idx_results_model_id
                ON results(model_id);
            CREATE INDEX IF NOT EXISTS idx_results_created_at
                ON results(created_at);

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
        """)
        conn.commit()
    finally:
        conn.close()


# --- prompts ---

def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def prompt_create(prompt: str, tags: str = "") -> int:
    """Создаёт промт. Возвращает id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO prompts (created_at, prompt, tags) VALUES (?, ?, ?)",
            (_now(), prompt, tags),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def prompt_get(prompt_id: int) -> Optional[dict[str, Any]]:
    """Возвращает один промт по id или None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, created_at, prompt, tags FROM prompts WHERE id = ?",
            (prompt_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def prompt_list() -> list[dict[str, Any]]:
    """Список всех промтов (последние сначала)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, created_at, prompt, tags FROM prompts "
            "ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def prompt_update(prompt_id: int, prompt: str, tags: str = "") -> bool:
    """Обновляет промт. Возвращает True, если строка обновлена."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE prompts SET prompt = ?, tags = ? WHERE id = ?",
            (prompt, tags, prompt_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def prompt_delete(prompt_id: int) -> bool:
    """Удаляет промт. Возвращает True, если строка удалена."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# --- models ---

def model_create(name: str, api_url: str, api_id: str, is_active: int = 1) -> int:
    """Создаёт запись модели. Возвращает id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO models (name, api_url, api_id, is_active) "
            "VALUES (?, ?, ?, ?)",
            (name, api_url, api_id, is_active),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def model_get(model_id: int) -> Optional[dict[str, Any]]:
    """Возвращает одну модель по id или None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, api_url, api_id, is_active FROM models "
            "WHERE id = ?",
            (model_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def model_list(active_only: bool = False) -> list[dict[str, Any]]:
    """Список моделей. Если active_only=True — только с is_active=1."""
    conn = get_connection()
    try:
        if active_only:
            rows = conn.execute(
                "SELECT id, name, api_url, api_id, is_active FROM models "
                "WHERE is_active = 1"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, api_url, api_id, is_active FROM models"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def model_update(
    model_id: int,
    name: Optional[str] = None,
    api_url: Optional[str] = None,
    api_id: Optional[str] = None,
    is_active: Optional[int] = None,
) -> bool:
    """Обновляет модель. Передавать только меняющиеся поля."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT name, api_url, api_id, is_active FROM models WHERE id = ?",
            (model_id,),
        ).fetchone()
        if not row:
            return False
        r = dict(row)
        if name is not None:
            r["name"] = name
        if api_url is not None:
            r["api_url"] = api_url
        if api_id is not None:
            r["api_id"] = api_id
        if is_active is not None:
            r["is_active"] = is_active
        cur = conn.execute(
            "UPDATE models SET name = ?, api_url = ?, api_id = ?, "
            "is_active = ? WHERE id = ?",
            (r["name"], r["api_url"], r["api_id"], r["is_active"], model_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def model_delete(model_id: int) -> bool:
    """Удаляет модель."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# --- results ---

def result_create(
    prompt_id: int,
    model_id: int,
    model_name: str,
    response: str,
) -> int:
    """Сохраняет результат. Возвращает id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO results (created_at, prompt_id, model_id, "
            "model_name, response) VALUES (?, ?, ?, ?, ?)",
            (_now(), prompt_id, model_id, model_name, response),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def result_get(result_id: int) -> Optional[dict[str, Any]]:
    """Возвращает один результат по id или None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, created_at, prompt_id, model_id, model_name, response "
            "FROM results WHERE id = ?",
            (result_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def result_list(
    prompt_id: Optional[int] = None,
    model_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Список результатов, опционально по prompt_id и/или model_id."""
    conn = get_connection()
    try:
        sql = (
            "SELECT id, created_at, prompt_id, model_id, model_name, response "
            "FROM results WHERE 1=1"
        )
        params: list[Any] = []
        if prompt_id is not None:
            sql += " AND prompt_id = ?"
            params.append(prompt_id)
        if model_id is not None:
            sql += " AND model_id = ?"
            params.append(model_id)
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def result_delete(result_id: int) -> bool:
    """Удаляет результат."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# --- settings ---

def setting_get(key: str) -> Optional[str]:
    """Возвращает значение настройки по ключу или None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def setting_set(key: str, value: str) -> None:
    """Устанавливает настройку (вставка или обновление)."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value),
        )
        conn.commit()
    finally:
        conn.close()


def setting_list() -> list[dict[str, Any]]:
    """Список всех настроек."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, key, value FROM settings ORDER BY key"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def setting_delete(key: str) -> bool:
    """Удаляет настройку по ключу."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
