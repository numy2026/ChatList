#!/usr/bin/env python3
"""Временная таблица результатов в памяти (до нажатия «Сохранить»)."""

from typing import Any


class TempResultsTable:
    """
    Хранит результаты текущего запроса в памяти.
    Каждая строка: model_id, model_name, response, error, selected.
    При новом запросе таблицу очищают и заполняют заново.
    При «Сохранить» отмеченные строки передают в db.result_create.
    """

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def clear(self) -> None:
        """Полностью очистить временную таблицу."""
        self._rows.clear()

    def set_results(self, results: list[dict[str, Any]]) -> None:
        """
        Заменить содержимое новыми результатами (из network).
        Поля: model_id, model_name, response, error, selected.
        """
        self._rows = []
        for r in results:
            row = {
                "model_id": r.get("model_id"),
                "model_name": r.get("model_name", ""),
                "response": r.get("response") or "",
                "error": r.get("error"),
                "selected": r.get("selected", False),
            }
            self._rows.append(row)

    def get_rows(self) -> list[dict[str, Any]]:
        """Вернуть все строки (копии для отображения в GUI)."""
        return [dict(r) for r in self._rows]

    def set_selected(self, index: int, value: bool) -> None:
        """Установить флаг selected для строки по индексу."""
        if 0 <= index < len(self._rows):
            self._rows[index]["selected"] = value

    def set_selected_by_key(
        self, model_id: Any, response: str, value: bool
    ) -> None:
        """Установить selected по паре (model_id, response)."""
        for r in self._rows:
            if r.get("model_id") == model_id and (r.get("response") or "") == response:
                r["selected"] = value
                break

    def get_selected_rows(self) -> list[dict[str, Any]]:
        """Строки с selected=True (для записи в таблицу results)."""
        return [dict(r) for r in self._rows if r.get("selected")]

    def remove_saved(self, saved_rows: list[dict[str, Any]]) -> None:
        """
        Удалить строки, уже сохранённые в БД.
        saved_rows — список с model_id и response для сопоставления.
        """
        saved_set = {(r.get("model_id"), (r.get("response") or "")) for r in saved_rows}
        self._rows = [
            r for r in self._rows
            if (r.get("model_id"), r.get("response") or "") not in saved_set
        ]

    def __len__(self) -> int:
        return len(self._rows)
