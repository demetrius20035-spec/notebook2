"""RAG-подсистема: эмбеддинги, чанкинг, индексация, поиск (§8)."""
from backend.rag.embeddings import EmbeddingClient
from backend.rag.indexer import Indexer
from backend.rag.retriever import Retriever
from backend.rag.vector_store import VectorStore

__all__ = ["EmbeddingClient", "Indexer", "Retriever", "VectorStore"]
