"""Карточка тикета — главный экран работы (§6.2).

Вкладки: Журнал, Измерения, Компоненты, AI Ассистент, Документы.
Сверху — сведения и смена статуса; снизу — приём оплаты.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.api_client import APIClient
from gui.widgets.helpers import fill_table, guard

# Человекочитаемые статусы.
STATUS_LABELS = {
    "new": "Принят",
    "diagnostics": "Диагностика",
    "in_repair": "В работе",
    "waiting_parts": "Ожидание деталей",
    "waiting_client": "Ожидание клиента",
    "ready": "Готов",
    "delivered": "Выдан",
    "closed": "Закрыт",
    "warranty": "Гарантия",
}
_DOC_TYPES = [
    ("Квитанция о приёмке", "acceptance"),
    ("Акт выполненных работ", "act"),
    ("Дефектовочная ведомость", "defect"),
    ("Гарантийный талон", "warranty"),
]
_AI_MODES = [("🎯 Следующий шаг", "next_step"), ("🧙 Мастер", "wizard"), ("💬 Чат", "chat")]


class TicketDetail(QWidget):
    """Детальная карточка одного тикета."""

    def __init__(self, client: APIClient, ticket_id: int, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.ticket_id = ticket_id
        self.ticket: dict = {}

        self.header = QLabel()
        self.header.setWordWrap(True)

        # Панель статуса
        self.status_combo = QComboBox()
        for value, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, value)
        apply_status = QPushButton("Сменить статус")
        apply_status.clicked.connect(self._change_status)
        pay_btn = QPushButton("💰 Принять оплату")
        pay_btn.clicked.connect(self._take_payment)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Статус:"))
        status_row.addWidget(self.status_combo)
        status_row.addWidget(apply_status)
        status_row.addStretch()
        status_row.addWidget(pay_btn)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._journal_tab(), "Журнал")
        self.tabs.addTab(self._measurements_tab(), "Измерения")
        self.tabs.addTab(self._components_tab(), "Компоненты")
        self.tabs.addTab(self._ai_tab(), "AI Ассистент")
        self.tabs.addTab(self._documents_tab(), "Документы")

        layout = QVBoxLayout(self)
        layout.addWidget(self.header)
        layout.addLayout(status_row)
        layout.addWidget(self.tabs, stretch=1)

        self.reload()

    # ──────────────────────────── загрузка ────────────────────────────
    def reload(self) -> None:
        data = guard(self, lambda: self.client.get_ticket(self.ticket_id))
        if not data:
            return
        self.ticket = data
        status = data.get("status", "")
        self.header.setText(
            f"<h2>{data.get('ticket_number','')}</h2>"
            f"<b>Статус:</b> {STATUS_LABELS.get(status, status)} &nbsp; | &nbsp;"
            f"<b>Приоритет:</b> {data.get('priority','')}<br>"
            f"<b>Проблема:</b> {data.get('problem_description','')}"
        )
        idx = self.status_combo.findData(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self._reload_journal()
        self._reload_measurements()
        self._reload_documents()

    def _change_status(self) -> None:
        new_status = self.status_combo.currentData()
        res = guard(
            self,
            lambda: self.client.change_status(self.ticket_id, new_status),
            error_title="Смена статуса",
        )
        if res:
            self.reload()

    def _take_payment(self) -> None:
        amount, okp = QInputDialog.getDouble(
            self, "Оплата", "Сумма:", 0, 0, 10_000_000, 2
        )
        if not okp or amount <= 0:
            return
        res = guard(
            self,
            lambda: self.client.add_payment(
                {"ticket_id": self.ticket_id, "amount": amount, "payment_type": "final"}
            ),
        )
        if res:
            QMessageBox.information(self, "Оплата", "Платёж зафиксирован.")
            self._reload_journal()

    # ──────────────────────────── Журнал ────────────────────────────
    def _journal_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.journal_table = QTableWidget(0, 3)
        layout.addWidget(self.journal_table)

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Новая заметка в журнал…")
        add = QPushButton("+ Добавить заметку")
        add.clicked.connect(self._add_note)
        row = QHBoxLayout()
        row.addWidget(self.note_input)
        row.addWidget(add)
        layout.addLayout(row)
        return w

    def _reload_journal(self) -> None:
        rows = guard(self, lambda: self.client.ticket_history(self.ticket_id)) or []
        fill_table(
            self.journal_table,
            rows,
            [("created_at", "Время"), ("type", "Тип"), ("content", "Описание")],
        )

    def _add_note(self) -> None:
        text = self.note_input.text().strip()
        if not text:
            return
        res = guard(
            self,
            lambda: self.client.add_history(
                self.ticket_id, {"entry_type": "note", "title": "Заметка", "content": text}
            ),
        )
        if res:
            self.note_input.clear()
            self._reload_journal()

    # ──────────────────────────── Измерения ────────────────────────────
    def _measurements_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.meas_table = QTableWidget(0, 5)
        layout.addWidget(self.meas_table)

        self.m_line = QLineEdit()
        self.m_line.setPlaceholderText("Линия (VIN, +3VALW…)")
        self.m_val = QLineEdit()
        self.m_val.setPlaceholderText("Измерено")
        self.m_norm = QLineEdit()
        self.m_norm.setPlaceholderText("Норма")
        self.m_unit = QLineEdit("V")
        self.m_unit.setMaximumWidth(48)
        add = QPushButton("+ Измерение")
        add.clicked.connect(self._add_measurement)
        row = QHBoxLayout()
        for wdt in (self.m_line, self.m_val, self.m_norm, self.m_unit, add):
            row.addWidget(wdt)
        layout.addLayout(row)
        return w

    def _reload_measurements(self) -> None:
        rows = guard(self, lambda: self.client.list_measurements(self.ticket_id)) or []
        fill_table(
            self.meas_table,
            rows,
            [
                ("line_name", "Линия"),
                ("value_norm", "Норма"),
                ("value_measured", "Измерено"),
                ("unit", "Ед."),
                ("status", "Статус"),
            ],
        )

    def _add_measurement(self) -> None:
        if not self.m_line.text().strip() or not self.m_val.text().strip():
            return
        try:
            measured = float(self.m_val.text().replace(",", "."))
            norm = float(self.m_norm.text().replace(",", ".")) if self.m_norm.text().strip() else None
        except ValueError:
            QMessageBox.information(self, "Проверка", "Значения должны быть числами.")
            return
        payload = {
            "line_name": self.m_line.text().strip(),
            "value_measured": measured,
            "value_norm": norm,
            "unit": self.m_unit.text().strip() or "V",
        }
        res = guard(self, lambda: self.client.add_measurement(self.ticket_id, payload))
        if res:
            for f in (self.m_line, self.m_val, self.m_norm):
                f.clear()
            self._reload_measurements()
            self._reload_journal()

    # ──────────────────────────── Компоненты ────────────────────────────
    def _components_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Поиск по справочнику и запись замены в журнал:"))
        self.comp_search = QLineEdit()
        self.comp_search.setPlaceholderText("Part number или название")
        find = QPushButton("Найти")
        find.clicked.connect(self._search_components)
        srow = QHBoxLayout()
        srow.addWidget(self.comp_search)
        srow.addWidget(find)
        layout.addLayout(srow)

        self.comp_table = QTableWidget(0, 3)
        layout.addWidget(self.comp_table)

        record = QPushButton("Записать замену выбранного компонента")
        record.clicked.connect(self._record_replacement)
        layout.addWidget(record)
        return w

    def _search_components(self) -> None:
        rows = guard(self, lambda: self.client.list_components(self.comp_search.text().strip())) or []
        fill_table(
            self.comp_table,
            rows,
            [("part_number", "Part №"), ("name", "Название"), ("category", "Категория")],
        )

    def _record_replacement(self) -> None:
        from gui.widgets.helpers import selected_id

        comp_id = selected_id(self.comp_table)
        if comp_id is None:
            QMessageBox.information(self, "Компоненты", "Выберите компонент в таблице.")
            return
        row = self.comp_table.currentRow()
        name = self.comp_table.item(row, 1).text() if row >= 0 else f"#{comp_id}"
        res = guard(
            self,
            lambda: self.client.add_history(
                self.ticket_id,
                {"entry_type": "replacement", "title": "Замена", "content": f"Заменён: {name}"},
            ),
        )
        if res:
            self._reload_journal()
            QMessageBox.information(self, "Компоненты", f"Замена «{name}» записана в журнал.")

    # ──────────────────────────── AI ────────────────────────────
    def _ai_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        modes = QHBoxLayout()
        self._ai_buttons: list[tuple[QRadioButton, str]] = []
        for i, (label, value) in enumerate(_AI_MODES):
            btn = QRadioButton(label)
            if i == 0:
                btn.setChecked(True)
            modes.addWidget(btn)
            self._ai_buttons.append((btn, value))
        modes.addStretch()
        layout.addLayout(modes)

        form = QFormLayout()
        self.ai_provider = QComboBox()
        self.ai_provider.addItem("(по умолчанию)", None)
        self.ai_query = QLineEdit()
        self.ai_query.setPlaceholderText("Вопрос (для чата)")
        form.addRow("Провайдер:", self.ai_provider)
        form.addRow("Вопрос:", self.ai_query)
        layout.addLayout(form)

        ask = QPushButton("🤖 Спросить AI")
        ask.clicked.connect(self._ask_ai)
        layout.addWidget(ask)

        self.ai_result = QPlainTextEdit()
        self.ai_result.setReadOnly(True)
        layout.addWidget(self.ai_result, stretch=1)

        data = guard(self, self.client.list_providers)
        if data:
            for name in data.get("providers", []):
                self.ai_provider.addItem(name, name)
        return w

    def _ask_ai(self) -> None:
        mode = next((v for b, v in self._ai_buttons if b.isChecked()), "next_step")
        self.ai_result.setPlainText("Запрос к модели…")
        payload = {
            "ticket_id": self.ticket_id,
            "mode": mode,
            "query": self.ai_query.text(),
            "provider": self.ai_provider.currentData(),
        }
        data = guard(self, lambda: self.client.diagnose(payload), error_title="AI")
        if not data:
            self.ai_result.setPlainText("(ошибка запроса)")
            return
        head = f"[{data.get('provider')}/{data.get('model')}] токенов: {data.get('tokens_used')}\n\n"
        self.ai_result.setPlainText(head + data.get("answer", ""))
        self._reload_journal()

    # ──────────────────────────── Документы ────────────────────────────
    def _documents_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.doc_type = QComboBox()
        for label, value in _DOC_TYPES:
            self.doc_type.addItem(label, value)
        gen = QPushButton("Сгенерировать PDF")
        gen.clicked.connect(self._generate_doc)
        row = QHBoxLayout()
        row.addWidget(self.doc_type)
        row.addWidget(gen)
        row.addStretch()
        layout.addLayout(row)

        self.doc_table = QTableWidget(0, 3)
        layout.addWidget(self.doc_table)
        return w

    def _reload_documents(self) -> None:
        rows = guard(self, lambda: self.client.list_documents(self.ticket_id)) or []
        fill_table(
            self.doc_table,
            rows,
            [("created_at", "Время"), ("document_type", "Тип"), ("file_path", "Файл")],
        )

    def _generate_doc(self) -> None:
        res = guard(
            self,
            lambda: self.client.generate_document(self.ticket_id, self.doc_type.currentData()),
            error_title="Документ",
        )
        if res:
            QMessageBox.information(self, "Документ", f"Создан файл:\n{res.get('file_path')}")
            self._reload_documents()
