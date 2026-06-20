"""Адаптер Sber GigaChat.

Реализован на основе примера заказчика (LLM.txt, раздел 2).

Шаг 1 — авторизация (получение access_token):

    POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth
    headers:
        Content-Type: application/x-www-form-urlencoded
        Accept: application/json
        RqUID: <uuid4>
        Authorization: Basic <GIGACHAT_AUTH_KEY>
    body: scope=<SCOPE>            # GIGACHAT_API_PERS | _B2B | _CORP

Шаг 2 — генерация:

    POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions
    headers:
        Authorization: Bearer <access_token>
    body: {"model": "GigaChat-2", "messages": [...], "profanity_check": true}

Модели: ``GigaChat-2``, ``GigaChat-2-Pro``, ``GigaChat-2-Max``.

Примечание по TLS: инфраструктура Sber использует корневой сертификат
«Минцифры». Управляется параметром ``GIGACHAT_VERIFY_SSL`` (путь к .pem
или ``false`` для отключения проверки во внутренней сети).
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator

import httpx

from backend.llm.base import BaseLLMAdapter, LLMError, LLMMessage, LLMResponse

_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class GigaChatAdapter(BaseLLMAdapter):
    """Адаптер Sber GigaChat с кэшированием OAuth-токена."""

    provider = "gigachat"

    def __init__(
        self,
        model: str,
        auth_key: str,
        scope: str = "GIGACHAT_API_PERS",
        *,
        profanity_check: bool = True,
        verify_ssl: bool | str = False,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(model)
        self.auth_key = auth_key
        self.scope = scope
        self.profanity_check = profanity_check
        # httpx принимает bool или путь к CA-бандлу.
        self.verify = verify_ssl
        self.timeout = timeout
        self._token: str | None = None
        self._token_exp: float = 0.0  # unix-время истечения (сек)

    # ─────────────────────────── OAuth ───────────────────────────
    async def _get_token(self) -> str:
        """Возвращает действующий access_token, обновляя при истечении."""
        # Обновляем заранее, за 30 секунд до истечения.
        if self._token and time.time() < self._token_exp - 30:
            return self._token
        if not self.auth_key:
            raise LLMError("[gigachat] не задан GIGACHAT_AUTH_KEY")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self.auth_key}",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify) as client:
                resp = await client.post(
                    _OAUTH_URL, headers=headers, data={"scope": self.scope}
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"[gigachat] ошибка авторизации: {exc}") from exc

        self._token = data["access_token"]
        # expires_at — unix-время в миллисекундах.
        self._token_exp = data.get("expires_at", 0) / 1000 or time.time() + 1500
        return self._token

    def _payload(
        self, messages: list[LLMMessage], temperature: float, max_tokens: int, stream: bool
    ) -> dict:
        return {
            "model": self.model,
            "messages": self._to_openai_dicts(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "profanity_check": self.profanity_check,
            "stream": stream,
        }

    # ─────────────────────────── Генерация ───────────────────────────
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        token = await self._get_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        payload = self._payload(messages, temperature, max_tokens, stream=False)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify) as client:
                resp = await client.post(_CHAT_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"[gigachat] HTTP error: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"[gigachat] неожиданный формат ответа: {data}") from exc

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
        token = await self._get_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        payload = self._payload(messages, temperature, max_tokens, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify) as client:
                async with client.stream(
                    "POST", _CHAT_URL, headers=headers, json=payload
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
            raise LLMError(f"[gigachat] stream error: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            await self._get_token()
            return True
        except LLMError:
            return False
