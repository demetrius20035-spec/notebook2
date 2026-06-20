"""Справочники и устройства: производители, типы, платформы, устройства."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import encrypt_device_password
from backend.models.catalog import DeviceType, Manufacturer, Platform
from backend.models.device import Device
from backend.models.enums import UserRole
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import ok
from backend.schemas.more import DeviceCreate, NamedCreate, PlatformCreate

router = APIRouter(prefix="/api/v1", tags=["catalog"])

_EDIT = (UserRole.ADMIN, UserRole.MASTER, UserRole.RECEIVER)


def get_or_create_manufacturer(db: Session, name: str) -> Manufacturer:
    obj = db.scalar(select(Manufacturer).where(Manufacturer.name == name))
    if obj is None:
        obj = Manufacturer(name=name)
        db.add(obj)
        db.flush()
    return obj


def get_or_create_platform(db: Session, name: str) -> Platform:
    obj = db.scalar(select(Platform).where(Platform.name == name))
    if obj is None:
        obj = Platform(name=name)
        db.add(obj)
        db.flush()
    return obj


# ── Производители ──
@router.get("/manufacturers")
def list_manufacturers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(Manufacturer).order_by(Manufacturer.name)).all()
    return ok([{"id": m.id, "name": m.name} for m in rows])


@router.post("/manufacturers")
def create_manufacturer(
    body: NamedCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(*_EDIT))
):
    obj = get_or_create_manufacturer(db, body.name)
    db.commit()
    return ok({"id": obj.id, "name": obj.name})


# ── Типы устройств ──
@router.get("/device-types")
def list_device_types(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(DeviceType).order_by(DeviceType.name)).all()
    return ok([{"id": t.id, "name": t.name} for t in rows])


@router.post("/device-types")
def create_device_type(
    body: NamedCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(*_EDIT))
):
    obj = db.scalar(select(DeviceType).where(DeviceType.name == body.name))
    if obj is None:
        obj = DeviceType(name=body.name)
        db.add(obj)
        db.commit()
    return ok({"id": obj.id, "name": obj.name})


# ── Платформы ──
@router.get("/platforms")
def list_platforms(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(Platform).order_by(Platform.name)).all()
    return ok([{"id": p.id, "name": p.name, "description": p.description} for p in rows])


@router.post("/platforms")
def create_platform(
    body: PlatformCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(*_EDIT))
):
    obj = Platform(**body.model_dump())
    db.add(obj)
    db.commit()
    return ok({"id": obj.id, "name": obj.name})


# ── Устройства ──
@router.post("/devices")
def create_device(
    body: DeviceCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(*_EDIT))
):
    if db.get(DeviceType, body.device_type_id) is None:
        raise HTTPException(status_code=422, detail="Неизвестный тип устройства")
    manufacturer = get_or_create_manufacturer(db, body.manufacturer)
    platform = get_or_create_platform(db, body.platform) if body.platform else None
    device = Device(
        client_id=body.client_id,
        device_type_id=body.device_type_id,
        manufacturer_id=manufacturer.id,
        model_name=body.model_name,
        platform_id=platform.id if platform else None,
        serial_number=body.serial_number,
        imei=body.imei,
        device_password=encrypt_device_password(body.device_password or ""),
        condition_note=body.condition_note,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return ok({"id": device.id, "model_name": device.model_name})


@router.get("/devices/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    d = db.get(Device, device_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    manufacturer = db.get(Manufacturer, d.manufacturer_id)
    platform = db.get(Platform, d.platform_id) if d.platform_id else None
    return ok(
        {
            "id": d.id,
            "model_name": d.model_name,
            "manufacturer": manufacturer.name if manufacturer else None,
            "platform": platform.name if platform else None,
            "serial_number": d.serial_number,
            "imei": d.imei,
        }
    )
