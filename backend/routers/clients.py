"""Эндпоинты CRM — клиенты (§2.1, §6.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.client import Client
from backend.models.enums import UserRole
from backend.models.ticket import RepairTicket
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import Meta, ok
from backend.schemas.entities import ClientCreate, ClientOut
from backend.services import audit_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])

_EDIT_ROLES = (UserRole.ADMIN, UserRole.MASTER, UserRole.RECEIVER)


@router.get("")
def list_clients(
    q: str | None = Query(default=None, description="Поиск по ФИО / телефону / email"),
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Client)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Client.full_name.like(like), Client.phone.like(like), Client.email.like(like))
        )
    total = len(db.scalars(stmt).all())
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    return ok(
        [ClientOut.model_validate(c).model_dump() for c in rows],
        meta=Meta(total=total, page=page, per_page=per_page),
    )


@router.post("")
def create_client(
    body: ClientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDIT_ROLES)),
):
    if body.phone and db.scalar(select(Client).where(Client.phone == body.phone)):
        raise HTTPException(status_code=409, detail="Клиент с таким телефоном уже существует")
    client = Client(**body.model_dump())
    db.add(client)
    db.flush()
    audit_service.record(
        db, user_id=user.id, action="CREATE_CLIENT", entity_type="client", entity_id=client.id
    )
    db.commit()
    db.refresh(client)
    return ok(ClientOut.model_validate(client).model_dump())


@router.get("/{client_id}")
def get_client(
    client_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return ok(ClientOut.model_validate(client).model_dump())


@router.get("/{client_id}/tickets")
def client_tickets(
    client_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    rows = db.scalars(
        select(RepairTicket).where(RepairTicket.client_id == client_id)
    ).all()
    return ok([{"id": t.id, "ticket_number": t.ticket_number, "status": t.status.value} for t in rows])
