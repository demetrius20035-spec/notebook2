"""Раздел «Компоненты»: справочник и создание (§2.7)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.widgets.helpers import fill_table, guard

_COLUMNS = [
    ("part_number", "Part №"),
    ("name", "Название"),
    ("category", "Категория"),
    ("manufacturer", "Производитель"),
    ("package_type", "Корпус"),
]


class _ComponentDialog(QDialog):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.created = None
        self.setWindowTitle("Новый компонент")
        self.setMinimumWidth(360)

        self.part_number = QLineEdit()
        self.name = QLineEdit()
        self.category = QLineEdit()
        self.manufacturer = QLineEdit()
        self.package_type = QLineEdit()

        form = QFormLayout()
        form.addRow("Part number:", self.part_number)
        form.addRow("Название*:", self.name)
        form.addRow("Категория*:", self.category)
        form.addRow("Производитель:", self.manufacturer)
        form.addRow("Корпус:", self.package_type)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _save(self) -> None:
        if not self.name.text().strip() or not self.category.text().strip():
            QMessageBox.information(self, "Проверка", "Название и категория обязательны.")
            return
        payload = {
            "part_number": self.part_number.text().strip() or None,
            "name": self.name.text().strip(),
            "category": self.category.text().strip(),
            "manufacturer": self.manufacturer.text().strip() or None,
            "package_type": self.package_type.text().strip() or None,
        }
        self.created = guard(self, lambda: self.client.create_component(payload))
        if self.created:
            self.accept()


class ComponentsView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Компоненты</h2>"))
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Part number или название")
        self.search.returnPressed.connect(self.reload)
        find = QPushButton("Найти")
        find.clicked.connect(self.reload)
        new_btn = QPushButton("+ Компонент")
        new_btn.clicked.connect(self._new_component)
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
        rows = guard(self, lambda: self.client.list_components(self.search.text().strip() or None)) or []
        fill_table(self.table, rows, _COLUMNS)

    def _new_component(self) -> None:
        dlg = _ComponentDialog(self.client, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.reload()
