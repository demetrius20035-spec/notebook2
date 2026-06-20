"""Диалог создания клиента (§2.1)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from gui.api_client import APIClient, APIError


class ClientDialog(QDialog):
    """Создание нового клиента."""

    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.created: dict | None = None
        self.setWindowTitle("Новый клиент")
        self.setMinimumWidth(380)

        self.full_name = QLineEdit()
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.address = QLineEdit()
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(80)

        form = QFormLayout()
        form.addRow("ФИО*:", self.full_name)
        form.addRow("Телефон:", self.phone)
        form.addRow("E-mail:", self.email)
        form.addRow("Адрес:", self.address)
        form.addRow("Заметки:", self.notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _save(self) -> None:
        if not self.full_name.text().strip():
            QMessageBox.information(self, "Проверка", "Укажите ФИО клиента.")
            return
        payload = {
            "full_name": self.full_name.text().strip(),
            "phone": self.phone.text().strip() or None,
            "email": self.email.text().strip() or None,
            "address": self.address.text().strip() or None,
            "notes": self.notes.toPlainText().strip() or None,
        }
        try:
            self.created = self.client.create_client(payload)
        except APIError as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.accept()
