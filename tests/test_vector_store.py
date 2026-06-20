"""Тест встроенного режима Qdrant (без сервера и Docker).

Использует in-memory режим qdrant-client — не требует внешних сервисов,
поэтому подходит для CI. Покрывает API query_points (актуальный клиент).
"""
from __future__ import annotations

from backend.rag.vector_store import COLLECTIONS, VectorStore


def test_embedded_qdrant_roundtrip():
    vs = VectorStore(mode="memory")
    vs.ensure_collections()

    names = {c.name for c in vs.client.get_collections().collections}
    assert set(COLLECTIONS) <= names

    vector = [0.1] * vs.dim
    vs.upsert("repair_vectors", 1, vector, {"object_id": 1, "kb_id": 7})

    hits = vs.search("repair_vectors", vector, top_k=3, min_score=0.0)
    assert hits and hits[0].object_id == 1
    assert hits[0].payload["kb_id"] == 7


def test_ensure_collections_idempotent():
    vs = VectorStore(mode="memory")
    vs.ensure_collections()
    vs.ensure_collections()  # повторный вызов не должен падать
    names = {c.name for c in vs.client.get_collections().collections}
    assert set(COLLECTIONS) <= names
