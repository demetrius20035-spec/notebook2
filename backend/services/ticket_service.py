"""Бизнес-логика тикетов: создание, статусы, измерения (F-001..F-003)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.client import Client
from backend.models.enums import (
    ALLOWED_STATUS_TRANSITIONS,
    ClientTier,
    HistoryEntryType,
    MeasurementPhase,
    MeasurementStatus,
    TicketStatus,
    UserRole,
)
from backend.models.ticket import (
    RepairHistory,
    RepairMeasurement,
    RepairTicket,
    TicketSequence,
)
from backend.services import audit_service

# Допуск для авто-оценки статуса измерения (F-003): ±10%.
_MEASUREMENT_TOLERANCE = Decimal("0.10")
# Поля меток времени, обновляемые при смене статуса.
_STATUS_TIMESTAMP = {
    TicketStatus.DIAGNOSTICS: "diagnostics_at",
    TicketStatus.IN_REPAIR: "started_at",
    TicketStatus.READY: "completed_at",
    TicketStatus.DELIVERED: "delivered_at",
    TicketStatus.CLOSED: "closed_at",
}


class TicketError(ValueError):
    """Нарушение бизнес-правила работы с тикетом."""


# ───────────────────────── BR-003: номер тикета ─────────────────────────
def generate_ticket_number(db: Session, *, year: int | None = None) -> str:
    """Возвращает следующий номер формата РМ-YYYY-NNNNN.

    Использует таблицу-счётчик ``ticket_sequences`` с блокировкой строки.
    """
    year = year or dt.date.today().year
    seq = db.get(TicketSequence, year, with_for_update=True)
    if seq is None:
        seq = TicketSequence(year=year, last_number=0)
        db.add(seq)
        db.flush()
    seq.last_number += 1
    return f"РМ-{year}-{seq.last_number:05d}"


# ─────────────────────────── F-001: создание ───────────────────────────
def create_ticket(
    db: Session,
    *,
    actor_id: int,
    client_id: int,
    device_id: int,
    receiver_id: int,
    problem_description: str,
    master_id: int | None = None,
    priority=None,
    ip_address: str | None = None,
) -> RepairTicket:
    """Создаёт тикет со статусом ``new`` и стартовой записью журнала."""
    if not (5 <= len(problem_description) <= 5000):
        raise TicketError("problem_description должно быть от 5 до 5000 символов")

    now = dt.datetime.now()
    ticket = RepairTicket(
        ticket_number=generate_ticket_number(db),
        client_id=client_id,
        device_id=device_id,
        receiver_id=receiver_id,
        master_id=master_id,
        status=TicketStatus.NEW,
        problem_description=problem_description,
        accepted_at=now,
    )
    if priority is not None:
        ticket.priority = priority
    db.add(ticket)
    db.flush()

    db.add(
        RepairHistory(
            ticket_id=ticket.id,
            user_id=actor_id,
            entry_type=HistoryEntryType.STATUS_CHANGE,
            title="Принят",
            content="Устройство принято на ремонт",
        )
    )
    audit_service.record(
        db,
        user_id=actor_id,
        action="CREATE_TICKET",
        entity_type="repair_ticket",
        entity_id=ticket.id,
        new_value={"ticket_number": ticket.ticket_number},
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(ticket)
    return ticket


# ─────────────────────── F-002: смена статуса ───────────────────────
def change_status(
    db: Session,
    *,
    ticket: RepairTicket,
    new_status: TicketStatus,
    actor_id: int,
    actor_role: UserRole,
    ip_address: str | None = None,
) -> RepairTicket:
    """Меняет статус тикета с проверкой допустимости перехода."""
    old_status = ticket.status
    if new_status == old_status:
        return ticket

    # «любой → closed» разрешён только администратору.
    allowed = ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
    is_admin_force_close = (
        new_status == TicketStatus.CLOSED and actor_role == UserRole.ADMIN
    )
    if new_status not in allowed and not is_admin_force_close:
        raise TicketError(
            f"Недопустимый переход статуса: {old_status.value} → {new_status.value}"
        )

    ticket.status = new_status
    ts_field = _STATUS_TIMESTAMP.get(new_status)
    now = dt.datetime.now()
    if ts_field:
        setattr(ticket, ts_field, now)

    # BR-002: расчёт окончания гарантии при выдаче.
    if new_status == TicketStatus.DELIVERED:
        _set_warranty_expiry(ticket, now)

    db.add(
        RepairHistory(
            ticket_id=ticket.id,
            user_id=actor_id,
            entry_type=HistoryEntryType.STATUS_CHANGE,
            title="Смена статуса",
            content=f"{old_status.value} → {new_status.value}",
        )
    )

    # BR-001: обновление статистики клиента при закрытии.
    if new_status == TicketStatus.CLOSED:
        _bump_client_repairs(db, ticket.client_id)

    audit_service.record(
        db,
        user_id=actor_id,
        action="TICKET_STATUS_CHANGE",
        entity_type="repair_ticket",
        entity_id=ticket.id,
        old_value={"status": old_status.value},
        new_value={"status": new_status.value},
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def _set_warranty_expiry(ticket: RepairTicket, delivered_at: dt.datetime) -> None:
    """BR-002: warranty_expires_at = delivered_at + warranty_months."""
    months = ticket.warranty_months or 0
    base = delivered_at.date()
    month = base.month - 1 + months
    year = base.year + month // 12
    month = month % 12 + 1
    day = min(base.day, _days_in_month(year, month))
    ticket.warranty_expires_at = dt.date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        nxt = dt.date(year + 1, 1, 1)
    else:
        nxt = dt.date(year, month + 1, 1)
    return (nxt - dt.timedelta(days=1)).day


def _bump_client_repairs(db: Session, client_id: int) -> None:
    """BR-001: инкремент total_repairs и пересчёт client_tier."""
    client = db.get(Client, client_id)
    if client is None:
        return
    client.total_repairs = (client.total_repairs or 0) + 1
    if client.total_repairs >= 10:
        client.client_tier = ClientTier.VIP
    elif client.total_repairs >= 3:
        client.client_tier = ClientTier.REGULAR
    else:
        client.client_tier = ClientTier.NEW


# ─────────────────────── F-003: добавление измерения ───────────────────────
def add_measurement(
    db: Session,
    *,
    ticket_id: int,
    actor_id: int,
    line_name: str,
    value_measured: Decimal,
    value_norm: Decimal | None = None,
    unit: str = "V",
    phase: MeasurementPhase = MeasurementPhase.BEFORE,
    notes: str | None = None,
) -> RepairMeasurement:
    """Добавляет измерение и авто-вычисляет статус по допуску ±10%."""
    status = compute_measurement_status(value_measured, value_norm)
    measurement = RepairMeasurement(
        ticket_id=ticket_id,
        user_id=actor_id,
        line_name=line_name,
        value_measured=value_measured,
        value_norm=value_norm,
        unit=unit,
        status=status,
        phase=phase,
        notes=notes,
        measured_at=dt.datetime.now(),
    )
    db.add(measurement)
    db.add(
        RepairHistory(
            ticket_id=ticket_id,
            user_id=actor_id,
            entry_type=HistoryEntryType.MEASUREMENT,
            title=f"Измерение {line_name}",
            content=f"{line_name} = {value_measured} {unit} — {status.value.upper()}",
        )
    )
    db.commit()
    db.refresh(measurement)
    return measurement


def compute_measurement_status(
    value_measured: Decimal | None, value_norm: Decimal | None
) -> MeasurementStatus:
    """Сравнивает измеренное значение с нормой ±10% (F-003)."""
    if value_measured is None or value_norm is None:
        return MeasurementStatus.OK
    value_measured = Decimal(value_measured)
    value_norm = Decimal(value_norm)
    if value_norm == 0:
        # Норма 0 В: любое заметное напряжение — отклонение.
        return MeasurementStatus.OK if abs(value_measured) < Decimal("0.1") else MeasurementStatus.FAIL
    deviation = abs(value_measured - value_norm) / abs(value_norm)
    if deviation <= _MEASUREMENT_TOLERANCE:
        return MeasurementStatus.OK
    if deviation <= _MEASUREMENT_TOLERANCE * 2:
        return MeasurementStatus.WARN
    return MeasurementStatus.FAIL


def get_ticket_by_number(db: Session, ticket_number: str) -> RepairTicket | None:
    return db.scalar(select(RepairTicket).where(RepairTicket.ticket_number == ticket_number))
