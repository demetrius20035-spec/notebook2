"""Обёртка над Qdrant: коллекции и поиск (§7.2, §8.3).

Четыре коллекции (ТЗ §2.5):
    repair_vectors, datasheet_vectors, forum_vectors, knowledge_vectors.
В Qdrant хранятся только вектора и payload с object_id; тексты — в MariaDB.

Импорт ``qdrant_client`` (и транзитивно ``numpy``) выполняется лениво —
внутри методов, а не на уровне модуля. Это позволяет запускать ядро
системы (CRM, тикеты, документы, LLM-диагностика) даже без установленного
или несовместимого Qdrant/NumPy; падает только сам RAG при обращении.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import settings

COLLECTIONS = ("repair_vectors", "datasheet_vectors", "forum_vectors", "knowledge_vectors")

# §8.3 — параметры RAG-поиска.
DEFAULT_MIN_SCORE = 0.72
TOP_K_REPAIRS = 5
TOP_K_DATASHEETS = 3


@dataclass
class SearchHit:
    object_id: int
    score: float
    payload: dict


class VectorStore:
    """Тонкая обёртка над qdrant-client с фабрикой коллекций."""

    def __init__(
        self, host: str | None = None, port: int | None = None, mode: str | None = None
    ) -> None:
        from qdrant_client import QdrantClient  # ленивый импорт (тянет numpy)

        mode = (mode or settings.qdrant_mode).lower()
        if mode == "memory":
            # Встроенный режим в ОЗУ — без сервера, без персистентности.
            self.client = QdrantClient(location=":memory:")
        elif mode == "local":
            # Встроенный режим: вектора хранятся в локальной папке.
            # Не требует ни сервера Qdrant, ни Docker — удобно для Windows.
            self.client = QdrantClient(path=settings.qdrant_local_path)
        else:
            # Внешний сервер Qdrant по host:port.
            self.client = QdrantClient(
                host=host or settings.qdrant_host,
                port=port or settings.qdrant_port,
            )
        self.dim = settings.embedding_dim

    def ensure_collections(self) -> None:
        """Создаёт все коллекции с косинусной метрикой, если их нет."""
        from qdrant_client.http import models as qmodels

        existing = {c.name for c in self.client.get_collections().collections}
        for name in COLLECTIONS:
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=self.dim, distance=qmodels.Distance.COSINE
                    ),
                )

    def upsert(
        self, collection: str, point_id: int, vector: list[float], payload: dict
    ) -> None:
        from qdrant_client.http import models as qmodels

        self.client.upsert(
            collection_name=collection,
            points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        min_score: float = DEFAULT_MIN_SCORE,
        query_filter=None,
    ) -> list[SearchHit]:
        # query_points — актуальный API (search() удалён в свежих версиях
        # qdrant-client); для совместимости откатываемся на search().
        if hasattr(self.client, "query_points"):
            results = self.client.query_points(
                collection_name=collection,
                query=vector,
                limit=top_k,
                score_threshold=min_score,
                query_filter=query_filter,
                with_payload=True,
            ).points
        else:  # pragma: no cover — старые версии клиента
            results = self.client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
                score_threshold=min_score,
                query_filter=query_filter,
            )
        return [
            SearchHit(
                object_id=int((r.payload or {}).get("object_id", r.id)),
                score=r.score,
                payload=r.payload or {},
            )
            for r in results
        ]
