"""Фабрика LLM-адаптеров.

Единая точка создания адаптера по имени провайдера. Позволяет
переключать провайдера и модель без перезапуска приложения (ТЗ §2.4):
можно задать разные модели для диагностики и для генерации документов.
"""
from __future__ import annotations

from backend.core.config import Settings, settings
from backend.llm.anthropic_adapter import AnthropicAdapter
from backend.llm.base import BaseLLMAdapter, LLMError
from backend.llm.gigachat_adapter import GigaChatAdapter
from backend.llm.ollama_adapter import OllamaAdapter
from backend.llm.openai_compatible import (
    GrokAdapter,
    LMStudioAdapter,
    OpenAIAdapter,
    OpenAICompatServerAdapter,
    OpenRouterAdapter,
)
from backend.llm.yandex_adapter import YandexAdapter

#: Все поддерживаемые провайдеры (для эндпоинта GET /api/v1/ai/providers).
SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "ollama",
    "openai",
    "anthropic",
    "grok",
    "openrouter",
    "lmstudio",
    "openai_compat",
    "yandex",
    "gigachat",
)


def create_adapter(
    provider: str | None = None,
    model: str | None = None,
    cfg: Settings | None = None,
) -> BaseLLMAdapter:
    """Создаёт адаптер для указанного провайдера.

    :param provider: имя провайдера; если ``None`` — берётся из настроек.
    :param model: переопределение модели; если ``None`` — дефолт провайдера.
    :param cfg: объект настроек (для тестов); по умолчанию — глобальный.
    """
    cfg = cfg or settings
    provider = (provider or cfg.default_llm_provider).lower()

    if provider == "ollama":
        return OllamaAdapter(model or cfg.ollama_model, cfg.ollama_base_url)

    if provider == "openai":
        return OpenAIAdapter(model or cfg.openai_model, cfg.openai_base_url, cfg.openai_api_key)

    if provider == "anthropic":
        return AnthropicAdapter(
            model or cfg.anthropic_model, cfg.anthropic_base_url, cfg.anthropic_api_key
        )

    if provider == "grok":
        return GrokAdapter(model or cfg.grok_model, cfg.grok_base_url, cfg.grok_api_key)

    if provider == "openrouter":
        return OpenRouterAdapter(
            model or cfg.openrouter_model, cfg.openrouter_base_url, cfg.openrouter_api_key
        )

    if provider == "lmstudio":
        return LMStudioAdapter(model or cfg.lmstudio_model, cfg.lmstudio_base_url)

    if provider == "openai_compat":
        return OpenAICompatServerAdapter(
            model or cfg.openai_compat_model,
            cfg.openai_compat_base_url,
            cfg.openai_compat_api_key,
        )

    if provider == "yandex":
        return YandexAdapter(
            model or cfg.yandex_cloud_model,
            cfg.yandex_cloud_folder,
            cfg.yandex_cloud_api_key,
        )

    if provider == "gigachat":
        return GigaChatAdapter(
            model or cfg.gigachat_model,
            cfg.gigachat_auth_key,
            cfg.gigachat_scope,
            profanity_check=cfg.gigachat_profanity_check,
            verify_ssl=cfg.gigachat_verify_ssl,
        )

    raise LLMError(
        f"Неизвестный LLM-провайдер: '{provider}'. "
        f"Доступны: {', '.join(SUPPORTED_PROVIDERS)}"
    )
