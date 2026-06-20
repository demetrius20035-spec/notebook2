"""Генерация эмбеддингов через Ollama (BGE-M3 / nomic-embed-text).

§7.2: размерность 1024 (BGE-M3) или 768 (nomic-embed-text).
Локальный режим обеспечивает полный оффлайн (ТЗ §3.6).
"""
from __future__ import annotations

import httpx

from backend.core.config import settings


class EmbeddingClient:
    """Клиент для получения векторных представлений текста."""

    def __init__(
        self, base_url: str | None = None, model: str | None = None
    ) -> None:
        self.base_url = (base_url or settings.embedding_base_url).rstrip("/")
        self.model = model or settings.embedding_model

    async def embed(self, text: str) -> list[float]:
        """Возвращает эмбеддинг одного фрагмента текста."""
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Эмбеддинги для списка фрагментов (последовательно)."""
        return [await self.embed(t) for t in texts]
