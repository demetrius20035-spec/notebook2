"""Вкладка «AI Ассистент» (§6.3).

Три режима: «Следующий шаг», «Мастер диагностики», «Свободный чат».
Запрос уходит к POST /api/v1/ai/diagnose с привязкой к тикету.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient, APIError

_MODES = [
    ("🎯 Следующий шаг", "next_step"),
    ("🧙 Мастер диагностики", "wizard"),
    ("💬 Свободный чат", "chat"),
]


class AIAssistantView(QWidget):
    """Панель взаимодействия с LLM-диагностикой."""

    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>AI Ассистент</h2>"))

        # Режимы
        modes_box = QHBoxLayout()
        self._mode_buttons: list[tuple[QRadioButton, str]] = []
        for idx, (label, value) in enumerate(_MODES):
            btn = QRadioButton(label)
            if idx == 0:
                btn.setChecked(True)
            modes_box.addWidget(btn)
            self._mode_buttons.append((btn, value))
        modes_box.addStretch()
        layout.addLayout(modes_box)

        # Параметры запроса
        form = QFormLayout()
        self.ticket_id = QLineEdit()
        self.ticket_id.setPlaceholderText("ID тикета")
        self.provider = QComboBox()
        self.provider.addItem("(по умолчанию)", None)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Вопрос инженера (для свободного чата)")
        form.addRow("Тикет:", self.ticket_id)
        form.addRow("Провайдер:", self.provider)
        form.addRow("Вопрос:", self.query)
        layout.addLayout(form)

        ask = QPushButton("🤖 Спросить AI")
        ask.clicked.connect(self._on_ask)
        layout.addWidget(ask)

        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        layout.addWidget(self.result, stretch=1)

        self._load_providers()

    def _selected_mode(self) -> str:
        for btn, value in self._mode_buttons:
            if btn.isChecked():
                return value
        return "next_step"

    def _load_providers(self) -> None:
        try:
            data = self.client.list_providers()
        except APIError:
            return
        for name in data.get("providers", []):
            self.provider.addItem(name, name)

    def _on_ask(self) -> None:
        if not self.ticket_id.text().strip().isdigit():
            QMessageBox.information(self, "AI", "Укажите числовой ID тикета.")
            return
        payload = {
            "ticket_id": int(self.ticket_id.text()),
            "mode": self._selected_mode(),
            "query": self.query.text(),
            "provider": self.provider.currentData(),
        }
        self.result.setPlainText("Запрос к модели…")
        try:
            data = self.client.diagnose(payload)
        except APIError as exc:
            self.result.setPlainText(f"Ошибка: {exc}")
            return
        header = f"[{data.get('provider')}/{data.get('model')}] токенов: {data.get('tokens_used')}\n"
        sources = data.get("sources", {})
        footer = (
            f"\n\n— Похожие ремонты: {sources.get('repairs')}"
            f"\n— Даташиты: {sources.get('datasheets')}"
        )
        self.result.setPlainText(header + "\n" + data.get("answer", "") + footer)
