"""Быстрая инициализация окружения разработки.

Создаёт таблицы (без Alembic), коллекции Qdrant и администратора.
Для продакшена используйте Alembic-миграции.

Запуск:
    python -m scripts.bootstrap --admin-password "Secret123"
"""
from __future__ import annotations

import argparse
import sys

from backend.core.config import settings
from backend.core.database import SessionLocal, engine
from backend.core.security import hash_password
from backend.models import Base, User
from backend.models.enums import UserRole


def create_schema() -> None:
    print(f"→ Создание схемы в {settings.db_name} …")
    Base.metadata.create_all(bind=engine)
    print("  ✔ таблицы созданы")


def create_qdrant_collections() -> None:
    try:
        from backend.rag.vector_store import VectorStore

        VectorStore().ensure_collections()
        print("  ✔ коллекции Qdrant готовы")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Qdrant недоступен ({exc}); пропускаю")


def create_admin(username: str, password: str, full_name: str) -> None:
    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"  • администратор '{username}' уже существует")
            return
        admin = User(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        print(f"  ✔ создан администратор '{username}'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap RepairExpert AI")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--admin-name", default="Администратор")
    parser.add_argument("--skip-qdrant", action="store_true")
    args = parser.parse_args()

    create_schema()
    if not args.skip_qdrant:
        create_qdrant_collections()
    create_admin(args.admin_username, args.admin_password, args.admin_name)
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
