"""Конфигурация приложения, загружаемая из переменных окружения (.env).

Все настройки сосредоточены здесь, чтобы соответствовать требованию
§12.3 спецификации: «Все настройки через `.env` и GUI настроек (не в коде)».
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Типизированные настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── База данных ──
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "repair_expert"
    db_user: str = "repairapp"
    db_password: str = ""

    # ── Qdrant ──
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333

    # ── Хранилище ──
    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    minio_endpoint: str = "127.0.0.1:9000"
    minio_user: str = ""
    minio_password: str = ""
    minio_bucket: str = "repairexpert"

    # ── Безопасность ──
    jwt_secret: str = "insecure-dev-secret-change-me-change-me-change-me"
    jwt_expire_hours: int = 8
    jwt_refresh_days: int = 30
    device_password_key: str = ""  # base64, 32 байта для AES-256-GCM

    # ── Backend ──
    api_host: str = "127.0.0.1"
    api_port: int = 8077
    log_level: str = "INFO"

    # ── LLM ──
    default_llm_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    anthropic_model: str = "claude-3-5-sonnet-latest"

    grok_api_key: str = ""
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = "grok-2-latest"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.1-70b-instruct"

    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "local-model"

    openai_compat_base_url: str = "http://localhost:8000/v1"
    openai_compat_api_key: str = ""
    openai_compat_model: str = ""

    # Yandex Cloud (см. LLM.txt §1)
    yandex_cloud_folder: str = ""
    yandex_cloud_api_key: str = ""
    yandex_cloud_model: str = "yandexgpt-5.1/latest"

    # Sber GigaChat (см. LLM.txt §2)
    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2"
    gigachat_profanity_check: bool = True
    gigachat_verify_ssl: bool = False

    # ── Эмбеддинги ──
    embedding_model: str = "bge-m3"
    embedding_base_url: str = "http://localhost:11434"
    embedding_dim: int = 1024

    # ── OCR ──
    tesseract_cmd: str = "/usr/bin/tesseract"
    tesseract_lang: str = "rus+eng"

    # ── Реквизиты организации ──
    org_name: str = "Сервисный центр «RepairExpert»"
    org_inn: str = ""
    org_address: str = ""
    org_phone: str = ""
    org_email: str = ""
    org_logo_path: str = ""

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL для MariaDB через PyMySQL."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


@lru_cache
def get_settings() -> Settings:
    """Кэшированный доступ к настройкам (singleton)."""
    return Settings()


settings = get_settings()
