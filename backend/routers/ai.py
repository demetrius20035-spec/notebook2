"""AI-эндпоинты: диагностика, семантический поиск, провайдеры (§6.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.llm import LLMError, SUPPORTED_PROVIDERS, create_adapter
from backend.models.enums import UserRole
from backend.models.user import User
from backend.routers.deps import require_roles
from backend.rag.retriever import Retriever
from backend.schemas.common import ok
from backend.schemas.entities import DiagnoseRequest, SemanticSearchRequest
from backend.services.diagnostics_service import DiagnosticsService

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

# Использование AI разрешено admin и master (§3.1).
_AI_ROLES = (UserRole.ADMIN, UserRole.MASTER)


@router.get("/providers")
def list_providers(_: User = Depends(require_roles(*_AI_ROLES))):
    """Список поддерживаемых LLM-провайдеров с активным по умолчанию."""
    return ok(
        {
            "providers": list(SUPPORTED_PROVIDERS),
            "default": settings.default_llm_provider,
        }
    )


@router.post("/diagnose")
async def diagnose(
    body: DiagnoseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_AI_ROLES)),
):
    """F-004: запрос к LLM с RAG-контекстом текущего тикета."""
    try:
        adapter = create_adapter(provider=body.provider, model=body.model)
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    retriever = Retriever(db)
    service = DiagnosticsService(db, adapter=adapter, retriever=retriever)
    try:
        result = await service.diagnose(
            ticket_id=body.ticket_id,
            mode=body.mode,
            user_query=body.query,
            actor_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {exc}") from exc
    return ok(result)


@router.post("/search")
async def semantic_search(
    body: SemanticSearchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_AI_ROLES)),
):
    """Семантический поиск по выбранной коллекции Qdrant."""
    retriever = Retriever(db)
    try:
        hits = await retriever.search(body.query, body.collection, top_k=body.top_k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Ошибка поиска: {exc}") from exc
    return ok(
        [{"chunk_id": h.chunk_id, "score": h.score, "text": h.text, "kb_id": h.kb_id} for h in hits]
    )


@router.get("/health")
async def ai_health(
    provider: str | None = None, _: User = Depends(require_roles(*_AI_ROLES))
):
    """Проверка доступности выбранного (или дефолтного) провайдера."""
    try:
        adapter = create_adapter(provider=provider)
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    healthy = await adapter.health_check()
    return ok({"provider": adapter.provider, "model": adapter.model, "healthy": healthy})
