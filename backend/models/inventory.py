"""Склад, движения, поставщики и их каталог (§4.9, §4.12, ТЗ §2.9)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.enums import InventoryMoveType
from backend.models.mixins import CreatedAtMixin


class Inventory(Base):
    """Остатки на складе (§4.9). PK = component_id."""

    __tablename__ = "inventory"

    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0)
    min_stock: Mapped[int] = mapped_column(Integer, default=5)
    price_purchase: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_sale: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    location: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    component = relationship("Component")

    @property
    def quantity_available(self) -> int:
        """BR-004: доступно = всего − зарезервировано."""
        return self.quantity - self.quantity_reserved

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_available < self.min_stock


class InventoryMove(Base, CreatedAtMixin):
    """Приходные/расходные операции со складом."""

    __tablename__ = "inventory_moves"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    move_type: Mapped[InventoryMoveType] = mapped_column(Enum(InventoryMoveType), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("repair_tickets.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(String(255))


class Supplier(Base, CreatedAtMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(100))
    contact_person: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(80))
    delivery_days: Mapped[int | None] = mapped_column(Integer)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SupplierCatalog(Base):
    """Каталог компонентов от поставщика с ценами (ТЗ §2.9)."""

    __tablename__ = "supplier_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), nullable=False)
    supplier_sku: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    in_stock: Mapped[int | None] = mapped_column(Integer)
