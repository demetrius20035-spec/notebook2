"""Семантический поиск по базе знаний (F-004 шаг 2, §8.3)."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.knowledge import KnowledgeChunk
from backend.rag.embeddings import EmbeddingClient
from backend.rag.vector_store import (
    DEFAULT_MIN_SCORE,
    TOP_K_DATASHEETS,
    TOP_K_REPAIRS,
    VectorStore,
)


@dataclass
class RetrievedChunk:
    chunk_id: int
    score: float
    text: str
    kb_id: int | None


class Retriever:
    """Извлекает релевантные чанки из Qdrant + текст из MariaDB."""

    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingClient | None = None,
        store: VectorStore | None = None,
    ) -> None:
        self.db = db
        self.embeddings = embeddings or EmbeddingClient()
        self.store = store or VectorStore()

    async def search(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[RetrievedChunk]:
        vector = await self.embeddings.embed(query)
        hits = self.store.search(collection, vector, top_k=top_k, min_score=min_score)
        out: list[RetrievedChunk] = []
        for hit in hits:
            kc = self.db.get(KnowledgeChunk, hit.object_id)
            out.append(
                RetrievedChunk(
                    chunk_id=hit.object_id,
                    score=hit.score,
                    text=kc.chunk_text if kc else "",
                    kb_id=kc.kb_id if kc else hit.payload.get("kb_id"),
                )
            )
        return out

    async def similar_repairs(self, query: str) -> list[RetrievedChunk]:
        return await self.search(query, "repair_vectors", top_k=TOP_K_REPAIRS)

    async def relevant_datasheets(self, query: str) -> list[RetrievedChunk]:
        return await self.search(query, "datasheet_vectors", top_k=TOP_K_DATASHEETS)
