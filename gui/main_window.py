"""Главное окно приложения (§6.1)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from gui.api_client import APIClient
from gui.views.analytics_view import AnalyticsView
from gui.views.clients_view import ClientsView
from gui.views.components_view import ComponentsView
from gui.views.finance_view import FinanceView
from gui.views.inventory_view import InventoryView
from gui.views.knowledge_view import KnowledgeView
from gui.views.settings_view import SettingsView
from gui.views.tickets_view import TicketsView


class MainWindow(QMainWindow):
    """QMainWindow с левой навигацией и стеком рабочих областей."""

    def __init__(self, client: APIClient) -> None:
        super().__init__()
        self.client = client
        user = client.current_user or {}
        self.setWindowTitle(
            f"RepairExpert AI — {user.get('full_name','')} ({user.get('role','')})"
        )
        self.resize(1240, 780)

        self.nav = QListWidget()
        self.nav.setMaximumWidth(230)
        self.stack = QStackedWidget()

        # (метка, фабрика виджета). Виджеты создаются лениво при первом показе.
        self._specs = [
            ("📋 Тикеты", lambda: TicketsView(client)),
            ("👥 Клиенты", lambda: ClientsView(client)),
            ("🔧 Компоненты", lambda: ComponentsView(client)),
            ("📚 База знаний", lambda: KnowledgeView(client)),
            ("🏪 Склад", lambda: InventoryView(client)),
            ("💰 Финансы", lambda: FinanceView(client)),
            ("📊 Аналитика", lambda: AnalyticsView(client)),
            ("⚙️ Настройки", lambda: SettingsView(client)),
        ]
        self._widgets: list[QWidget | None] = [None] * len(self._specs)

        for label, _ in self._specs:
            QListWidgetItem(label, self.nav)
            self.stack.addWidget(QWidget())  # плейсхолдер до ленивой загрузки

        self.nav.currentRowChanged.connect(self._switch)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(central)

        self.statusBar().showMessage("Готово")
        self.nav.setCurrentRow(0)

    def _switch(self, index: int) -> None:
        if index < 0:
            return
        if self._widgets[index] is None:
            widget = self._specs[index][1]()
            self._widgets[index] = widget
            old = self.stack.widget(index)
            self.stack.insertWidget(index, widget)
            self.stack.removeWidget(old)
            old.deleteLater()
        widget = self._widgets[index]
        self.stack.setCurrentIndex(index)
        # Обновляем данные при каждом показе, если у виджета есть reload().
        if hasattr(widget, "reload"):
            widget.reload()
