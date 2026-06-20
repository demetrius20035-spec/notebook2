"""LLM-диагностика: сборка контекста, RAG и вызов модели (F-004)."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.llm import LLMMessage, create_adapter
from backend.llm.base import BaseLLMAdapter
from backend.models.catalog import Manufacturer, Platform
from backend.models.device import Device
from backend.models.enums import HistoryEntryType
from backend.models.ticket import RepairHistory, RepairMeasurement, RepairTicket
from backend.prompts.diagnostics import CONTEXT_TEMPLATE, build_system_prompt
from backend.rag.retriever import Retriever
from backend.services import audit_service

logger = logging.getLogger(__name__)


class DiagnosticsService:
    """Оркестрация запроса к LLM с RAG-контекстом."""

    def __init__(
        self,
        db: Session,
        adapter: BaseLLMAdapter | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        self.db = db
        self.adapter = adapter or create_adapter()
        self.retriever = retriever

    async def diagnose(
        self,
        *,
        ticket_id: int,
        mode: str = "next_step",
        user_query: str = "",
        actor_id: int | None = None,
    ) -> dict:
        """Выполняет диагностический запрос и сохраняет его в журнал."""
        ticket = self.db.get(RepairTicket, ticket_id)
        if ticket is None:
            raise ValueError(f"Тикет {ticket_id} не найден")

        context, sources = await self._build_context(ticket, user_query)
        messages = [
            LLMMessage(role="system", content=build_system_prompt(mode)),
            LLMMessage(role="user", content=context),
        ]

        response = await self.adapter.complete(messages)

        # Сохраняем запрос+ответ в журнал ремонта (F-004 шаг 5).
        self.db.add(
            RepairHistory(
                ticket_id=ticket.id,
                user_id=actor_id or ticket.master_id or ticket.receiver_id,
                entry_type=HistoryEntryType.AI_QUERY,
                title=f"AI [{mode}] {self.adapter.provider}/{self.adapter.model}",
                content=f"Q: {user_query}\n\nA: {response.content}",
            )
        )
        if actor_id:
            audit_service.record(
                self.db,
                user_id=actor_id,
                action="AI_DIAGNOSE",
                entity_type="repair_ticket",
                entity_id=ticket.id,
            )
        self.db.commit()

        return {
            "answer": response.content,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used,
            "sources": sources,
        }

    async def _build_context(
        self, ticket: RepairTicket, user_query: str
    ) -> tuple[str, dict]:
        """Собирает контекстный блок §8.2 и список RAG-источников."""
        device = self.db.get(Device, ticket.device_id)
        manufacturer = (
            self.db.get(Manufacturer, device.manufacturer_id) if device else None
        )
        platform = (
            self.db.get(Platform, device.platform_id)
            if device and device.platform_id
            else None
        )

        measurements_table = self._format_measurements(ticket.id)
        history_block = self._format_history(ticket.id)

        # RAG: похожие ремонты и даташиты (§8.3). Деградирует при недоступности.
        rag_repairs, rag_datasheets, sources = "—", "—", {"repairs": [], "datasheets": []}
        if self.retriever is not None:
            search_query = user_query or ticket.problem_description
            try:
                repairs = await self.retriever.similar_repairs(search_query)
                datasheets = await self.retriever.relevant_datasheets(search_query)
                rag_repairs = self._format_chunks(repairs) or "—"
                rag_datasheets = self._format_chunks(datasheets) or "—"
                sources = {
                    "repairs": [r.kb_id for r in repairs],
                    "datasheets": [d.kb_id for d in datasheets],
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("RAG недоступен, продолжаем без него: %s", exc)

        context = CONTEXT_TEMPLATE.format(
            device_manufacturer=manufacturer.name if manufacturer else "—",
            device_model=device.model_name if device else "—",
            platform_name=platform.name if platform else "—",
            problem_description=ticket.problem_description,
            available_tools="—",
            measurements_table=measurements_table,
            repair_history_last_10=history_block,
            rag_similar_repairs=rag_repairs,
            rag_datasheet_chunks=rag_datasheets,
            user_query=user_query or "(режим автоматической рекомендации)",
        )
        return context, sources

    def _format_measurements(self, ticket_id: int) -> str:
        rows = self.db.scalars(
            select(RepairMeasurement)
            .where(RepairMeasurement.ticket_id == ticket_id)
            .order_by(RepairMeasurement.measured_at)
        ).all()
        if not rows:
            return "(измерений нет)"
        lines = ["Линия | Норма | Измерено | Статус", "------|-------|----------|-------"]
        for m in rows:
            lines.append(
                f"{m.line_name} | {m.value_norm or '—'} {m.unit} | "
                f"{m.value_measured} {m.unit} | {m.status.value}"
            )
        return "\n".join(lines)

    def _format_history(self, ticket_id: int, limit: int = 10) -> str:
        rows = self.db.scalars(
            select(RepairHistory)
            .where(RepairHistory.ticket_id == ticket_id)
            .order_by(RepairHistory.created_at.desc())
            .limit(limit)
        ).all()
        if not rows:
            return "(журнал пуст)"
        return "\n".join(
            f"[{r.entry_type.value}] {r.title or ''}: {r.content or ''}"
            for r in reversed(rows)
        )

    @staticmethod
    def _format_chunks(chunks) -> str:
        return "\n---\n".join(
            f"(score={c.score:.2f}) {c.text[:600]}" for c in chunks
        )
