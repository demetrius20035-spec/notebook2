"""Пайплайн индексации документов в RAG (F-005).

Файл → текст → чанки → MariaDB(knowledge_chunks) → эмбеддинги → Qdrant.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.models.enums import KnowledgeSourceType
from backend.models.knowledge import KnowledgeBase, KnowledgeChunk
from backend.rag.chunker import chunk_text
from backend.rag.embeddings import EmbeddingClient
from backend.rag.extractor import extract_text
from backend.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Соответствие типа источника и коллекции Qdrant (§7.2).
_COLLECTION_BY_SOURCE = {
    KnowledgeSourceType.DATASHEET: "datasheet_vectors",
    KnowledgeSourceType.REPAIR_CASE: "repair_vectors",
    KnowledgeSourceType.FORUM: "forum_vectors",
}
_DEFAULT_COLLECTION = "knowledge_vectors"


class Indexer:
    """Сервис индексации документов в базу знаний и Qdrant."""

    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingClient | None = None,
        store: VectorStore | None = None,
    ) -> None:
        self.db = db
        self.embeddings = embeddings or EmbeddingClient()
        self.store = store or VectorStore()

    async def index_file(
        self,
        file_path: str,
        title: str,
        source_type: KnowledgeSourceType,
        author_id: int | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeBase:
        """Индексирует файл целиком: создаёт KB-запись, чанки и вектора."""
        text = extract_text(file_path)
        return await self.index_text(text, title, source_type, author_id, tags)

    async def index_text(
        self,
        text: str,
        title: str,
        source_type: KnowledgeSourceType,
        author_id: int | None = None,
        tags: list[str] | None = None,
        source_ref_id: int | None = None,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            title=title,
            content=text,
            source_type=source_type,
            author_id=author_id,
            tags=tags,
            source_ref_id=source_ref_id,
        )
        self.db.add(kb)
        self.db.flush()  # получаем kb.id

        collection = _COLLECTION_BY_SOURCE.get(source_type, _DEFAULT_COLLECTION)
        self.store.ensure_collections()

        for chunk in chunk_text(text):
            kc = KnowledgeChunk(
                kb_id=kb.id,
                chunk_index=chunk.index,
                chunk_text=chunk.text,
                token_count=chunk.token_count,
            )
            self.db.add(kc)
            self.db.flush()

            vector = await self.embeddings.embed(chunk.text)
            embedding_id = f"{collection}:{kc.id}"
            self.store.upsert(
                collection=collection,
                point_id=kc.id,
                vector=vector,
                payload={
                    "object_id": kc.id,
                    "kb_id": kb.id,
                    "chunk_id": kc.id,
                    "source_type": source_type.value,
                    "tags": tags or [],
                },
            )
            kc.embedding_id = embedding_id

        self.db.commit()
        logger.info("Проиндексирован документ '%s' (kb_id=%s)", title, kb.id)
        return kb
