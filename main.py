#!/usr/bin/env python3
"""ChatList: отправка промта в несколько моделей, сравнение и сохранение результатов."""

import sys
from typing import Any, List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QAbstractItemView,
)

import db
import models as models_module
import network
from temp_results import TempResultsTable
from network import OPENROUTER_API_URL


# Диалог добавления модели
class AddModelDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить модель")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("openai/gpt-4o или имя модели")
        layout.addRow("Название (name):", self.name_edit)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(OPENROUTER_API_URL)
        self.url_edit.setText(OPENROUTER_API_URL)
        layout.addRow("API URL:", self.url_edit)
        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText("OPENROUTER_API_KEY")
        self.api_id_edit.setText("OPENROUTER_API_KEY")
        layout.addRow("Переменная ключа (api_id):", self.api_id_edit)
        self.active_cb = QCheckBox("Активна (участвует в запросах)")
        self.active_cb.setChecked(True)
        layout.addRow("", self.active_cb)
        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addRow(bb)

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "api_url": self.url_edit.text().strip(),
            "api_id": self.api_id_edit.text().strip(),
            "is_active": 1 if self.active_cb.isChecked() else 0,
        }


# Поток для отправки запросов без блокировки UI
class SendWorker(QThread):
    finished = pyqtSignal(list)  # list[dict]

    def __init__(self, prompt: str, model_list: List[dict]) -> None:
        super().__init__()
        self.prompt = prompt
        self.model_list = model_list

    def run(self) -> None:
        results = network.send_prompt_to_all_models(
            self.prompt, self.model_list
        )
        self.finished.emit(results)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        self.current_prompt_id: Optional[int] = None
        self.temp_results = TempResultsTable()
        self.send_worker: Optional[SendWorker] = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Промт ---
        layout.addWidget(QLabel("Промт"))
        prompt_row = QHBoxLayout()
        self.prompt_combo = QComboBox()
        self.prompt_combo.setMinimumWidth(200)
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_combo_changed)
        prompt_row.addWidget(self.prompt_combo)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите промт или выберите сохранённый...")
        self.prompt_edit.setMaximumHeight(100)
        prompt_row.addWidget(self.prompt_edit, 1)
        layout.addLayout(prompt_row)

        btn_row1 = QHBoxLayout()
        self.btn_save_prompt = QPushButton("Сохранить промт")
        self.btn_save_prompt.clicked.connect(self._on_save_prompt)
        self.btn_send = QPushButton("Отправить")
        self.btn_send.clicked.connect(self._on_send)
        btn_row1.addWidget(self.btn_save_prompt)
        btn_row1.addWidget(self.btn_send)
        btn_row1.addStretch()
        layout.addLayout(btn_row1)

        # --- Результаты ---
        layout.addWidget(QLabel("Результаты"))
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("По модели или ответу...")
        self.search_edit.textChanged.connect(self._refresh_results_table)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["", "Модель", "Ответ / Ошибка"])
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.results_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.results_table)

        btn_row2 = QHBoxLayout()
        self.btn_save_results = QPushButton("Сохранить выбранные")
        self.btn_save_results.clicked.connect(self._on_save_results)
        self.btn_export = QPushButton("Экспорт…")
        self.btn_export.clicked.connect(self._on_export)
        btn_row2.addWidget(self.btn_save_results)
        btn_row2.addWidget(self.btn_export)
        btn_row2.addStretch()
        layout.addLayout(btn_row2)

        # Меню
        menubar = self.menuBar()
        menu_models = menubar.addMenu("Модели")
        act_add = menu_models.addAction("Добавить модель…")
        act_add.triggered.connect(self._on_add_model)

        self._refresh_prompts_combo()
        self._refresh_results_table()

    def _refresh_prompts_combo(self) -> None:
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— Новый промт —", None)
        for p in db.prompt_list():
            label = (p["prompt"][:50] + "…") if len(p["prompt"]) > 50 else p["prompt"]
            self.prompt_combo.addItem(label, p["id"])
        self.prompt_combo.blockSignals(False)

    def _on_prompt_combo_changed(self, index: int) -> None:
        pid = self.prompt_combo.currentData()
        if pid is None:
            self.current_prompt_id = None
            return
        self.current_prompt_id = pid
        p = db.prompt_get(pid)
        if p:
            self.prompt_edit.blockSignals(True)
            self.prompt_edit.setPlainText(p["prompt"])
            self.prompt_edit.blockSignals(False)

    def _on_add_model(self) -> None:
        dlg = AddModelDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"] or not data["api_url"] or not data["api_id"]:
            QMessageBox.warning(
                self, "Модель", "Заполните название, URL и api_id."
            )
            return
        db.model_create(
            data["name"],
            data["api_url"],
            data["api_id"],
            data["is_active"],
        )
        QMessageBox.information(self, "Модель", "Модель добавлена.")

    def _on_save_prompt(self) -> None:
        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Промт", "Введите текст промта.")
            return
        db.prompt_create(text, "")
        self._refresh_prompts_combo()
        QMessageBox.information(self, "Промт", "Промт сохранён.")

    def _on_send(self) -> None:
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Отправка", "Введите промт.")
            return
        model_list = models_module.get_active_models_with_keys()
        if not model_list:
            QMessageBox.warning(
                self,
                "Отправка",
                "Нет активных моделей. Добавьте модели в БД и отметьте is_active.",
            )
            return
        self.temp_results.clear()
        self.btn_send.setEnabled(False)
        self.send_worker = SendWorker(prompt, model_list)
        self.send_worker.finished.connect(self._on_send_finished)
        self.send_worker.start()

    def _on_send_finished(self, results: List[dict]) -> None:
        self.send_worker = None
        self.btn_send.setEnabled(True)
        self.temp_results.set_results(results)
        self._refresh_results_table()

    def _refresh_results_table(self) -> None:
        rows = self.temp_results.get_rows()
        q = self.search_edit.text().strip().lower()
        if q:
            rows = [
                r for r in rows
                if q in (r.get("model_name") or "").lower()
                or q in (r.get("response") or "").lower()
                or q in (str(r.get("error") or "")).lower()
            ]
        self.results_table.setRowCount(len(rows))
        self.results_table.blockSignals(True)
        for i, row in enumerate(rows):
            cb = QCheckBox()
            cb.setChecked(bool(row.get("selected")))
            mid, resp = row.get("model_id"), row.get("response") or ""
            cb.stateChanged.connect(
                lambda state, mi=mid, r=resp: self._on_result_checkbox_key(mi, r, state)
            )
            self.results_table.setCellWidget(i, 0, cb)
            self.results_table.setItem(i, 1, QTableWidgetItem(row.get("model_name", "")))
            text = row.get("response") or row.get("error") or ""
            self.results_table.setItem(i, 2, QTableWidgetItem(text))
        self.results_table.blockSignals(False)
        self.results_table.setSortingEnabled(True)

    def _on_result_checkbox_key(
        self, model_id: Any, response: str, state: int
    ) -> None:
        self.temp_results.set_selected_by_key(
            model_id, response, state == Qt.Checked
        )

    def _on_save_results(self) -> None:
        selected = self.temp_results.get_selected_rows()
        if not selected:
            QMessageBox.warning(
                self, "Сохранение", "Выберите строки (галочки) для сохранения."
            )
            return
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Сохранение", "Промт не может быть пустым.")
            return
        prompt_id = self.current_prompt_id
        if prompt_id is None:
            prompt_id = db.prompt_create(prompt_text, "")
            self.current_prompt_id = prompt_id
            self._refresh_prompts_combo()
        saved = []
        for row in selected:
            db.result_create(
                prompt_id,
                row["model_id"],
                row["model_name"],
                row.get("response") or "",
            )
            saved.append(row)
        self.temp_results.remove_saved(saved)
        self._refresh_results_table()
        QMessageBox.information(
            self, "Сохранение", f"Сохранено строк: {len(saved)}."
        )

    def _on_export(self) -> None:
        rows = self.temp_results.get_selected_rows()
        if not rows:
            rows = self.temp_results.get_rows()
        if not rows:
            QMessageBox.warning(self, "Экспорт", "Нет данных для экспорта.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт", "", "Markdown (*.md);;JSON (*.json);;Все файлы (*)"
        )
        if not path:
            return
        try:
            if path.endswith(".json"):
                import json
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, ensure_ascii=False, indent=2)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    for r in rows:
                        f.write(f"## {r.get('model_name', '')}\n\n")
                        f.write((r.get("response") or r.get("error") or "") + "\n\n")
            QMessageBox.information(self, "Экспорт", f"Сохранено: {path}")
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", str(e))


def main() -> None:
    db.init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
