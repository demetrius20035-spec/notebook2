"""Адаптер Ollama — локальные модели для полного оффлайн-режима (ТЗ §3.6).

Использует нативный Ollama API ``/api/chat``.
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx

from backend.llm.base import BaseLLMAdapter, LLMError, LLMMessage, LLMResponse


class OllamaAdapter(BaseLLMAdapter):
    """Адаптер локального сервера Ollama."""

    provider = "ollama"

    def __init__(self, model: str, base_url: str, *, timeout: float = 120.0) -> None:
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _payload(
        self, messages: list[LLMMessage], temperature: float, max_tokens: int, stream: bool
    ) -> dict:
        return {
            "model": self.model,
            "messages": self._to_openai_dicts(messages),
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        url = f"{self.base_url}/api/chat"
        payload = self._payload(messages, temperature, max_tokens, stream=False)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"[ollama] HTTP error: {exc}") from exc

        content = data.get("message", {}).get("content", "")
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.provider,
            tokens_used=tokens,
            raw=data,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        payload = self._payload(messages, temperature, max_tokens, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        piece = data.get("message", {}).get("content")
                        if piece:
                            yield piece
                        if data.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise LLMError(f"[ollama] stream error: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
