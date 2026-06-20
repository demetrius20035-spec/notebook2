"""Представление списка тикетов (§6.1, §6.2)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient, APIError

_COLUMNS = ["№", "Номер", "Статус", "Приоритет", "Проблема"]


class TicketsView(QWidget):
    """Таблица тикетов с кнопкой обновления."""

    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Ремонтные заявки</h2>"))
        header.addStretch()
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.reload)
        header.addWidget(refresh)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(
            len(_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.table)

    def reload(self) -> None:
        try:
            tickets = self.client.list_tickets()
        except APIError as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить тикеты:\n{exc}")
            return
        self.table.setRowCount(0)
        for t in tickets:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                str(t.get("id", "")),
                t.get("ticket_number", ""),
                t.get("status", ""),
                t.get("priority", ""),
                (t.get("problem_description", "") or "")[:80],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, t.get("id"))
                self.table.setItem(row, col, item)
