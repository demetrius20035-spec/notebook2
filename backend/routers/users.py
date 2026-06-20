"""Пользователи: профиль и управление (§3.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import hash_password
from backend.models.enums import UserRole
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import ok
from backend.services import audit_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4)
    full_name: str = Field(min_length=1, max_length=150)
    role: UserRole = UserRole.MASTER
    phone: str | None = None
    email: str | None = None


def _serialize(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role.value,
        "is_active": u.is_active,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(_serialize(user))


@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(User).where(User.is_active)).all()
    return ok([_serialize(u) for u in rows])


@router.post("")
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status_code=409, detail="Пользователь уже существует")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        phone=body.phone,
        email=body.email,
    )
    db.add(user)
    db.flush()
    audit_service.record(
        db, user_id=actor.id, action="UPDATE_USER", entity_type="user", entity_id=user.id,
        new_value={"username": user.username, "role": user.role.value},
    )
    db.commit()
    db.refresh(user)
    return ok(_serialize(user))
