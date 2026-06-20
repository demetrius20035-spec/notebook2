"""Журнал аудита и таблица системных настроек (§4.14, §10.2)."""
from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
from backend.models.mixins import CreatedAtMixin


class AuditLog(Base, CreatedAtMixin):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))


class SystemSetting(Base):
    """Хранилище настроек системы.

    Используется в том числе для зашифрованных API-ключей LLM (§10.2):
    значение шифруется на уровне приложения перед сохранением.
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    is_encrypted: Mapped[bool] = mapped_column(default=False)
