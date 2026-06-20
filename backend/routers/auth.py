"""Эндпоинты аутентификации (§6.4, §10.1)."""
from __future__ import annotations

import datetime as dt

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from backend.models.user import User
from backend.schemas.auth import LoginRequest, TokenResponse
from backend.schemas.common import ok
from backend.services import audit_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Проверяет учётные данные и выдаёт JWT."""
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись отключена")

    access = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id) if body.remember_me else None

    user.last_login_at = dt.datetime.now()
    audit_service.record(
        db,
        user_id=user.id,
        action="AUTH_LOGIN",
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return ok(
        TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.jwt_expire_hours * 3600,
        ).model_dump()
    )


@router.post("/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    """Обновляет access-токен по действующему refresh-токену."""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Недействительный refresh-токен") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Ожидался refresh-токен")

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь недоступен")

    access = create_access_token(user.id, user.role.value)
    return ok(
        TokenResponse(
            access_token=access, expires_in=settings.jwt_expire_hours * 3600
        ).model_dump()
    )


@router.post("/logout")
def logout():
    """Выход (клиент удаляет токен; серверная инвалидация — через ротацию)."""
    return ok({"message": "Сессия завершена"})
