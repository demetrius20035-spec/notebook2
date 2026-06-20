"""Зависимости FastAPI: текущий пользователь и проверка ролей (§3.1)."""
from __future__ import annotations

from collections.abc import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import decode_token
from backend.models.enums import UserRole
from backend.models.user import User

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Извлекает и валидирует пользователя из JWT access-токена."""
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен"
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Ожидался access-токен")

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден или отключён")
    return user


def require_roles(*roles: UserRole):
    """Фабрика зависимостей: доступ только указанным ролям (§3.1)."""
    allowed: Iterable[UserRole] = roles

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции",
            )
        return user

    return checker
