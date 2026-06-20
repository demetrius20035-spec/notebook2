"""Справочники: производители, типы устройств, модели, платформы (§5 ТЗ).

Платформы ноутбуков (ТЗ §2.8): каталог плат LA-XXXX, NM-XXXX, DA0XXXX
с привязкой схем/boardview и типовыми точками измерения.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class DeviceType(Base):
    __tablename__ = "device_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    # ноутбук, смартфон, планшет, материнская плата, блок питания, монитор, другое


class Platform(Base):
    """Ревизия платы устройства (NM-D221, LA-B181P, …)."""

    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    manufacturer_id: Mapped[int | None] = mapped_column(ForeignKey("manufacturers.id"))
    description: Mapped[str | None] = mapped_column(Text)
    schematic_path: Mapped[str | None] = mapped_column(String(512))
    boardview_path: Mapped[str | None] = mapped_column(String(512))


class DeviceModel(Base):
    """Модель устройства с привязкой к платформе."""

    __tablename__ = "device_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"), nullable=False)
    device_type_id: Mapped[int] = mapped_column(ForeignKey("device_types.id"), nullable=False)
    platform_id: Mapped[int | None] = mapped_column(ForeignKey("platforms.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    release_year: Mapped[int | None] = mapped_column()

    platform = relationship("Platform")
