"""Диалог авторизации (§6.1)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from gui.api_client import APIClient, APIError


class LoginDialog(QDialog):
    """Окно входа: логин/пароль/«Запомнить меня»."""

    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("RepairExpert AI — Вход")
        self.setMinimumWidth(320)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember = QCheckBox("Запомнить меня")

        form = QFormLayout()
        form.addRow("Логин:", self.username)
        form.addRow("Пароль:", self.password)
        form.addRow("", self.remember)

        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self._on_login)
        self.password.returnPressed.connect(self._on_login)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(login_btn)

    def _on_login(self) -> None:
        try:
            self.client.login(
                self.username.text().strip(),
                self.password.text(),
                self.remember.isChecked(),
            )
        except APIError as exc:
            QMessageBox.critical(self, "Ошибка входа", str(exc))
            return
        self.accept()
