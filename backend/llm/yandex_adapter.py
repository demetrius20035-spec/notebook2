"""Адаптер Yandex Cloud (Алиса / YandexGPT).

Реализован на основе примера заказчика (LLM.txt, раздел 1):

    import openai
    client = openai.OpenAI(
        api_key=YANDEX_CLOUD_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        project=YANDEX_CLOUD_FOLDER,
    )
    response = client.responses.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        temperature=0.3,
        instructions="",        # системный промпт
        input="",               # пользовательский ввод
        max_output_tokens=500,
    )
    print(response.output_text)

Поддерживаемые модели (поле ``YANDEX_CLOUD_MODEL``):
    * ``aliceai-llm/latest``     — Алиса
    * ``yandexgpt-5.1/latest``   — YandexGPT 5.1 Pro
    * ``yandexgpt-lite/latest``  — облегчённая модель
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI, OpenAIError

from backend.llm.base import BaseLLMAdapter, LLMError, LLMMessage, LLMResponse

_YANDEX_BASE_URL = "https://ai.api.cloud.yandex.net/v1"


class YandexAdapter(BaseLLMAdapter):
    """Адаптер Yandex Cloud Foundation Models через OpenAI-совместимый SDK."""

    provider = "yandex"

    def __init__(self, model: str, folder: str, api_key: str) -> None:
        # `model` — короткое имя, например "yandexgpt-5.1/latest".
        super().__init__(model)
        self.folder = folder
        self.api_key = api_key
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=_YANDEX_BASE_URL,
            project=folder,
        )

    @property
    def _model_uri(self) -> str:
        """Полный URI модели в формате gpt://<folder>/<model>."""
        return f"gpt://{self.folder}/{self.model}"

    def _build_input(self, messages: list[LLMMessage]) -> tuple[str, list[dict]]:
        """Готовит (instructions, input) для responses API.

        Системные сообщения → ``instructions``; остальные сообщения →
        список элементов ``input`` (сохраняем многошаговый диалог).
        """
        instructions, rest = self._split_system(messages)
        items = [{"role": m.role, "content": m.content} for m in rest]
        return instructions, items

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        instructions, items = self._build_input(messages)
        try:
            response = await self._client.responses.create(
                model=self._model_uri,
                temperature=temperature,
                instructions=instructions,
                input=items,
                max_output_tokens=max_tokens,
            )
        except OpenAIError as exc:
            raise LLMError(f"[yandex] API error: {exc}") from exc

        content = getattr(response, "output_text", "") or ""
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            tokens_used=tokens,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Потоковая выдача через события responses API.

        При недоступности стриминга деградирует к полному ответу.
        """
        instructions, items = self._build_input(messages)
        try:
            stream = await self._client.responses.create(
                model=self._model_uri,
                temperature=temperature,
                instructions=instructions,
                input=items,
                max_output_tokens=max_tokens,
                stream=True,
            )
            async for event in stream:
                delta = getattr(event, "delta", None)
                if isinstance(delta, str) and delta:
                    yield delta
        except (OpenAIError, TypeError):
            # Фолбэк: один цельный ответ.
            result = await self.complete(messages, temperature, max_tokens)
            yield result.content

    async def health_check(self) -> bool:
        if not (self.api_key and self.folder):
            return False
        try:
            await self.complete([LLMMessage(role="user", content="ping")], max_tokens=1)
            return True
        except LLMError:
            return False
