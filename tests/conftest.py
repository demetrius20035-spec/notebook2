"""Общие фикстуры тестов."""
from __future__ import annotations

import base64
import os

import pytest

# Тестовые секреты задаём до импорта настроек.
os.environ.setdefault("JWT_SECRET", base64.b64encode(os.urandom(48)).decode())
os.environ.setdefault("DEVICE_PASSWORD_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture(autouse=True)
def _ensure_keys():
    """Гарантирует наличие ключей шифрования в настройках для каждого теста."""
    from backend.core.config import settings

    if not settings.device_password_key:
        settings.device_password_key = base64.b64encode(os.urandom(32)).decode()
    yield
