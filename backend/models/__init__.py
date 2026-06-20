"""ORM-модели RepairExpert AI (§4 спецификации).

Импорт всех моделей здесь гарантирует их регистрацию в ``Base.metadata``
(необходимо для Alembic autogenerate и ``create_all``).
"""
from backend.models.audit import AuditLog, SystemSetting
from backend.models.base import Base
from backend.models.catalog import DeviceModel, DeviceType, Manufacturer, Platform
from backend.models.client import Client
from backend.models.component import Component, ComponentAnalog
from backend.models.device import Device
from backend.models.finance import Payment
from backend.models.inventory import Inventory, InventoryMove, Supplier, SupplierCatalog
from backend.models.knowledge import (
    Attachment,
    Document,
    KnowledgeBase,
    KnowledgeChunk,
)
from backend.models.ticket import (
    RepairHistory,
    RepairMeasurement,
    RepairTicket,
    TicketComponent,
    TicketSequence,
)
from backend.models.user import User

__all__ = [
    "Base",
    "User",
    "Client",
    "Manufacturer",
    "DeviceType",
    "DeviceModel",
    "Platform",
    "Device",
    "RepairTicket",
    "RepairHistory",
    "RepairMeasurement",
    "TicketComponent",
    "TicketSequence",
    "Component",
    "ComponentAnalog",
    "Inventory",
    "InventoryMove",
    "Supplier",
    "SupplierCatalog",
    "KnowledgeBase",
    "KnowledgeChunk",
    "Attachment",
    "Document",
    "Payment",
    "AuditLog",
    "SystemSetting",
]
