"""Адаптер Anthropic Claude (Messages API).

Anthropic использует отдельное поле ``system`` и собственный формат
``/v1/messages`` с заголовками ``x-api-key`` и ``anthropic-version``.
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx

from backend.llm.base import BaseLLMAdapter, LLMError, LLMMessage, LLMResponse

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(BaseLLMAdapter):
    """Адаптер Claude через нативный Messages API."""

    provider = "anthropic"

    def __init__(
        self, model: str, base_url: str, api_key: str = "", *, timeout: float = 60.0
    ) -> None:
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    def _payload(
        self, messages: list[LLMMessage], temperature: float, max_tokens: int, stream: bool
    ) -> dict:
        system, rest = self._split_system(messages)
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in rest],
            "stream": stream,
        }
        if system:
            payload["system"] = system
        return payload

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        url = f"{self.base_url}/messages"
        payload = self._payload(messages, temperature, max_tokens, stream=False)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"[anthropic] HTTP error: {exc}") from exc

        try:
            content = "".join(
                block.get("text", "") for block in data["content"] if block.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise LLMError(f"[anthropic] неожиданный формат ответа: {data}") from exc

        usage = data.get("usage", {}) or {}
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.provider,
            tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            raw=data,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/messages"
        payload = self._payload(messages, temperature, max_tokens, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, headers=self._headers(), json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        chunk = line[len("data:"):].strip()
                        try:
                            event = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
                        if event.get("type") == "content_block_delta":
                            piece = event.get("delta", {}).get("text")
                            if piece:
                                yield piece
        except httpx.HTTPError as exc:
            raise LLMError(f"[anthropic] stream error: {exc}") from exc

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        # Минимальный запрос для проверки ключа и доступности.
        try:
            await self.complete(
                [LLMMessage(role="user", content="ping")], max_tokens=1
            )
            return True
        except LLMError:
            return False
