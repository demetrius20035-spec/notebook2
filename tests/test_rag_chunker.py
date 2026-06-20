"""Тесты разбивки на чанки (F-005, §8.3)."""
from __future__ import annotations

from backend.rag.chunker import CHARS_PER_TOKEN, chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_single_chunk():
    chunks = chunk_text("короткий текст")
    assert len(chunks) == 1
    assert chunks[0].index == 0


def test_long_text_is_split_with_overlap():
    text = "слово " * 2000  # заведомо длиннее одного чанка
    chunks = chunk_text(text, chunk_tokens=512, overlap_tokens=64)
    assert len(chunks) > 1
    # индексы последовательны
    assert [c.index for c in chunks] == list(range(len(chunks)))
    # размер чанка соответствует ~512 токенам
    assert chunks[0].token_count <= 512 + 1


def test_token_estimate_uses_chars_ratio():
    chunks = chunk_text("a" * (512 * CHARS_PER_TOKEN))
    assert chunks[0].token_count == 512
