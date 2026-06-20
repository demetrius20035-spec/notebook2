"""Аналитика и дашборд (§2.13)."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.client import Client
from backend.models.component import Component
from backend.models.enums import PaymentType, TicketStatus
from backend.models.finance import Payment
from backend.models.inventory import Inventory
from backend.models.ticket import RepairTicket, TicketComponent
from backend.models.user import User
from backend.routers.deps import get_current_user
from backend.schemas.common import ok

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Активные (незакрытые) статусы.
_ACTIVE = (
    TicketStatus.NEW,
    TicketStatus.DIAGNOSTICS,
    TicketStatus.IN_REPAIR,
    TicketStatus.WAITING_PARTS,
    TicketStatus.WAITING_CLIENT,
    TicketStatus.READY,
)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Сводные показатели мастерской для главного экрана."""
    by_status = dict(
        db.execute(
            select(RepairTicket.status, func.count(RepairTicket.id)).group_by(
                RepairTicket.status
            )
        ).all()
    )
    status_counts = {s.value: int(by_status.get(s, 0)) for s in TicketStatus}
    active = sum(int(by_status.get(s, 0)) for s in _ACTIVE)

    since = dt.datetime.now() - dt.timedelta(days=30)
    revenue_30d = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.paid_at >= since, Payment.payment_type != PaymentType.REFUND
        )
    )

    low_stock = db.scalar(
        select(func.count()).select_from(Inventory).where(
            (Inventory.quantity - Inventory.quantity_reserved) < Inventory.min_stock
        )
    )

    # Топ-5 часто заменяемых компонентов.
    top_rows = db.execute(
        select(Component.name, func.coalesce(func.sum(TicketComponent.quantity), 0).label("n"))
        .join(TicketComponent, TicketComponent.component_id == Component.id)
        .group_by(Component.id)
        .order_by(func.sum(TicketComponent.quantity).desc())
        .limit(5)
    ).all()

    return ok(
        {
            "tickets_active": active,
            "tickets_by_status": status_counts,
            "revenue_30d": float(revenue_30d or 0),
            "low_stock_count": int(low_stock or 0),
            "clients_total": int(db.scalar(select(func.count(Client.id))) or 0),
            "top_components": [{"name": n, "count": int(c)} for n, c in top_rows],
        }
    )
