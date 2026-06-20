"""Реализация адаптеров поверх OpenAI-совместимого Chat Completions API.

Множество провайдеров (OpenAI, xAI Grok, OpenRouter, LM Studio,
vLLM, llama.cpp) используют один и тот же протокол ``/chat/completions``.
Все они наследуются от :class:`OpenAICompatibleAdapter`, меняя лишь
``base_url``, заголовки и значение поля ``provider``.
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx

from backend.llm.base import BaseLLMAdapter, LLMError, LLMMessage, LLMResponse


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """Общая реализация для провайдеров с OpenAI Chat Completions API."""

    provider = "openai_compat"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "",
        *,
        extra_headers: dict[str, str] | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.extra_headers = extra_headers or {}
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _payload(
        self, messages: list[LLMMessage], temperature: float, max_tokens: int, stream: bool
    ) -> dict:
        return {
            "model": self.model,
            "messages": self._to_openai_dicts(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        payload = self._payload(messages, temperature, max_tokens, stream=False)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"[{self.provider}] HTTP error: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"[{self.provider}] неожиданный формат ответа: {data}") from exc

        usage = data.get("usage", {}) or {}
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.provider,
            tokens_used=usage.get("total_tokens", 0),
            raw=data,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        payload = self._payload(messages, temperature, max_tokens, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, headers=self._headers(), json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        chunk = line[len("data:"):].strip()
                        if chunk == "[DONE]":
                            break
                        try:
                            delta = json.loads(chunk)["choices"][0]["delta"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                        piece = delta.get("content")
                        if piece:
                            yield piece
        except httpx.HTTPError as exc:
            raise LLMError(f"[{self.provider}] stream error: {exc}") from exc

    async def health_check(self) -> bool:
        """Проверяет доступность через эндпоинт ``/models``."""
        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers())
                return resp.status_code < 500
        except httpx.HTTPError:
            return False


# ───────────────────────── Конкретные провайдеры ──────────────────────────
class OpenAIAdapter(OpenAICompatibleAdapter):
    provider = "openai"


class GrokAdapter(OpenAICompatibleAdapter):
    """xAI Grok — OpenAI-совместимый API на https://api.x.ai/v1."""

    provider = "grok"


class OpenRouterAdapter(OpenAICompatibleAdapter):
    """OpenRouter — агрегатор моделей через OpenAI-совместимый API."""

    provider = "openrouter"

    def __init__(self, model: str, base_url: str, api_key: str = "", **kw) -> None:
        # OpenRouter рекомендует заголовки идентификации приложения.
        extra = {
            "HTTP-Referer": "https://repairexpert.local",
            "X-Title": "RepairExpert AI",
        }
        extra.update(kw.pop("extra_headers", {}))
        super().__init__(model, base_url, api_key, extra_headers=extra, **kw)


class LMStudioAdapter(OpenAICompatibleAdapter):
    """LM Studio — локальный OpenAI-совместимый сервер (порт 1234)."""

    provider = "lmstudio"


class OpenAICompatServerAdapter(OpenAICompatibleAdapter):
    """vLLM / llama.cpp — настраиваемый пользователем OpenAI-совместимый сервер."""

    provider = "openai_compat"
