"""Сборка контекста и генерация документов по тикету (F-007, §9)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.documents.generator import generate_pdf
from backend.models.catalog import DeviceType, Manufacturer
from backend.models.client import Client
from backend.models.component import Component
from backend.models.device import Device
from backend.models.knowledge import Document
from backend.models.ticket import RepairTicket, TicketComponent
from backend.models.user import User
from backend.services import audit_service


def _fmt(value) -> str:
    return "" if value is None else str(value)


def build_context(db: Session, ticket: RepairTicket) -> dict:
    """Готовит словарь данных для шаблонов документов."""
    client = db.get(Client, ticket.client_id)
    device = db.get(Device, ticket.device_id)
    manufacturer = db.get(Manufacturer, device.manufacturer_id) if device else None
    device_type = db.get(DeviceType, device.device_type_id) if device else None
    master = db.get(User, ticket.master_id) if ticket.master_id else None
    receiver = db.get(User, ticket.receiver_id) if ticket.receiver_id else None

    components = []
    for tc in db.query(TicketComponent).filter(TicketComponent.ticket_id == ticket.id).all():
        comp = db.get(Component, tc.component_id)
        total = (tc.unit_cost or 0) * (tc.quantity or 0)
        components.append(
            {
                "name": comp.name if comp else f"#{tc.component_id}",
                "quantity": tc.quantity,
                "unit_cost": float(tc.unit_cost or 0),
                "total": float(total),
            }
        )

    return {
        "ticket_number": ticket.ticket_number,
        "accepted_at": _fmt(ticket.accepted_at),
        "delivered_at": _fmt(ticket.delivered_at),
        "client_name": client.full_name if client else "—",
        "client_phone": client.phone if client else "",
        "receiver_name": receiver.full_name if receiver else "",
        "master_name": master.full_name if master else "",
        "device_type": device_type.name if device_type else "",
        "device_manufacturer": manufacturer.name if manufacturer else "",
        "device_model": device.model_name if device else "",
        "serial_number": device.serial_number if device else "",
        "problem_description": ticket.problem_description,
        "diagnostic_result": ticket.diagnostic_result,
        "repair_description": ticket.repair_description,
        "cost_estimate": float(ticket.cost_estimate or 0),
        "cost_final": float(ticket.cost_final or 0),
        "work_cost": float(ticket.cost_final or 0),
        "warranty_months": ticket.warranty_months,
        "warranty_expires_at": _fmt(ticket.warranty_expires_at),
        "components": components,
        "defect_items": components,
    }


def generate_document(
    db: Session, ticket: RepairTicket, document_type: str, actor_id: int
) -> Document:
    """Генерирует PDF, сохраняет в хранилище и фиксирует запись в documents."""
    context = build_context(db, ticket)
    out_dir = Path(settings.storage_local_path) / "repairs" / str(ticket.id) / "documents"
    out_path = out_dir / f"{document_type}_{ticket.ticket_number}.pdf"

    generate_pdf(document_type, context, out_path)

    doc = Document(
        ticket_id=ticket.id,
        document_type=document_type,
        file_path=str(out_path),
        generated_by=actor_id,
    )
    db.add(doc)
    audit_service.record(
        db, user_id=actor_id, action="DOCUMENT_GENERATE",
        entity_type="repair_ticket", entity_id=ticket.id,
        new_value={"document_type": document_type},
    )
    db.commit()
    db.refresh(doc)
    return doc
