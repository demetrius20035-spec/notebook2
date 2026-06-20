"""Модель клиентов (§4.2)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import ClientTier


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True)
    email: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[str | None] = mapped_column(Text)
    client_tier: Mapped[ClientTier] = mapped_column(Enum(ClientTier), default=ClientTier.NEW)
    total_repairs: Mapped[int] = mapped_column(Integer, default=0)
    total_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))

    devices = relationship("Device", back_populates="client")
    tickets = relationship("RepairTicket", back_populates="client")
