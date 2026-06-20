"""Подключение к MariaDB через SQLAlchemy 2.x."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings

# READ-COMMITTED — согласно §12.2 спецификации.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    isolation_level="READ COMMITTED",
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: сессия БД на запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
