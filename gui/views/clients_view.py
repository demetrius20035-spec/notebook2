"""Раздел «Клиенты»: список, поиск, создание (§2.1)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.dialogs.client_dialog import ClientDialog
from gui.widgets.helpers import fill_table, guard

_COLUMNS = [
    ("full_name", "ФИО"),
    ("phone", "Телефон"),
    ("email", "E-mail"),
    ("client_tier", "Категория"),
    ("total_repairs", "Ремонтов"),
]


class ClientsView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Клиенты</h2>"))
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по ФИО / телефону / e-mail")
        self.search.returnPressed.connect(self.reload)
        new_btn = QPushButton("+ Новый клиент")
        new_btn.clicked.connect(self._new_client)
        find = QPushButton("Найти")
        find.clicked.connect(self.reload)
        header.addWidget(self.search)
        header.addWidget(find)
        header.addWidget(new_btn)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.table)

    def reload(self) -> None:
        rows = guard(self, lambda: self.client.list_clients(self.search.text().strip() or None)) or []
        fill_table(self.table, rows, _COLUMNS)

    def _new_client(self) -> None:
        dlg = ClientDialog(self.client, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.reload()
