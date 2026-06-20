"""Диалог приёмки: создание устройства и тикета (§2.2, F-001)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.api_client import APIClient, APIError
from gui.dialogs.client_dialog import ClientDialog

_PRIORITIES = [("Обычный", "normal"), ("Высокий", "high"), ("Срочный", "urgent")]


class TicketDialog(QDialog):
    """Приёмка устройства: клиент + устройство + описание проблемы."""

    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.created: dict | None = None
        self.setWindowTitle("Приёмка — новый тикет")
        self.setMinimumWidth(460)

        # Клиент
        self.client_combo = QComboBox()
        add_client = QPushButton("+ Клиент")
        add_client.clicked.connect(self._new_client)

        # Устройство
        self.device_type = QComboBox()
        self.manufacturer = QLineEdit()
        self.model_name = QLineEdit()
        self.platform = QLineEdit()
        self.serial = QLineEdit()
        self.imei = QLineEdit()

        # Заявка
        self.priority = QComboBox()
        for label, value in _PRIORITIES:
            self.priority.addItem(label, value)
        self.master = QComboBox()
        self.problem = QPlainTextEdit()
        self.problem.setPlaceholderText("Описание неисправности со слов клиента (мин. 5 символов)")
        self.problem.setMinimumHeight(90)

        form = QFormLayout()
        client_row = QVBoxLayout()
        client_row.addWidget(self.client_combo)
        client_row.addWidget(add_client)
        form.addRow("Клиент*:", client_row)
        form.addRow("Тип устройства*:", self.device_type)
        form.addRow("Производитель*:", self.manufacturer)
        form.addRow("Модель*:", self.model_name)
        form.addRow("Платформа/плата:", self.platform)
        form.addRow("Серийный номер:", self.serial)
        form.addRow("IMEI:", self.imei)
        form.addRow("Приоритет:", self.priority)
        form.addRow("Инженер:", self.master)
        form.addRow("Проблема*:", self.problem)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._load_refs()

    def _load_refs(self) -> None:
        try:
            for c in self.client.list_clients():
                self.client_combo.addItem(f"{c['full_name']} ({c.get('phone') or '—'})", c["id"])
            for t in self.client.list_device_types():
                self.device_type.addItem(t["name"], t["id"])
            self.master.addItem("(не назначен)", None)
            for u in self.client.list_users():
                if u["role"] in ("master", "admin"):
                    self.master.addItem(u["full_name"], u["id"])
        except APIError as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить справочники:\n{exc}")

    def _new_client(self) -> None:
        dlg = ClientDialog(self.client, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.created:
            self.client_combo.addItem(dlg.created["full_name"], dlg.created["id"])
            self.client_combo.setCurrentIndex(self.client_combo.count() - 1)

    def _save(self) -> None:
        client_id = self.client_combo.currentData()
        if client_id is None:
            QMessageBox.information(self, "Проверка", "Выберите или создайте клиента.")
            return
        if not self.manufacturer.text().strip() or not self.model_name.text().strip():
            QMessageBox.information(self, "Проверка", "Заполните производителя и модель.")
            return
        if len(self.problem.toPlainText().strip()) < 5:
            QMessageBox.information(self, "Проверка", "Описание проблемы — минимум 5 символов.")
            return

        try:
            device = self.client.create_device(
                {
                    "client_id": client_id,
                    "device_type_id": self.device_type.currentData(),
                    "manufacturer": self.manufacturer.text().strip(),
                    "model_name": self.model_name.text().strip(),
                    "platform": self.platform.text().strip() or None,
                    "serial_number": self.serial.text().strip() or None,
                    "imei": self.imei.text().strip() or None,
                }
            )
            self.created = self.client.create_ticket(
                {
                    "client_id": client_id,
                    "device_id": device["id"],
                    "problem_description": self.problem.toPlainText().strip(),
                    "priority": self.priority.currentData(),
                    "master_id": self.master.currentData(),
                }
            )
        except APIError as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.accept()
