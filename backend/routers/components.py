"""Эндпоинты базы компонентов (§2.7, §6.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.component import Component, ComponentAnalog
from backend.models.enums import UserRole
from backend.models.ticket import TicketComponent
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import ok
from backend.schemas.entities import ComponentCreate, ComponentOut

router = APIRouter(prefix="/api/v1/components", tags=["components"])

_EDIT_ROLES = (UserRole.ADMIN, UserRole.MASTER, UserRole.STOREKEEPER)


@router.get("")
def list_components(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Component)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Component.part_number.like(like), Component.name.like(like)))
    rows = db.scalars(stmt.limit(100)).all()
    return ok([ComponentOut.model_validate(c).model_dump() for c in rows])


@router.post("")
def create_component(
    body: ComponentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_EDIT_ROLES)),
):
    comp = Component(**body.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return ok(ComponentOut.model_validate(comp).model_dump())


@router.get("/{component_id}")
def get_component(
    component_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    comp = db.get(Component, component_id)
    if comp is None:
        raise HTTPException(status_code=404, detail="Компонент не найден")
    return ok(ComponentOut.model_validate(comp).model_dump())


@router.get("/{component_id}/analogs")
def component_analogs(
    component_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """F-006: прямые аналоги компонента."""
    rows = db.scalars(
        select(ComponentAnalog).where(ComponentAnalog.component_id == component_id)
    ).all()
    return ok(
        [
            {
                "analog_id": a.analog_id,
                "compatibility": a.compatibility.value,
                "notes": a.notes,
            }
            for a in rows
        ]
    )


@router.get("/{component_id}/stats")
def component_stats(
    component_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """Статистика использования компонента (§2.7)."""
    times_used = db.scalar(
        select(func.coalesce(func.sum(TicketComponent.quantity), 0)).where(
            TicketComponent.component_id == component_id
        )
    )
    return ok({"component_id": component_id, "times_used": int(times_used or 0)})
