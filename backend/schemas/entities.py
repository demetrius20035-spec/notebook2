"""Pydantic-схемы основных сущностей API."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import (
    MeasurementPhase,
    TicketPriority,
    TicketStatus,
)


# ── Клиенты ──
class ClientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = None
    address: str | None = None
    notes: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str | None
    email: str | None
    client_tier: str
    total_repairs: int
    is_blacklisted: bool


# ── Тикеты ──
class TicketCreate(BaseModel):
    client_id: int
    device_id: int
    problem_description: str = Field(min_length=5, max_length=5000)
    priority: TicketPriority = TicketPriority.NORMAL
    master_id: int | None = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    client_id: int
    device_id: int
    status: TicketStatus
    priority: TicketPriority
    problem_description: str
    cost_estimate: Decimal
    cost_final: Decimal
    warranty_expires_at: dt.date | None
    accepted_at: dt.datetime | None


# ── Измерения ──
class MeasurementCreate(BaseModel):
    line_name: str = Field(max_length=100)
    value_measured: Decimal
    value_norm: Decimal | None = None
    unit: str = "V"
    phase: MeasurementPhase = MeasurementPhase.BEFORE
    notes: str | None = None


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_name: str
    value_measured: Decimal | None
    value_norm: Decimal | None
    unit: str
    status: str
    phase: MeasurementPhase


# ── Журнал ──
class HistoryEntryCreate(BaseModel):
    entry_type: str
    title: str | None = None
    content: str | None = None
    duration_sec: int | None = None


# ── AI ──
class DiagnoseRequest(BaseModel):
    ticket_id: int
    mode: str = Field(default="next_step", pattern="^(next_step|chat|wizard)$")
    query: str = ""
    provider: str | None = None
    model: str | None = None


class SemanticSearchRequest(BaseModel):
    query: str
    collection: str = "repair_vectors"
    top_k: int = 5


# ── Компоненты ──
class ComponentCreate(BaseModel):
    part_number: str | None = None
    name: str = Field(max_length=200)
    category: str = Field(max_length=80)
    manufacturer: str | None = None
    package_type: str | None = None
    description: str | None = None


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_number: str | None
    name: str
    category: str
    manufacturer: str | None
    package_type: str | None
