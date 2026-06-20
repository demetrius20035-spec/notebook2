"""Эндпоинты тикетов (§6.4, F-001..F-003)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.enums import TicketStatus, UserRole
from backend.models.ticket import RepairHistory, RepairMeasurement, RepairTicket
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import Meta, ok
from backend.schemas.entities import (
    HistoryEntryCreate,
    MeasurementCreate,
    MeasurementOut,
    TicketCreate,
    TicketOut,
    TicketStatusUpdate,
)
from backend.services import ticket_service
from backend.services.ticket_service import TicketError

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

_CREATE_ROLES = (UserRole.ADMIN, UserRole.MASTER, UserRole.RECEIVER)
_WORK_ROLES = (UserRole.ADMIN, UserRole.MASTER)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("")
def list_tickets(
    status: TicketStatus | None = None,
    master_id: int | None = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(RepairTicket)
    if status:
        stmt = stmt.where(RepairTicket.status == status)
    if master_id:
        stmt = stmt.where(RepairTicket.master_id == master_id)
    total = len(db.scalars(stmt).all())
    rows = db.scalars(
        stmt.order_by(RepairTicket.accepted_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return ok(
        [TicketOut.model_validate(t).model_dump() for t in rows],
        meta=Meta(total=total, page=page, per_page=per_page),
    )


@router.post("")
def create_ticket(
    body: TicketCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_CREATE_ROLES)),
):
    try:
        ticket = ticket_service.create_ticket(
            db,
            actor_id=user.id,
            client_id=body.client_id,
            device_id=body.device_id,
            receiver_id=user.id,
            problem_description=body.problem_description,
            master_id=body.master_id,
            priority=body.priority,
            ip_address=_client_ip(request),
        )
    except TicketError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ok(TicketOut.model_validate(ticket).model_dump())


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    ticket = db.get(RepairTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    return ok(TicketOut.model_validate(ticket).model_dump())


@router.post("/{ticket_id}/status")
def change_status(
    ticket_id: int,
    body: TicketStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_WORK_ROLES)),
):
    ticket = db.get(RepairTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    try:
        ticket = ticket_service.change_status(
            db,
            ticket=ticket,
            new_status=body.status,
            actor_id=user.id,
            actor_role=user.role,
            ip_address=_client_ip(request),
        )
    except TicketError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ok(TicketOut.model_validate(ticket).model_dump())


@router.post("/{ticket_id}/measurements")
def add_measurement(
    ticket_id: int,
    body: MeasurementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_WORK_ROLES)),
):
    if db.get(RepairTicket, ticket_id) is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    m = ticket_service.add_measurement(
        db,
        ticket_id=ticket_id,
        actor_id=user.id,
        line_name=body.line_name,
        value_measured=body.value_measured,
        value_norm=body.value_norm,
        unit=body.unit,
        phase=body.phase,
        notes=body.notes,
    )
    return ok(MeasurementOut.model_validate(m).model_dump())


@router.get("/{ticket_id}/measurements")
def list_measurements(
    ticket_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    rows = db.scalars(
        select(RepairMeasurement).where(RepairMeasurement.ticket_id == ticket_id)
    ).all()
    return ok([MeasurementOut.model_validate(m).model_dump() for m in rows])


@router.post("/{ticket_id}/history")
def add_history(
    ticket_id: int,
    body: HistoryEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_WORK_ROLES)),
):
    if db.get(RepairTicket, ticket_id) is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    entry = RepairHistory(
        ticket_id=ticket_id,
        user_id=user.id,
        entry_type=body.entry_type,
        title=body.title,
        content=body.content,
        duration_sec=body.duration_sec,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ok({"id": entry.id})


@router.get("/{ticket_id}/history")
def list_history(
    ticket_id: int,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(RepairHistory)
        .where(RepairHistory.ticket_id == ticket_id)
        .order_by(RepairHistory.created_at)
        .limit(limit)
    ).all()
    return ok(
        [
            {
                "id": r.id,
                "type": r.entry_type.value,
                "title": r.title,
                "content": r.content,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    )
