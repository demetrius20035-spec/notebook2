# RepairExpert AI

Экспертная система компонентного ремонта электроники с интеграцией LLM.
Реализация по **ТЗ RepairExpert AI v1.0** и **Формализованной спецификации
ФС-RepairExpert-1.0**.

Десктопное приложение для сервисного центра: CRM, приёмка, журнал ремонта
и карта измерений, база компонентов и склад, документооборот (PDF),
RAG-поиск по базе знаний и экспертная LLM-диагностика.

---

## Архитектура

```
PySide6 GUI  ──HTTP──▶  FastAPI Backend  ──┬──▶  MariaDB (данные)
(gui/)                  (backend/)         ├──▶  Qdrant  (RAG-вектора)
                                           ├──▶  Файловое хранилище
                                           └──▶  LLM Adapter (9 провайдеров)
```

| Слой        | Технологии                                            |
|-------------|-------------------------------------------------------|
| GUI         | PySide6 (Qt6)                                         |
| Backend     | FastAPI, SQLAlchemy 2.x, Alembic                      |
| СУБД        | MariaDB 11.x (InnoDB, utf8mb4, READ-COMMITTED)        |
| Вектора     | Qdrant (4 коллекции)                                  |
| LLM         | Единый адаптер: 9 провайдеров (см. ниже)              |
| Эмбеддинги  | BGE-M3 / nomic-embed-text через Ollama                |
| OCR / PDF   | Tesseract 5+, pdfminer / WeasyPrint + Jinja2          |
| Безопасность| bcrypt, JWT (HS256), AES-256-GCM                      |

Структура каталогов:

```
backend/
├── core/         конфигурация, БД, безопасность, логирование
├── models/       ORM-модели всех сущностей (§4 спецификации)
├── schemas/      Pydantic-схемы API
├── routers/      эндпоинты: auth, clients, tickets, ai, components
├── services/     бизнес-логика (тикеты, диагностика, аудит)
├── llm/          LLM Adapter и реализации провайдеров   ← см. ниже
├── rag/          эмбеддинги, чанкинг, индексация, поиск
├── documents/    генерация PDF (Jinja2 → WeasyPrint)
└── prompts/      системные промпты диагностики (§8)
gui/              приложение PySide6
alembic/          миграции схемы БД
scripts/          bootstrap (быстрый старт)
tests/            pytest
```

---

## Интеграция LLM (единый адаптер)

Переключение провайдера и модели — без перезапуска приложения (ТЗ §2.4).
Все адаптеры реализуют единый интерфейс `BaseLLMAdapter`
(`complete` / `stream` / `health_check`) — см. `backend/llm/base.py`.

| Провайдер        | Класс                       | Источник                       |
|------------------|-----------------------------|--------------------------------|
| Ollama (локально)| `OllamaAdapter`             | ТЗ §2.4 (оффлайн-режим)        |
| OpenAI           | `OpenAIAdapter`             | ТЗ §2.4                        |
| Anthropic Claude | `AnthropicAdapter`          | ТЗ §2.4                        |
| xAI Grok         | `GrokAdapter`               | ТЗ §2.4                        |
| OpenRouter       | `OpenRouterAdapter`         | ТЗ §2.4                        |
| LM Studio        | `LMStudioAdapter`           | ТЗ §2.4                        |
| vLLM / llama.cpp | `OpenAICompatServerAdapter` | ТЗ §2.4                        |
| **Yandex Cloud** | `YandexAdapter`             | **LLM.txt §1 (Алиса, YandexGPT 5.1)** |
| **Sber GigaChat**| `GigaChatAdapter`           | **LLM.txt §2 (GigaChat-2/Pro/Max)** |

Провайдеры из присланных примеров (`LLM.txt`) реализованы в точности по
указанным эндпоинтам и форматам:

- **Yandex** (`backend/llm/yandex_adapter.py`) — OpenAI SDK,
  `base_url=https://ai.api.cloud.yandex.net/v1`, `project=<folder>`,
  модель `gpt://<folder>/<model>`, вызов `responses.create` с
  `instructions` (system) и `input` (диалог).
- **GigaChat** (`backend/llm/gigachat_adapter.py`) — двухшаговый поток:
  OAuth (`ngw.devices.sberbank.ru:9443/api/v2/oauth`, `Basic`-ключ + `RqUID`,
  `scope`) с кэшированием токена, затем
  `gigachat.devices.sberbank.ru/api/v1/chat/completions`
  (`Bearer`-токен, `profanity_check`). TLS-проверка настраивается
  (`GIGACHAT_VERIFY_SSL`).

Выбор провайдера: переменная `DEFAULT_LLM_PROVIDER` в `.env` либо параметр
`provider` в запросе `POST /api/v1/ai/diagnose`.

---

## Быстрый старт (разработка)

### 1. Зависимости

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# системные пакеты для WeasyPrint/Tesseract: см. их документацию
```

### 2. Сервисы (MariaDB + Qdrant)

```bash
cp .env.example .env          # отредактируйте секреты
docker compose up -d mariadb qdrant
# опционально MinIO:
# docker compose --profile minio up -d
```

Сгенерировать секреты:

```bash
python -m backend.core.security   # печатает DEVICE_PASSWORD_KEY и JWT_SECRET
```

### 3. Схема БД и администратор

Через быстрый bootstrap:

```bash
python -m scripts.bootstrap --admin-password "ВашПароль123"
```

Либо через Alembic (рекомендуется для продакшена):

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 4. Запуск

```bash
# Backend (слушает только 127.0.0.1 — §10.4)
python -m backend.main
#   → http://127.0.0.1:8077/docs  (Swagger UI)

# GUI (в отдельном терминале)
python -m gui.app
```

### 5. Локальная LLM (оффлайн)

```bash
ollama pull llama3.1:8b
ollama pull bge-m3            # эмбеддинги для RAG
```

---

## Тесты

```bash
pip install -e ".[dev]"
pytest
```

Покрыты: криптография (§10), фабрика LLM-адаптеров и провайдеры из
`LLM.txt`, бизнес-логика тикетов (переходы статусов, гарантия, оценка
измерений), разбивка на чанки RAG.

---

## Соответствие спецификации

| Раздел спецификации              | Реализация                                  |
|----------------------------------|---------------------------------------------|
| §4 Данные                        | `backend/models/`                           |
| F-001..F-003 Тикеты              | `backend/services/ticket_service.py`        |
| F-004 LLM-диагностика            | `backend/services/diagnostics_service.py`   |
| F-005 Индексация RAG             | `backend/rag/indexer.py`                    |
| F-006 Поиск аналогов             | `backend/routers/components.py`             |
| F-007 Генерация PDF              | `backend/documents/`                        |
| §6.4 API                         | `backend/routers/`                          |
| §7.1 LLM Adapter                 | `backend/llm/`                              |
| §7.2 Qdrant-коллекции            | `backend/rag/vector_store.py`               |
| §8 RAG-промпты                   | `backend/prompts/diagnostics.py`            |
| §9 Документооборот               | `backend/documents/templates/`              |
| §10 Безопасность                 | `backend/core/security.py`, `routers/deps.py` |
| §11 Развёртывание                | `docker-compose.yml`, `.env.example`        |

---

*Версия 1.0. Стек и поведение соответствуют ТЗ и Формализованной
спецификации RepairExpert AI от 17 июня 2026.*
