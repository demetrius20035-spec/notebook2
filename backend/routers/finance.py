"""Финансовый модуль: платежи и отчёты (§2.10)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.enums import HistoryEntryType, PaymentType, UserRole
from backend.models.finance import Payment
from backend.models.ticket import RepairHistory, RepairTicket
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import ok
from backend.schemas.more import PaymentCreate

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])

_PAY_ROLES = (UserRole.ADMIN, UserRole.MASTER, UserRole.RECEIVER)
_REPORT_ROLES = (UserRole.ADMIN, UserRole.ACCOUNTANT)


@router.get("/payments")
def list_payments(
    ticket_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Payment).order_by(Payment.paid_at.desc())
    if ticket_id:
        stmt = stmt.where(Payment.ticket_id == ticket_id)
    rows = db.scalars(stmt.limit(500)).all()
    return ok(
        [
            {
                "id": p.id,
                "ticket_id": p.ticket_id,
                "amount": float(p.amount),
                "type": p.payment_type.value,
                "method": p.method.value,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in rows
        ]
    )


@router.post("/payments")
def add_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_PAY_ROLES)),
):
    ticket = db.get(RepairTicket, body.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    payment = Payment(
        ticket_id=body.ticket_id,
        user_id=user.id,
        amount=body.amount,
        payment_type=body.payment_type,
        method=body.method,
        notes=body.notes,
    )
    db.add(payment)

    # Возврат уменьшает оплаченную сумму, остальное — увеличивает.
    delta = -body.amount if body.payment_type == PaymentType.REFUND else body.amount
    ticket.paid_amount = (ticket.paid_amount or Decimal("0.00")) + delta

    db.add(
        RepairHistory(
            ticket_id=ticket.id,
            user_id=user.id,
            entry_type=HistoryEntryType.PAYMENT,
            title="Оплата",
            content=f"{body.payment_type.value}: {body.amount} ({body.method.value})",
        )
    )
    db.commit()
    db.refresh(payment)
    return ok({"id": payment.id, "ticket_paid": float(ticket.paid_amount)})


@router.get("/report")
def revenue_report(
    days: int = 30,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_REPORT_ROLES)),
):
    """Сводка по выручке за период (§2.10)."""
    since = dt.datetime.now() - dt.timedelta(days=days)
    total = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.paid_at >= since, Payment.payment_type != PaymentType.REFUND
        )
    )
    refunds = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.paid_at >= since, Payment.payment_type == PaymentType.REFUND
        )
    )
    count = db.scalar(select(func.count(Payment.id)).where(Payment.paid_at >= since))
    return ok(
        {
            "days": days,
            "revenue": float(total or 0),
            "refunds": float(refunds or 0),
            "net": float((total or 0) - (refunds or 0)),
            "payments_count": int(count or 0),
        }
    )
