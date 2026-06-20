"""Извлечение текста из файлов для индексации (F-005).

PDF с текстовым слоем → pdfminer; PDF-скан → Tesseract OCR;
TXT/MD → прямое чтение.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _clean(text: str) -> str:
    """Базовая нормализация: убираем лишние пустые строки/пробелы."""
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def extract_text(path: str | Path) -> str:
    """Возвращает извлечённый и очищенный текст из файла."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return _clean(path.read_text(encoding="utf-8", errors="ignore"))

    if suffix == ".pdf":
        return _clean(_extract_pdf(path))

    raise ValueError(f"Неподдерживаемый тип файла для индексации: {suffix}")


def _extract_pdf(path: Path) -> str:
    """Сначала пробуем текстовый слой, при пустом результате — OCR."""
    try:
        from pdfminer.high_level import extract_text as pdf_extract

        text = pdf_extract(str(path)) or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfminer не справился с %s: %s", path, exc)
        text = ""

    if len(text.strip()) >= 40:
        return text

    logger.info("PDF %s выглядит как скан — запускаем OCR", path.name)
    return _ocr_pdf(path)


def _ocr_pdf(path: Path) -> str:
    """OCR PDF-скана через pdf2image + pytesseract (Tesseract 5+)."""
    try:
        import pytesseract
        from pdf2image import convert_from_path

        from backend.core.config import settings

        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        pages = convert_from_path(str(path))
        return "\n".join(
            pytesseract.image_to_string(page, lang=settings.tesseract_lang) for page in pages
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("OCR не удался для %s: %s", path, exc)
        return ""
