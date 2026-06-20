"""База знаний: статьи и заметки (§2.6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.enums import KnowledgeSourceType, UserRole
from backend.models.knowledge import KnowledgeBase
from backend.models.user import User
from backend.routers.deps import get_current_user, require_roles
from backend.schemas.common import ok
from backend.schemas.more import KnowledgeCreate

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

_EDIT = (UserRole.ADMIN, UserRole.MASTER)


@router.get("")
def list_articles(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(KnowledgeBase.title.like(like), KnowledgeBase.content.like(like)))
    rows = db.scalars(stmt.limit(200)).all()
    return ok(
        [
            {
                "id": a.id,
                "title": a.title,
                "source_type": a.source_type.value,
                "tags": a.tags or [],
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in rows
        ]
    )


@router.post("")
def create_article(
    body: KnowledgeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDIT)),
):
    try:
        source = KnowledgeSourceType(body.source_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Неизвестный тип источника") from exc
    article = KnowledgeBase(
        title=body.title,
        content=body.content,
        source_type=source,
        tags=body.tags,
        author_id=user.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return ok({"id": article.id, "title": article.title})


@router.get("/{article_id}")
def get_article(
    article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    a = db.get(KnowledgeBase, article_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Статья не найдена")
    return ok(
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "source_type": a.source_type.value,
            "tags": a.tags or [],
        }
    )
