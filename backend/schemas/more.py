"""Дополнительные схемы запросов для расширенных эндпоинтов."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from backend.models.enums import InventoryMoveType, PaymentMethod, PaymentType


# ── Справочники ──
class NamedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class PlatformCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    manufacturer_id: int | None = None
    description: str | None = None


# ── Устройства ──
class DeviceCreate(BaseModel):
    client_id: int | None = None
    device_type_id: int
    manufacturer: str = Field(min_length=1, max_length=120)
    model_name: str = Field(min_length=1, max_length=150)
    platform: str | None = None
    serial_number: str | None = None
    imei: str | None = None
    device_password: str | None = None
    condition_note: str | None = None


# ── База знаний ──
class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    source_type: str = "article"
    tags: list[str] | None = None


# ── Склад ──
class InventoryUpsert(BaseModel):
    component_id: int
    quantity: int = 0
    min_stock: int = 5
    price_purchase: Decimal | None = None
    price_sale: Decimal | None = None
    location: str | None = None


class InventoryMoveCreate(BaseModel):
    component_id: int
    move_type: InventoryMoveType
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = None
    notes: str | None = None


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    contact_person: str | None = None
    country: str | None = None


# ── Финансы ──
class PaymentCreate(BaseModel):
    ticket_id: int
    amount: Decimal = Field(gt=0)
    payment_type: PaymentType = PaymentType.FINAL
    method: PaymentMethod = PaymentMethod.CASH
    notes: str | None = None


# ── Документы ──
class DocumentGenerateRequest(BaseModel):
    document_type: str = Field(pattern="^(acceptance|act|defect|warranty)$")
