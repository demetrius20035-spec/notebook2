"""Перечисления, соответствующие ENUM-полям спецификации (§4, §5)."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MASTER = "master"
    RECEIVER = "receiver"
    STOREKEEPER = "storekeeper"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class ClientTier(str, enum.Enum):
    NEW = "new"
    REGULAR = "regular"
    VIP = "vip"


class TicketStatus(str, enum.Enum):
    NEW = "new"                      # Принят
    DIAGNOSTICS = "diagnostics"      # Диагностика
    IN_REPAIR = "in_repair"          # В работе
    WAITING_PARTS = "waiting_parts"  # Ожидание деталей
    WAITING_CLIENT = "waiting_client"  # Ожидание клиента
    READY = "ready"                  # Готов
    DELIVERED = "delivered"          # Выдан
    CLOSED = "closed"                # Закрыт
    WARRANTY = "warranty"            # Гарантийный случай


class TicketPriority(str, enum.Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class HistoryEntryType(str, enum.Enum):
    MEASUREMENT = "measurement"
    REPLACEMENT = "replacement"
    NOTE = "note"
    AI_QUERY = "ai_query"
    PHOTO = "photo"
    SOLDER = "solder"
    FLASH = "flash"
    TEST = "test"
    STATUS_CHANGE = "status_change"
    PAYMENT = "payment"


class MeasurementStatus(str, enum.Enum):
    OK = "ok"
    FAIL = "fail"
    WARN = "warn"


class MeasurementPhase(str, enum.Enum):
    BEFORE = "before"
    DURING = "during"
    AFTER = "after"


class CompatibilityLevel(str, enum.Enum):
    FULL = "full"
    PARTIAL = "partial"
    PINOUT_DIFF = "pinout_diff"


class KnowledgeSourceType(str, enum.Enum):
    ARTICLE = "article"
    DATASHEET = "datasheet"
    MANUAL = "manual"
    NOTE = "note"
    REPAIR_CASE = "repair_case"
    FORUM = "forum"


class PaymentType(str, enum.Enum):
    PREPAYMENT = "prepayment"
    FINAL = "final"
    REFUND = "refund"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    OTHER = "other"


class InventoryMoveType(str, enum.Enum):
    IN = "in"            # приход
    OUT = "out"          # расход
    WRITE_OFF = "write_off"  # списание в ремонт
    RETURN = "return"    # возврат


# Допустимые переходы статусов тикета (F-002).
ALLOWED_STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.DIAGNOSTICS},
    TicketStatus.DIAGNOSTICS: {
        TicketStatus.IN_REPAIR,
        TicketStatus.WAITING_PARTS,
        TicketStatus.WAITING_CLIENT,
    },
    TicketStatus.IN_REPAIR: {
        TicketStatus.WAITING_PARTS,
        TicketStatus.WAITING_CLIENT,
        TicketStatus.READY,
    },
    TicketStatus.WAITING_PARTS: {TicketStatus.IN_REPAIR},
    TicketStatus.WAITING_CLIENT: {TicketStatus.IN_REPAIR},
    TicketStatus.READY: {TicketStatus.DELIVERED},
    TicketStatus.DELIVERED: {TicketStatus.CLOSED, TicketStatus.WARRANTY},
    TicketStatus.WARRANTY: {TicketStatus.IN_REPAIR},
    TicketStatus.CLOSED: set(),
}
