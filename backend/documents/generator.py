"""Генерация PDF-документов (F-007, §9).

Jinja2 (HTML) → WeasyPrint (PDF). QR-код тикета встраивается во все
документы (ТЗ §2.11). Реквизиты организации берутся из настроек.
"""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"

# document_type → имя шаблона (§9).
_TEMPLATES = {
    "acceptance": "acceptance.html",   # Квитанция о приёмке
    "act": "act.html",                 # Акт выполненных работ
    "defect": "defect.html",           # Дефектовочная ведомость
    "warranty": "warranty.html",       # Гарантийный талон
}


def _qr_data_uri(payload: str) -> str:
    """Возвращает QR-код как data-URI (PNG, base64)."""
    try:
        import qrcode

        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось сгенерировать QR: %s", exc)
        return ""


def _org_context() -> dict:
    return {
        "org_name": settings.org_name,
        "org_inn": settings.org_inn,
        "org_address": settings.org_address,
        "org_phone": settings.org_phone,
        "org_email": settings.org_email,
        "org_logo_path": settings.org_logo_path,
    }


def render_html(document_type: str, context: dict) -> str:
    """Рендерит HTML-шаблон документа с данными и реквизитами."""
    if document_type not in _TEMPLATES:
        raise ValueError(f"Неизвестный тип документа: {document_type}")

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(_TEMPLATES[document_type])
    full_context = {
        **_org_context(),
        "qr_code": _qr_data_uri(context.get("ticket_number", "")),
        **context,
    }
    return template.render(**full_context)


def generate_pdf(document_type: str, context: dict, output_path: str | Path) -> Path:
    """Генерирует PDF-документ и сохраняет его в файловое хранилище."""
    html = render_html(document_type, context)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from weasyprint import HTML

    HTML(string=html).write_pdf(str(output_path))
    logger.info("Сгенерирован документ %s → %s", document_type, output_path)
    return output_path
