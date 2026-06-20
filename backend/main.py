"""Точка входа FastAPI-бэкенда RepairExpert AI.

Запускается как дочерний процесс GUI или самостоятельно:
    python -m backend.main
    uvicorn backend.main:app --host 127.0.0.1 --port 8077

Согласно §10.4, сервер слушает только localhost.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.logging_config import setup_logging
from backend.routers import ALL_ROUTERS
from backend.schemas.common import fail

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RepairExpert AI API",
    version="1.0.0",
    description="Экспертная система компонентного ремонта электроники с интеграцией LLM",
)

# GUI на PySide6 обращается к localhost — разрешаем локальные источники.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in ALL_ROUTERS:
    app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Единый формат ошибок (§6.4)."""
    logger.exception("Необработанная ошибка на %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content=fail("INTERNAL_ERROR", "Внутренняя ошибка сервера"),
    )


@app.get("/health", tags=["system"])
def health():
    """Проверка живости бэкенда."""
    return {"status": "ok", "version": "1.0.0"}


@app.on_event("startup")
def on_startup() -> None:
    setup_logging()
    logger.info("RepairExpert AI backend запущен (provider=%s)", settings.default_llm_provider)


def run() -> None:
    """Entry point для `repairexpert-api`."""
    import uvicorn

    setup_logging()
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
