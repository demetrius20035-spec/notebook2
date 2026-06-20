"""Раздел «Склад»: остатки и движения (§2.9)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.widgets.helpers import fill_table, guard, selected_id

_COLUMNS = [
    ("component_id", "ID"),
    ("name", "Компонент"),
    ("available", "Доступно"),
    ("min_stock", "Мин."),
    ("location", "Место"),
    ("low_stock", "Дефицит"),
]


class InventoryView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Склад</h2>"))
        header.addStretch()
        for label, mtype in (("Приход", "in"), ("Расход", "out")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, t=mtype: self._move(t))
            header.addWidget(btn)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.reload)
        header.addWidget(refresh)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(QLabel("Остатки. Выберите строку и нажмите Приход/Расход."))
        layout.addWidget(self.table)

    def reload(self) -> None:
        rows = guard(self, self.client.list_inventory) or []
        for r in rows:
            r["low_stock"] = "⚠ да" if r.get("low_stock") else ""
        fill_table(self.table, rows, _COLUMNS)

    def _move(self, move_type: str) -> None:
        comp_id = selected_id(self.table)
        if comp_id is None:
            QMessageBox.information(self, "Склад", "Выберите компонент.")
            return
        qty, ok = QInputDialog.getInt(self, "Количество", "Кол-во:", 1, 1, 1_000_000)
        if not ok:
            return
        res = guard(
            self,
            lambda: self.client.inventory_move(
                {"component_id": comp_id, "move_type": move_type, "quantity": qty}
            ),
        )
        if res:
            self.reload()
