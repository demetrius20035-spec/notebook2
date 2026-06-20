"""Список тикетов: фильтр, создание, открытие карточки (§6.1, §6.2)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.dialogs.ticket_dialog import TicketDialog
from gui.views.ticket_detail import STATUS_LABELS, TicketDetail
from gui.widgets.helpers import fill_table, guard, selected_id

_COLUMNS = [
    ("ticket_number", "Номер"),
    ("status", "Статус"),
    ("priority", "Приоритет"),
    ("problem_description", "Проблема"),
]


class TicketsView(QWidget):
    """Таблица тикетов с приёмкой и открытием карточки."""

    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Ремонтные заявки</h2>"))
        header.addStretch()
        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", None)
        for value, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self.reload)
        new_btn = QPushButton("+ Приёмка (новый тикет)")
        new_btn.clicked.connect(self._new_ticket)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.reload)
        header.addWidget(self.status_filter)
        header.addWidget(new_btn)
        header.addWidget(refresh)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._open_selected)

        open_btn = QPushButton("Открыть карточку")
        open_btn.clicked.connect(self._open_selected)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.table)
        layout.addWidget(open_btn)

    def reload(self) -> None:
        status = self.status_filter.currentData()
        rows = guard(self, lambda: self.client.list_tickets(status)) or []
        # Локализуем статус для отображения.
        for r in rows:
            r["status"] = STATUS_LABELS.get(r.get("status"), r.get("status"))
            r["problem_description"] = (r.get("problem_description") or "")[:90]
        fill_table(self.table, rows, _COLUMNS)

    def _new_ticket(self) -> None:
        dlg = TicketDialog(self.client, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.created:
            self.reload()
            self._open_ticket(dlg.created["id"])

    def _open_selected(self) -> None:
        tid = selected_id(self.table)
        if tid is not None:
            self._open_ticket(tid)

    def _open_ticket(self, ticket_id: int) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Тикет #{ticket_id}")
        dlg.resize(900, 640)
        layout = QVBoxLayout(dlg)
        layout.addWidget(TicketDetail(self.client, ticket_id, dlg))
        dlg.exec()
        self.reload()
