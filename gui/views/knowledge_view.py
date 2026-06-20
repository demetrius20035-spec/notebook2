"""Раздел «База знаний»: статьи и заметки (§2.6)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from gui.api_client import APIClient
from gui.widgets.helpers import fill_table, guard, selected_id

_COLUMNS = [("title", "Заголовок"), ("source_type", "Тип"), ("updated_at", "Обновлено")]


class _ArticleDialog(QDialog):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.created = None
        self.setWindowTitle("Новая статья")
        self.resize(520, 420)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Заголовок*")
        self.content = QPlainTextEdit()
        self.content.setPlaceholderText("Текст статьи (Markdown)")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.content)
        layout.addWidget(buttons)

    def _save(self) -> None:
        if not self.title.text().strip():
            QMessageBox.information(self, "Проверка", "Укажите заголовок.")
            return
        payload = {
            "title": self.title.text().strip(),
            "content": self.content.toPlainText(),
            "source_type": "article",
        }
        self.created = guard(self, lambda: self.client.create_knowledge(payload))
        if self.created:
            self.accept()


class KnowledgeView(QWidget):
    def __init__(self, client: APIClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client

        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>База знаний</h2>"))
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск")
        self.search.returnPressed.connect(self.reload)
        find = QPushButton("Найти")
        find.clicked.connect(self.reload)
        new_btn = QPushButton("+ Статья")
        new_btn.clicked.connect(self._new_article)
        header.addWidget(self.search)
        header.addWidget(find)
        header.addWidget(new_btn)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._preview)
        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(self.viewer)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(splitter)

    def reload(self) -> None:
        rows = guard(self, lambda: self.client.list_knowledge(self.search.text().strip() or None)) or []
        fill_table(self.table, rows, _COLUMNS)

    def _preview(self) -> None:
        aid = selected_id(self.table)
        if aid is None:
            return
        data = guard(self, lambda: self.client.get_knowledge(aid))
        if data:
            self.viewer.setPlainText(f"# {data.get('title','')}\n\n{data.get('content','')}")

    def _new_article(self) -> None:
        dlg = _ArticleDialog(self.client, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.reload()
