"""LLM Adapter — единый слой абстракции над языковыми моделями (§7.1)."""
from backend.llm.base import BaseLLMAdapter, LLMError, LLMMessage, LLMResponse
from backend.llm.factory import SUPPORTED_PROVIDERS, create_adapter

__all__ = [
    "BaseLLMAdapter",
    "LLMMessage",
    "LLMResponse",
    "LLMError",
    "create_adapter",
    "SUPPORTED_PROVIDERS",
]
