"""Раздел «Аналитика»: дашборд мастерской (§2.13)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.views.ticket_detail import STATUS_LABELS
from gui.widgets.helpers import guard


def _metric(title: str, value: str) -> QGroupBox:
    box = QGroupBox(title)
    lay = QVBoxLayout(box)
    lbl = QLabel(value)
    lbl.setStyleSheet("font-size: 24px; font-weight: bold;")
    lay.addWidget(lbl)
    return box


class AnalyticsView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Аналитика</h2>"))
        header.addStretch()
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.reload)
        header.addWidget(refresh)

        self.metrics = QGridLayout()
        self.by_status = QLabel()
        self.top = QLabel()

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(self.metrics)
        layout.addWidget(QLabel("<b>Тикеты по статусам:</b>"))
        layout.addWidget(self.by_status)
        layout.addWidget(QLabel("<b>Топ заменяемых компонентов:</b>"))
        layout.addWidget(self.top)
        layout.addStretch()

    def reload(self) -> None:
        data = guard(self, self.client.dashboard)
        if not data:
            return
        # очистить метрики
        while self.metrics.count():
            item = self.metrics.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.metrics.addWidget(_metric("В работе", str(data["tickets_active"])), 0, 0)
        self.metrics.addWidget(_metric("Выручка 30д", f"{data['revenue_30d']:.0f}"), 0, 1)
        self.metrics.addWidget(_metric("Дефицит склада", str(data["low_stock_count"])), 0, 2)
        self.metrics.addWidget(_metric("Клиентов", str(data["clients_total"])), 0, 3)

        statuses = data.get("tickets_by_status", {})
        self.by_status.setText(
            "   ".join(
                f"{STATUS_LABELS.get(k, k)}: {v}" for k, v in statuses.items() if v
            )
            or "—"
        )
        top = data.get("top_components", [])
        self.top.setText(
            "\n".join(f"• {t['name']} — {t['count']}" for t in top) or "—"
        )
