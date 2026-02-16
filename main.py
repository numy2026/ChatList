#!/usr/bin/env python3
"""Минимальное приложение с графическим интерфейсом на PyQt5."""

import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Минимальное приложение PyQt")
        self.setMinimumSize(320, 200)

        # Центральный виджет и layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Метка
        self.label = QLabel("Привет, PyQt!")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Кнопка
        self.button = QPushButton("Нажми меня")
        self.button.clicked.connect(self._on_button_clicked)
        layout.addWidget(self.button)

    def _on_button_clicked(self):
        self.label.setText("Минимальная программа на Python")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
