"""Тикеты, журнал ремонта, карта измерений, использованные компоненты.

Соответствует §4.4–4.6 и F-001..F-003 спецификации.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.enums import (
    HistoryEntryType,
    MeasurementPhase,
    MeasurementStatus,
    TicketPriority,
    TicketStatus,
)
from backend.models.mixins import CreatedAtMixin


class TicketSequence(Base):
    """Сквозной счётчик номеров тикетов по годам (BR-003)."""

    __tablename__ = "ticket_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RepairTicket(Base):
    __tablename__ = "repair_tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    master_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), nullable=False, default=TicketStatus.NEW
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority), default=TicketPriority.NORMAL
    )
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostic_result: Mapped[str | None] = mapped_column(Text)
    repair_description: Mapped[str | None] = mapped_column(Text)
    cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    cost_final: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    warranty_months: Mapped[int] = mapped_column(Integer, default=3)
    warranty_expires_at: Mapped[dt.date | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text)

    accepted_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    diagnostics_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)

    client = relationship("Client", back_populates="tickets")
    device = relationship("Device")
    history = relationship(
        "RepairHistory", back_populates="ticket", cascade="all, delete-orphan"
    )
    measurements = relationship(
        "RepairMeasurement", back_populates="ticket", cascade="all, delete-orphan"
    )
    used_components = relationship(
        "TicketComponent", back_populates="ticket", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="ticket")


class RepairHistory(Base, CreatedAtMixin):
    """Журнал действий по ремонту (§4.5)."""

    __tablename__ = "repair_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("repair_tickets.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entry_type: Mapped[HistoryEntryType] = mapped_column(Enum(HistoryEntryType), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text)
    duration_sec: Mapped[int | None] = mapped_column(Integer)

    ticket = relationship("RepairTicket", back_populates="history")


class RepairMeasurement(Base):
    """Карта измерений напряжений/токов/сопротивлений (§4.6)."""

    __tablename__ = "repair_measurements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("repair_tickets.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    line_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_measured: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    value_norm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    unit: Mapped[str] = mapped_column(String(20), default="V")
    status: Mapped[MeasurementStatus] = mapped_column(
        Enum(MeasurementStatus), default=MeasurementStatus.OK
    )
    notes: Mapped[str | None] = mapped_column(String(255))
    measured_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    phase: Mapped[MeasurementPhase] = mapped_column(
        Enum(MeasurementPhase), default=MeasurementPhase.BEFORE
    )

    ticket = relationship("RepairTicket", back_populates="measurements")


class TicketComponent(Base):
    """Компоненты, использованные в ремонте (ТЗ §2.3)."""

    __tablename__ = "ticket_components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("repair_tickets.id"), nullable=False)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    ticket = relationship("RepairTicket", back_populates="used_components")
    component = relationship("Component")
