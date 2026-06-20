"""Тесты фабрики LLM-адаптеров (§7.1) и адаптеров из LLM.txt."""
from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.llm import LLMError, SUPPORTED_PROVIDERS, create_adapter
from backend.llm.anthropic_adapter import AnthropicAdapter
from backend.llm.base import LLMMessage
from backend.llm.gigachat_adapter import GigaChatAdapter
from backend.llm.ollama_adapter import OllamaAdapter
from backend.llm.openai_compatible import GrokAdapter, OpenAIAdapter
from backend.llm.yandex_adapter import YandexAdapter


@pytest.fixture
def cfg() -> Settings:
    return Settings(
        yandex_cloud_folder="b1gtgst618m140kehrm5",
        yandex_cloud_api_key="key",
        gigachat_auth_key="basic-token",
    )


def test_all_providers_supported():
    assert set(SUPPORTED_PROVIDERS) == {
        "ollama", "openai", "anthropic", "grok", "openrouter",
        "lmstudio", "openai_compat", "yandex", "gigachat",
    }


@pytest.mark.parametrize(
    "provider,expected",
    [
        ("ollama", OllamaAdapter),
        ("openai", OpenAIAdapter),
        ("anthropic", AnthropicAdapter),
        ("grok", GrokAdapter),
        ("yandex", YandexAdapter),
        ("gigachat", GigaChatAdapter),
    ],
)
def test_factory_creates_expected_adapter(cfg, provider, expected):
    adapter = create_adapter(provider=provider, cfg=cfg)
    assert isinstance(adapter, expected)
    assert adapter.provider == provider


def test_factory_unknown_provider_raises(cfg):
    with pytest.raises(LLMError):
        create_adapter(provider="does-not-exist", cfg=cfg)


def test_yandex_model_uri_format(cfg):
    adapter = create_adapter(provider="yandex", model="yandexgpt-5.1/latest", cfg=cfg)
    assert adapter._model_uri == "gpt://b1gtgst618m140kehrm5/yandexgpt-5.1/latest"


def test_gigachat_defaults_from_llm_txt(cfg):
    adapter = create_adapter(provider="gigachat", cfg=cfg)
    assert adapter.model == "GigaChat-2"
    assert adapter.scope == "GIGACHAT_API_PERS"
    assert adapter.profanity_check is True


def test_split_system_helper():
    msgs = [
        LLMMessage(role="system", content="rules"),
        LLMMessage(role="user", content="hi"),
    ]
    system, rest = OllamaAdapter("m", "http://x")._split_system(msgs)
    assert system == "rules"
    assert len(rest) == 1 and rest[0].role == "user"
