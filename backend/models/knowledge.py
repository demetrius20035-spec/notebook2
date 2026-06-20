"""База знаний, чанки для RAG, вложения и документы (§4.10, §4.11, F-007)."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import KnowledgeSourceType
from backend.models.mixins import CreatedAtMixin


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(MEDIUMTEXT)
    source_type: Mapped[KnowledgeSourceType] = mapped_column(
        Enum(KnowledgeSourceType), nullable=False
    )
    source_ref_id: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list | None] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    chunks = relationship(
        "KnowledgeChunk", back_populates="kb", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base, CreatedAtMixin):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("kb_id", "chunk_index", name="uq_kb_chunk"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    token_count: Mapped[int | None] = mapped_column(Integer)

    kb = relationship("KnowledgeBase", back_populates="chunks")


class Attachment(Base, CreatedAtMixin):
    """Вложения: фото, осциллограммы, дампы BIOS (§2.12)."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("repair_tickets.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(50))  # photos|oscillograms|bios_dumps
    size_bytes: Mapped[int | None] = mapped_column(Integer)


class Document(Base, CreatedAtMixin):
    """Сгенерированные PDF-документы (F-007, §9)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("repair_tickets.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
