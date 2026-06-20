"""Помощники для типовых операций с виджетами."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QMessageBox, QTableWidget, QTableWidgetItem, QWidget


def fill_table(
    table: QTableWidget,
    rows: list[dict],
    columns: list[tuple[str, str]],
    id_key: str = "id",
    stretch_last: bool = True,
) -> None:
    """Заполняет таблицу строками.

    :param columns: список (ключ_в_словаре, заголовок).
    :param id_key: ключ, чьё значение кладётся в UserRole первой ячейки.
    """
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([title for _, title in columns])
    table.setRowCount(0)
    for r in rows:
        row = table.rowCount()
        table.insertRow(row)
        for col, (key, _) in enumerate(columns):
            value = r.get(key)
            item = QTableWidgetItem("" if value is None else str(value))
            if col == 0 and id_key in r:
                item.setData(Qt.ItemDataRole.UserRole, r[id_key])
            table.setItem(row, col, item)
    if stretch_last and columns:
        table.horizontalHeader().setSectionResizeMode(
            len(columns) - 1, QHeaderView.ResizeMode.Stretch
        )


def selected_id(table: QTableWidget) -> int | None:
    """Возвращает id (из UserRole) выбранной строки или None."""
    row = table.currentRow()
    if row < 0:
        return None
    item = table.item(row, 0)
    return item.data(Qt.ItemDataRole.UserRole) if item else None


def guard(parent: QWidget, fn: Callable, *, error_title: str = "Ошибка"):
    """Выполняет вызов API, показывая ошибки как QMessageBox.

    Возвращает результат или None при ошибке.
    """
    from gui.api_client import APIError

    try:
        return fn()
    except APIError as exc:
        QMessageBox.warning(parent, error_title, str(exc))
        return None
