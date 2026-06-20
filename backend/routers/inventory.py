"""Склад и поставщики (§2.9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.component import Component
from backend.models.enums import InventoryMoveType, UserRole
from backend.models.inventory import Inventory, InventoryMove, Supplier
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import ok
from backend.schemas.more import InventoryMoveCreate, InventoryUpsert, SupplierCreate
from backend.services import audit_service

router = APIRouter(prefix="/api/v1", tags=["inventory"])

_STORE = (UserRole.ADMIN, UserRole.STOREKEEPER)


@router.get("/inventory")
def list_inventory(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(Inventory)).all()
    out = []
    for inv in rows:
        comp = db.get(Component, inv.component_id)
        out.append(
            {
                "component_id": inv.component_id,
                "name": comp.name if comp else "—",
                "part_number": comp.part_number if comp else None,
                "quantity": inv.quantity,
                "reserved": inv.quantity_reserved,
                "available": inv.quantity_available,
                "min_stock": inv.min_stock,
                "low_stock": inv.is_low_stock,
                "location": inv.location,
                "price_sale": float(inv.price_sale) if inv.price_sale is not None else None,
            }
        )
    return ok(out)


@router.post("/inventory")
def upsert_inventory(
    body: InventoryUpsert, db: Session = Depends(get_db), _: User = Depends(require_roles(*_STORE))
):
    if db.get(Component, body.component_id) is None:
        raise HTTPException(status_code=422, detail="Компонент не найден")
    inv = db.get(Inventory, body.component_id)
    if inv is None:
        inv = Inventory(component_id=body.component_id)
        db.add(inv)
    inv.quantity = body.quantity
    inv.min_stock = body.min_stock
    inv.price_purchase = body.price_purchase
    inv.price_sale = body.price_sale
    inv.location = body.location
    db.commit()
    return ok({"component_id": inv.component_id, "available": inv.quantity_available})


@router.post("/inventory/moves")
def create_move(
    body: InventoryMoveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_STORE)),
):
    """Приход/расход со склада с пересчётом остатка (ТЗ §2.9)."""
    inv = db.get(Inventory, body.component_id)
    if inv is None:
        if db.get(Component, body.component_id) is None:
            raise HTTPException(status_code=422, detail="Компонент не найден")
        inv = Inventory(component_id=body.component_id, quantity=0)
        db.add(inv)
        db.flush()

    if body.move_type == InventoryMoveType.IN:
        inv.quantity += body.quantity
    else:
        if inv.quantity < body.quantity:
            raise HTTPException(status_code=409, detail="Недостаточно остатка на складе")
        inv.quantity -= body.quantity

    db.add(
        InventoryMove(
            component_id=body.component_id,
            user_id=user.id,
            move_type=body.move_type,
            quantity=body.quantity,
            unit_price=body.unit_price,
            notes=body.notes,
        )
    )
    audit_service.record(
        db, user_id=user.id, action="INVENTORY_MOVE",
        entity_type="component", entity_id=body.component_id,
        new_value={"type": body.move_type.value, "qty": body.quantity},
    )
    db.commit()
    return ok({"component_id": inv.component_id, "quantity": inv.quantity})


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(Supplier).where(Supplier.is_active)).all()
    return ok(
        [
            {"id": s.id, "name": s.name, "phone": s.phone, "email": s.email,
             "country": s.country, "website": s.website}
            for s in rows
        ]
    )


@router.post("/suppliers")
def create_supplier(
    body: SupplierCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(*_STORE))
):
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return ok({"id": s.id, "name": s.name})
