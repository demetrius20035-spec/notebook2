"""Раздел «Финансы»: платежи и сводка по выручке (§2.10)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.widgets.helpers import fill_table, guard

_COLUMNS = [
    ("paid_at", "Время"),
    ("ticket_id", "Тикет"),
    ("amount", "Сумма"),
    ("type", "Тип"),
    ("method", "Способ"),
]


class FinanceView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Финансы</h2>"))
        header.addStretch()
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.reload)
        header.addWidget(refresh)

        self.summary = QLabel()
        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.summary)
        layout.addWidget(QLabel("Последние платежи:"))
        layout.addWidget(self.table)

    def reload(self) -> None:
        report = guard(self, lambda: self.client.revenue_report(30))
        if report:
            self.summary.setText(
                f"<b>За 30 дней:</b> выручка {report['revenue']:.2f} · "
                f"возвраты {report['refunds']:.2f} · "
                f"чистыми {report['net']:.2f} · платежей {report['payments_count']}"
            )
        else:
            self.summary.setText("Сводка доступна администратору и бухгалтеру.")
        rows = guard(self, lambda: self.client.list_payments()) or []
        fill_table(self.table, rows, _COLUMNS)
