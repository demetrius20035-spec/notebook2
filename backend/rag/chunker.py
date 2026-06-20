"""Разбивка текста на чанки (§5 F-005, §8.3).

Размер чанка ~512 токенов, перекрытие ~64 токена. Без тяжёлых
зависимостей-токенизаторов используется приближение: 1 токен ≈ 4 символа.
"""
from __future__ import annotations

from dataclasses import dataclass

CHARS_PER_TOKEN = 4
CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int


def chunk_text(
    text: str, chunk_tokens: int = CHUNK_TOKENS, overlap_tokens: int = OVERLAP_TOKENS
) -> list[Chunk]:
    """Разбивает текст на перекрывающиеся чанки по приближённому числу токенов."""
    text = " ".join(text.split())  # нормализация пробелов
    if not text:
        return []

    size = chunk_tokens * CHARS_PER_TOKEN
    overlap = overlap_tokens * CHARS_PER_TOKEN
    step = max(size - overlap, 1)

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        piece = text[start : start + size]
        chunks.append(Chunk(index=idx, text=piece, token_count=len(piece) // CHARS_PER_TOKEN))
        idx += 1
        start += step
    return chunks
