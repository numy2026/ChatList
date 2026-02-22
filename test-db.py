#!/usr/bin/env python3
"""Просмотр SQLite: список таблиц, открытие с пагинацией и CRUD."""

import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def get_tables(conn: sqlite3.Connection) -> List[str]:
    """Список имён таблиц в БД."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [row[0] for row in cur.fetchall()]


def get_columns(conn: sqlite3.Connection, table: str) -> List[tuple]:
    """Колонки таблицы: (cid, name, type, notnull, default, pk)."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return cur.fetchall()


def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
    return cur.fetchone()[0]


def get_page(
    conn: sqlite3.Connection,
    table: str,
    columns: List[str],
    limit: int,
    offset: int,
) -> List[tuple]:
    """Одна страница строк. columns — имена колонок."""
    cols = ", ".join(f'[{c}]' for c in columns)
    cur = conn.execute(
        f"SELECT {cols} FROM [{table}] LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return cur.fetchall()


class TableViewDialog(QDialog):
    """Окно таблицы с пагинацией и CRUD."""

    PAGE_SIZE = 50

    def __init__(
        self,
        db_path: str,
        table_name: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.table_name = table_name
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.columns = [c[1] for c in get_columns(self.conn, table_name)]
        self.total_rows = get_row_count(self.conn, table_name)
        self.current_page = 0
        self.setWindowTitle(f"Таблица: {table_name}")
        self.setMinimumSize(700, 450)
        self.resize(850, 500)

        layout = QVBoxLayout(self)

        # Пагинация
        pagination = QHBoxLayout()
        self.page_label = QLabel()
        pagination.addWidget(self.page_label)
        btn_prev = QPushButton("← Назад")
        btn_prev.clicked.connect(self._prev_page)
        btn_next = QPushButton("Вперёд →")
        btn_next.clicked.connect(self._next_page)
        pagination.addWidget(btn_prev)
        pagination.addWidget(btn_next)
        pagination.addStretch()
        layout.addLayout(pagination)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # CRUD
        crud_row = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self._add_row)
        btn_edit = QPushButton("Изменить")
        btn_edit.clicked.connect(self._edit_row)
        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(self._delete_rows)
        crud_row.addWidget(btn_add)
        crud_row.addWidget(btn_edit)
        crud_row.addWidget(btn_delete)
        crud_row.addStretch()
        layout.addLayout(crud_row)

        self._load_page()

    def _total_pages(self) -> int:
        if self.total_rows == 0:
            return 1
        return (self.total_rows + self.PAGE_SIZE - 1) // self.PAGE_SIZE

    def _load_page(self) -> None:
        total_pages = self._total_pages()
        self.current_page = max(0, min(self.current_page, total_pages - 1))
        offset = self.current_page * self.PAGE_SIZE
        rows = get_page(
            self.conn,
            self.table_name,
            self.columns,
            self.PAGE_SIZE,
            offset,
        )
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(
                    i, j, QTableWidgetItem("" if val is None else str(val))
                )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.page_label.setText(
            f"Страница {self.current_page + 1} из {total_pages} "
            f"(всего строк: {self.total_rows})"
        )

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._load_page()

    def _next_page(self) -> None:
        if self.current_page < self._total_pages() - 1:
            self.current_page += 1
            self._load_page()

    def _add_row(self) -> None:
        dlg = RowEditDialog(
            self.columns,
            {},
            "Добавить строку",
            self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        data = dlg.get_data()
        cols = ", ".join(f"[{c}]" for c in data)
        placeholders = ", ".join("?" for _ in data)
        try:
            sql = (
                f"INSERT INTO [{self.table_name}] ({cols}) "
                f"VALUES ({placeholders})"
            )
            self.conn.execute(sql, list(data.values()))
            self.conn.commit()
            self.total_rows = get_row_count(self.conn, self.table_name)
            self._load_page()
            QMessageBox.information(self, "Добавить", "Строка добавлена.")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _edit_row(self) -> None:
        row_idx = self.table.currentRow()
        if row_idx < 0:
            QMessageBox.warning(
                self, "Изменить", "Выберите строку для редактирования."
            )
            return
        offset = self.current_page * self.PAGE_SIZE
        rows = get_page(
            self.conn,
            self.table_name,
            self.columns,
            self.PAGE_SIZE,
            offset,
        )
        if row_idx >= len(rows):
            return
        row = rows[row_idx]
        pk_info = get_columns(self.conn, self.table_name)
        pk_cols = [c[1] for c in pk_info if c[5]]
        data = {self.columns[j]: row[j] for j in range(len(self.columns))}
        dlg = RowEditDialog(
            self.columns,
            data,
            "Изменить строку",
            self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        new_data = dlg.get_data()
        if not pk_cols:
            QMessageBox.warning(
                self,
                "Изменить",
                "У таблицы нет первичного ключа, изменение отменено.",
            )
            return
        set_clause = ", ".join(f"[{c}]=?" for c in new_data)
        where_clause = " AND ".join(f"[{c}]=?" for c in pk_cols)
        params = list(new_data.values()) + [data[c] for c in pk_cols]
        try:
            sql = (
                f"UPDATE [{self.table_name}] SET {set_clause} "
                f"WHERE {where_clause}"
            )
            self.conn.execute(sql, params)
            self.conn.commit()
            self._load_page()
            QMessageBox.information(self, "Изменить", "Строка обновлена.")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _delete_rows(self) -> None:
        indexes = {ix.row() for ix in self.table.selectionModel().selectedRows()}
        if not indexes:
            QMessageBox.warning(
                self, "Удалить", "Выберите одну или несколько строк."
            )
            return
        if QMessageBox.question(
            self,
            "Удалить",
            f"Удалить выбранные строки ({len(indexes)})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        pk_info = get_columns(self.conn, self.table_name)
        pk_cols = [c[1] for c in pk_info if c[5]]
        if not pk_cols:
            QMessageBox.warning(
                self,
                "Удалить",
                "У таблицы нет первичного ключа, удаление отменено.",
            )
            return
        offset = self.current_page * self.PAGE_SIZE
        rows = get_page(
            self.conn,
            self.table_name,
            self.columns,
            self.PAGE_SIZE,
            offset,
        )
        deleted = 0
        try:
            for i in sorted(indexes, reverse=True):
                if i >= len(rows):
                    continue
                row = rows[i]
                where_clause = " AND ".join(f"[{c}]=?" for c in pk_cols)
                params = [row[self.columns.index(c)] for c in pk_cols]
                sql = (
                    f"DELETE FROM [{self.table_name}] WHERE {where_clause}"
                )
                self.conn.execute(sql, params)
                deleted += 1
            self.conn.commit()
            self.total_rows = get_row_count(self.conn, self.table_name)
            self._load_page()
            QMessageBox.information(
                self, "Удалить", f"Удалено строк: {deleted}."
            )
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def closeEvent(self, event) -> None:
        self.conn.close()
        super().closeEvent(event)


class RowEditDialog(QDialog):
    """Диалог редактирования одной строки (поля по колонкам)."""

    def __init__(
        self,
        columns: List[str],
        initial: dict,
        title: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.columns = columns
        self.edits = {}
        layout = QFormLayout(self)
        for col in columns:
            le = QLineEdit()
            le.setText("" if initial.get(col) is None else str(initial[col]))
            self.edits[col] = le
            layout.addRow(col, le)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addRow(bb)

    def get_data(self) -> dict:
        return {c: self.edits[c].text().strip() for c in self.columns}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("test-db: просмотр SQLite")
        self.setMinimumSize(400, 350)
        self.conn: Optional[sqlite3.Connection] = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("Файл базы данных SQLite"))
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Путь к .db или .sqlite…")
        path_row.addWidget(self.path_edit)
        btn_browse = QPushButton("Обзор…")
        btn_browse.clicked.connect(self._browse)
        path_row.addWidget(btn_browse)
        layout.addLayout(path_row)

        btn_load = QPushButton("Загрузить список таблиц")
        btn_load.clicked.connect(self._load_tables)
        layout.addWidget(btn_load)

        layout.addWidget(QLabel("Таблицы"))
        self.table_list = QListWidget()
        layout.addWidget(self.table_list)

        btn_open = QPushButton("Открыть")
        btn_open.clicked.connect(self._open_table)
        layout.addWidget(btn_open)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл SQLite",
            "",
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*)",
        )
        if path:
            self.path_edit.setText(path)

    def _load_tables(self) -> None:
        path = self.path_edit.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(
                self, "Ошибка", "Укажите существующий файл базы данных."
            )
            return
        if self.conn:
            self.conn.close()
            self.conn = None
        try:
            self.conn = sqlite3.connect(path)
            tables = get_tables(self.conn)
            self.conn.close()
            self.conn = None
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.table_list.clear()
        for t in tables:
            self.table_list.addItem(QListWidgetItem(t))
        if tables:
            QMessageBox.information(
                self,
                "Таблицы",
                f"Загружено таблиц: {len(tables)}.",
            )
        else:
            QMessageBox.warning(self, "Таблицы", "В базе нет таблиц.")

    def _open_table(self) -> None:
        path = self.path_edit.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(
                self, "Ошибка", "Укажите существующий файл базы данных."
            )
            return
        current = self.table_list.currentItem()
        if not current:
            QMessageBox.warning(
                self, "Открыть", "Выберите таблицу в списке."
            )
            return
        table_name = current.text()
        dlg = TableViewDialog(path, table_name, self)
        dlg.exec_()


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
