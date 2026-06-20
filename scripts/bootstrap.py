"""Быстрая инициализация окружения разработки.

Создаёт таблицы (без Alembic), коллекции Qdrant и администратора.
Для продакшена используйте Alembic-миграции.

Запуск:
    python -m scripts.bootstrap --admin-password "Secret123"
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy.exc import OperationalError

from backend.core.config import settings
from backend.core.database import SessionLocal, engine
from backend.core.security import hash_password
from backend.models import Base, User
from backend.models.enums import UserRole


def _db_setup_hint() -> str:
    """Подсказка по настройке БД для типичных ошибок доступа."""
    return (
        "\nНе удалось подключиться к базе данных "
        f"'{settings.db_name}' под пользователем "
        f"'{settings.db_user}'@{settings.db_host}.\n"
        "Проверьте, что СУБД запущена, база существует и у пользователя\n"
        "есть права. Создать вручную (выполнить от root):\n\n"
        f"  CREATE DATABASE IF NOT EXISTS {settings.db_name}\n"
        "    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
        f"  CREATE USER IF NOT EXISTS '{settings.db_user}'@'localhost'\n"
        "    IDENTIFIED BY '<пароль из .env DB_PASSWORD>';\n"
        f"  GRANT ALL PRIVILEGES ON {settings.db_name}.* "
        f"TO '{settings.db_user}'@'localhost';\n"
        "  FLUSH PRIVILEGES;\n\n"
        "Либо поднимите готовый стек:  docker compose up -d mariadb qdrant\n"
    )


def create_schema() -> None:
    print(f"→ Создание схемы в {settings.db_name} …")
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        print(_db_setup_hint(), file=sys.stderr)
        raise SystemExit(f"Ошибка БД: {exc.orig}") from exc
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


# Типы устройств из ТЗ §2.2 и распространённые производители.
_DEVICE_TYPES = [
    "Ноутбук", "Смартфон", "Планшет", "Материнская плата",
    "Блок питания", "Монитор", "Другое",
]
_MANUFACTURERS = [
    "Lenovo", "ASUS", "Acer", "HP", "Dell", "Apple", "Samsung",
    "MSI", "Xiaomi", "Huawei",
]


def seed_reference_data() -> None:
    """Заполняет справочники типов устройств и производителей."""
    from backend.models.catalog import DeviceType, Manufacturer

    with SessionLocal() as db:
        for name in _DEVICE_TYPES:
            if not db.query(DeviceType).filter(DeviceType.name == name).first():
                db.add(DeviceType(name=name))
        for name in _MANUFACTURERS:
            if not db.query(Manufacturer).filter(Manufacturer.name == name).first():
                db.add(Manufacturer(name=name))
        db.commit()
    print("  ✔ справочники заполнены (типы устройств, производители)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap RepairExpert AI")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--admin-name", default="Администратор")
    parser.add_argument("--skip-qdrant", action="store_true")
    args = parser.parse_args()

    create_schema()
    seed_reference_data()
    if not args.skip_qdrant:
        create_qdrant_collections()
    create_admin(args.admin_username, args.admin_password, args.admin_name)
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
