"""Модель устройств клиентов (§4.3)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.mixins import CreatedAtMixin


class Device(Base, CreatedAtMixin):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    device_type_id: Mapped[int] = mapped_column(ForeignKey("device_types.id"), nullable=False)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    platform_id: Mapped[int | None] = mapped_column(ForeignKey("platforms.id"))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    imei: Mapped[str | None] = mapped_column(String(20))
    imei2: Mapped[str | None] = mapped_column(String(20))
    # AES-256-GCM, base64(nonce|ciphertext) — см. backend.core.security
    device_password: Mapped[str | None] = mapped_column(String(512))
    condition_note: Mapped[str | None] = mapped_column(Text)

    client = relationship("Client", back_populates="devices")
    platform = relationship("Platform")
