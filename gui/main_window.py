"""Главное окно приложения (§6.1)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from gui.api_client import APIClient
from gui.views.ai_view import AIAssistantView
from gui.views.tickets_view import TicketsView

# Пункты навигации (§6.1).
_NAV = [
    ("📋 Тикеты", "tickets"),
    ("👥 Клиенты", "clients"),
    ("🔧 Компоненты", "components"),
    ("📚 База знаний", "knowledge"),
    ("🏪 Склад", "inventory"),
    ("💰 Финансы", "finance"),
    ("📊 Аналитика", "analytics"),
    ("🤖 AI Ассистент", "ai"),
    ("⚙️ Настройки", "settings"),
]


class _PlaceholderView(QWidget):
    """Заглушка для ещё не реализованных экранов."""

    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{title}</h2><p>Раздел в разработке.</p>"))


class MainWindow(QMainWindow):
    """QMainWindow с левой навигацией и стеком рабочих областей."""

    def __init__(self, client: APIClient) -> None:
        super().__init__()
        self.client = client
        self.setWindowTitle("RepairExpert AI")
        self.resize(1200, 760)

        self.nav = QListWidget()
        self.nav.setMaximumWidth(220)
        self.stack = QStackedWidget()

        self.tickets_view = TicketsView(client)
        self.ai_view = AIAssistantView(client)

        for label, key in _NAV:
            QListWidgetItem(label, self.nav)
            if key == "tickets":
                self.stack.addWidget(self.tickets_view)
            elif key == "ai":
                self.stack.addWidget(self.ai_view)
            else:
                self.stack.addWidget(_PlaceholderView(label))

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(central)

        self.statusBar().showMessage("Готово")
        self.tickets_view.reload()
