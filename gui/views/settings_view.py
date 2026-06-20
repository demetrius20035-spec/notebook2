"""Раздел «Настройки»: профиль, LLM-провайдеры и их статус (§2.4)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.widgets.helpers import guard


class SettingsView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Настройки</h2>"))

        user = client.current_user or {}
        layout.addWidget(
            QLabel(
                f"<b>Пользователь:</b> {user.get('full_name','')} "
                f"({user.get('username','')}, роль: {user.get('role','')})"
            )
        )

        layout.addWidget(QLabel("<b>LLM-провайдеры</b> (выбор по умолчанию — в .env):"))
        row = QHBoxLayout()
        self.provider = QComboBox()
        check = QPushButton("Проверить доступность")
        check.clicked.connect(self._check)
        row.addWidget(self.provider)
        row.addWidget(check)
        row.addStretch()
        layout.addLayout(row)

        self.status = QLabel()
        layout.addWidget(self.status)
        layout.addStretch()

        self._load_providers()

    def _load_providers(self) -> None:
        data = guard(self, self.client.list_providers)
        if not data:
            return
        for name in data.get("providers", []):
            self.provider.addItem(name, name)
        idx = self.provider.findData(data.get("default"))
        if idx >= 0:
            self.provider.setCurrentIndex(idx)
        self.status.setText(f"Провайдер по умолчанию: <b>{data.get('default')}</b>")

    def _check(self) -> None:
        provider = self.provider.currentData()
        self.status.setText("Проверка…")
        data = guard(self, lambda: self.client.ai_health(provider), error_title="LLM")
        if data:
            mark = "🟢 доступен" if data.get("healthy") else "🔴 недоступен"
            self.status.setText(
                f"{data.get('provider')} / {data.get('model')}: {mark}"
            )
