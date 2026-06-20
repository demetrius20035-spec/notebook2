"""Настройка логирования с ротацией (§3.5, §12.3 спецификации)."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from backend.core.config import settings

_LOG_DIR = Path("logs")
_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"


def setup_logging() -> None:
    """Конфигурирует корневой логгер: консоль + файл с ротацией 10 МБ × 7."""
    _LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()

    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_DIR / "repairexpert.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
