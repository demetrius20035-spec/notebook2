"""Тесты бизнес-логики тикетов (F-002, F-003, BR-002)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from backend.models.enums import ALLOWED_STATUS_TRANSITIONS, MeasurementStatus, TicketStatus
from backend.services.ticket_service import (
    _set_warranty_expiry,
    compute_measurement_status,
)


class _FakeTicket:
    warranty_months = 3
    warranty_expires_at = None


def test_measurement_status_ok_within_tolerance():
    assert compute_measurement_status(Decimal("3.3"), Decimal("3.3")) is MeasurementStatus.OK
    assert compute_measurement_status(Decimal("3.4"), Decimal("3.3")) is MeasurementStatus.OK


def test_measurement_status_fail_far_off():
    assert compute_measurement_status(Decimal("0.0"), Decimal("5.0")) is MeasurementStatus.FAIL


def test_measurement_status_warn_between():
    # ~15% отклонение → WARN (между 10% и 20%).
    assert compute_measurement_status(Decimal("5.75"), Decimal("5.0")) is MeasurementStatus.WARN


def test_measurement_status_norm_zero():
    assert compute_measurement_status(Decimal("0.05"), Decimal("0")) is MeasurementStatus.OK
    assert compute_measurement_status(Decimal("1.0"), Decimal("0")) is MeasurementStatus.FAIL


def test_warranty_expiry_adds_months():
    ticket = _FakeTicket()
    _set_warranty_expiry(ticket, dt.datetime(2026, 1, 15, 12, 0))
    assert ticket.warranty_expires_at == dt.date(2026, 4, 15)


def test_warranty_expiry_year_rollover():
    ticket = _FakeTicket()
    ticket.warranty_months = 6
    _set_warranty_expiry(ticket, dt.datetime(2026, 10, 31, 9, 0))
    assert ticket.warranty_expires_at == dt.date(2027, 4, 30)  # апрель — 30 дней


def test_status_transition_table_consistency():
    # Из new можно только в diagnostics.
    assert ALLOWED_STATUS_TRANSITIONS[TicketStatus.NEW] == {TicketStatus.DIAGNOSTICS}
    # Закрытый тикет — терминальный.
    assert ALLOWED_STATUS_TRANSITIONS[TicketStatus.CLOSED] == set()
    # Из delivered — в closed или warranty.
    assert ALLOWED_STATUS_TRANSITIONS[TicketStatus.DELIVERED] == {
        TicketStatus.CLOSED,
        TicketStatus.WARRANTY,
    }
