"""Криптографические примитивы системы.

Реализует требования §10 спецификации:
- bcrypt-хэширование паролей пользователей (cost factor = 12);
- JWT HS256 для сессий;
- AES-256-GCM для шифрования паролей устройств клиентов.
"""
from __future__ import annotations

import base64
import datetime as dt
import os
from typing import Any

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.core.config import settings

# bcrypt: cost factor ≥ 12 (см. §10.1).
_BCRYPT_ROUNDS = 12


# ──────────────────────────── Пароли пользователей ─────────────────────────
def hash_password(password: str) -> str:
    """Возвращает bcrypt-хэш пароля."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет соответствие пароля его хэшу."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ──────────────────────────────── JWT-сессии ───────────────────────────────
def create_access_token(subject: str | int, role: str, extra: dict | None = None) -> str:
    """Создаёт access_token со сроком жизни из настроек (8 ч по умолчанию)."""
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + dt.timedelta(hours=settings.jwt_expire_hours),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(subject: str | int) -> str:
    """Создаёт refresh_token («Запомнить меня», 30 дней по умолчанию)."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(subject),
        "type": "refresh",
        "iat": now,
        "exp": now + dt.timedelta(days=settings.jwt_refresh_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует и валидирует JWT. Пробрасывает jwt-исключения наверх."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


# ────────────────────── AES-256-GCM для паролей устройств ───────────────────
def _device_key() -> bytes:
    """Возвращает 32-байтный ключ AES из настроек (base64)."""
    raw = settings.device_password_key
    if not raw:
        raise RuntimeError(
            "DEVICE_PASSWORD_KEY не задан. Сгенерируйте ключ: "
            "`python -m backend.core.security`"
        )
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("DEVICE_PASSWORD_KEY должен быть 32 байта (base64) для AES-256.")
    return key


def encrypt_device_password(plaintext: str) -> str:
    """Шифрует пароль устройства (AES-256-GCM). Возвращает base64(nonce|ct)."""
    if not plaintext:
        return ""
    aes = AESGCM(_device_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_device_password(token: str) -> str:
    """Расшифровывает значение, полученное из :func:`encrypt_device_password`."""
    if not token:
        return ""
    blob = base64.b64decode(token)
    nonce, ct = blob[:12], blob[12:]
    aes = AESGCM(_device_key())
    return aes.decrypt(nonce, ct, None).decode("utf-8")


def generate_device_key() -> str:
    """Утилита: генерирует новый base64-ключ AES-256."""
    return base64.b64encode(os.urandom(32)).decode("ascii")


if __name__ == "__main__":  # pragma: no cover
    print("DEVICE_PASSWORD_KEY=", generate_device_key())
    print("JWT_SECRET=", base64.b64encode(os.urandom(48)).decode("ascii"))
