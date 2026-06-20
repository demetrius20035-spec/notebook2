"""Общие схемы API-ответа (§6.4)."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class Meta(BaseModel):
    total: int | None = None
    page: int | None = None
    per_page: int | None = None


class APIResponse(BaseModel, Generic[T]):
    """Унифицированный конверт ответа: {status, data, meta, error}."""

    status: str = "ok"
    data: T | None = None
    meta: Meta | None = None
    error: ErrorInfo | None = None


def ok(data: Any = None, meta: Meta | None = None) -> dict:
    return {"status": "ok", "data": data, "meta": meta, "error": None}


def fail(code: str, message: str, details: dict | None = None) -> dict:
    return {
        "status": "error",
        "data": None,
        "meta": None,
        "error": {"code": code, "message": message, "details": details or {}},
    }
