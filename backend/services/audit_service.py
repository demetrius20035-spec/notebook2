"""Сервис журнала аудита (§10.3)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.audit import AuditLog


def record(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Создаёт запись аудита. Коммит выполняет вызывающий код."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
