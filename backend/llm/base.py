"""Базовый интерфейс LLM Adapter (§7.1 спецификации).

Единый слой абстракции над всеми провайдерами. Любой адаптер реализует
три метода: ``complete`` (полный ответ), ``stream`` (потоковая выдача) и
``health_check`` (проверка доступности). Это позволяет переключать
провайдера без перезапуска приложения (ТЗ §2.4).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """Сообщение диалога."""

    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Унифицированный ответ модели."""

    content: str
    model: str
    provider: str
    tokens_used: int = 0
    raw: dict = field(default_factory=dict)


class LLMError(RuntimeError):
    """Ошибка взаимодействия с провайдером LLM."""


class BaseLLMAdapter(ABC):
    """Абстрактный адаптер языковой модели."""

    #: человекочитаемое имя провайдера ("openai", "yandex", …)
    provider: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Возвращает полный ответ модели на список сообщений."""

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Асинхронно отдаёт ответ по частям (токенам/чанкам)."""
        raise NotImplementedError
        yield ""  # pragma: no cover  (делает функцию генератором для mypy)

    @abstractmethod
    async def health_check(self) -> bool:
        """True, если провайдер доступен и сконфигурирован корректно."""

    # ── вспомогательные методы ──
    @staticmethod
    def _split_system(messages: list[LLMMessage]) -> tuple[str, list[LLMMessage]]:
        """Отделяет системные сообщения от остальных.

        Возвращает (объединённый system-промпт, остальные сообщения).
        Полезно для провайдеров с раздельными полями system/messages
        (Anthropic, Yandex responses API).
        """
        system_parts = [m.content for m in messages if m.role == "system"]
        rest = [m for m in messages if m.role != "system"]
        return "\n\n".join(system_parts), rest

    @staticmethod
    def _to_openai_dicts(messages: list[LLMMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]
