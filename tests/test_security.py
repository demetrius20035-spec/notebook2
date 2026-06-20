"""Тесты криптографии (§10)."""
from __future__ import annotations

import jwt
import pytest

from backend.core.security import (
    create_access_token,
    decode_token,
    decrypt_device_password,
    encrypt_device_password,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("S3cret!")
    assert h != "S3cret!"
    assert verify_password("S3cret!", h)
    assert not verify_password("wrong", h)


def test_jwt_access_token_contains_role():
    token = create_access_token(42, "master")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "master"
    assert payload["type"] == "access"


def test_jwt_rejects_tampered_token():
    token = create_access_token(1, "admin")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token + "x", "another-secret", algorithms=["HS256"])


def test_device_password_aes_roundtrip():
    secret = "0000-пароль-устройства"
    enc = encrypt_device_password(secret)
    assert enc and enc != secret
    assert decrypt_device_password(enc) == secret


def test_device_password_empty():
    assert encrypt_device_password("") == ""
    assert decrypt_device_password("") == ""
