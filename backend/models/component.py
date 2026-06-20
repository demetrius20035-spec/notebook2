"""Справочник компонентов и их аналогов (§4.7, §4.8)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import CompatibilityLevel


class Component(Base, TimestampMixin):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(100))
    package_type: Mapped[str | None] = mapped_column(String(50))
    voltage_max: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    current_max: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    resistance: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    frequency: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    extra_params: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    datasheet_path: Mapped[str | None] = mapped_column(String(512))
    embedding_id: Mapped[str | None] = mapped_column(String(100))

    analogs = relationship(
        "ComponentAnalog",
        foreign_keys="ComponentAnalog.component_id",
        back_populates="component",
        cascade="all, delete-orphan",
    )


class ComponentAnalog(Base):
    __tablename__ = "component_analogs"
    __table_args__ = (UniqueConstraint("component_id", "analog_id", name="uq_analog_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), nullable=False)
    analog_id: Mapped[int] = mapped_column(ForeignKey("components.id"), nullable=False)
    compatibility: Mapped[CompatibilityLevel] = mapped_column(
        Enum(CompatibilityLevel), default=CompatibilityLevel.FULL
    )
    notes: Mapped[str | None] = mapped_column(String(255))

    component = relationship(
        "Component", foreign_keys=[component_id], back_populates="analogs"
    )
    analog = relationship("Component", foreign_keys=[analog_id])
