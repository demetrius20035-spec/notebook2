# Формализованная Спецификация
## RepairExpert AI — Экспертная система компонентного ремонта электроники

---

**Документ:** ФС-RepairExpert-1.0  
**На основании:** ТЗ RepairExpert AI v1.0  
**Дата:** 17 июня 2026  
**Статус:** К согласованию  

---

## Содержание

1. [Глоссарий](#1-глоссарий)
2. [Контекст и границы системы](#2-контекст-и-границы-системы)
3. [Роли и права доступа](#3-роли-и-права-доступа)
4. [Спецификация данных](#4-спецификация-данных)
5. [Спецификация функций](#5-спецификация-функций)
6. [Спецификация интерфейсов](#6-спецификация-интерфейсов)
7. [Спецификация интеграций](#7-спецификация-интеграций)
8. [Спецификация RAG-подсистемы](#8-спецификация-rag-подсистемы)
9. [Спецификация документооборота](#9-спецификация-документооборота)
10. [Спецификация безопасности](#10-спецификация-безопасности)
11. [Спецификация развёртывания](#11-спецификация-развёртывания)
12. [Нефункциональные спецификации](#12-нефункциональные-спецификации)
13. [Матрица трассировки требований](#13-матрица-трассировки-требований)

---

## 1. Глоссарий

| Термин              | Определение |
|---------------------|-------------|
| **Тикет**           | Ремонтная заявка — основная рабочая единица системы, объединяющая клиента, устройство, журнал работ и документы |
| **Журнал ремонта**  | Хронологический лог всех действий инженера по конкретному тикету |
| **Карта измерений** | Структурированная таблица напряжений/токов/сопротивлений по линиям питания устройства |
| **Чанк**            | Фрагмент текста (512 токенов) для векторного индексирования в Qdrant |
| **Эмбеддинг**       | Векторное представление текстового чанка, используемое для семантического поиска |
| **RAG**             | Retrieval-Augmented Generation — метод обогащения запросов к LLM релевантными фрагментами из базы знаний |
| **LLM Adapter**     | Слой абстракции для унифицированного взаимодействия с различными языковыми моделями |
| **Платформа**       | Ревизия платы устройства (например, NM-D221, LA-B181P) |
| **Boardview**       | Файл с интерактивной картой печатной платы |
| **PMIC**            | Power Management Integrated Circuit — микросхема управления питанием |
| **VRM**             | Voltage Regulator Module — модуль регулировки напряжения |
| **ЛБП**             | Лабораторный блок питания |
| **MinIO**           | S3-совместимый объектный сервер для локального хранения файлов |
| **Qdrant**          | Специализированная векторная база данных для хранения и поиска эмбеддингов |
| **Alembic**         | Инструмент версионирования схемы БД для SQLAlchemy |
| **Part Number**     | Уникальный артикул электронного компонента |
| **Аналог**          | Электронный компонент, совместимый по параметрам и корпусу с оригинальным |

---

## 2. Контекст и границы системы

### 2.1. Контекстная диаграмма

```
                    ┌─────────────┐
                    │  Инженер    │
                    └──────┬──────┘
                           │ Ведение ремонта,
                           │ диагностика, измерения
                           │
┌──────────┐    ┌──────────▼───────────────┐    ┌──────────────┐
│ Клиент   │───▶│                          │───▶│  LLM API     │
│          │    │     RepairExpert AI      │    │ (Grok/OpenAI/│
│          │◀───│                          │◀───│  Claude/     │
└──────────┘    │                          │    │  Ollama)     │
                │                          │    └──────────────┘
┌──────────┐    │                          │    ┌──────────────┐
│Приёмщик  │───▶│                          │───▶│  Принтер /   │
└──────────┘    └──────────────────────────┘    │  PDF-файл    │
                           │                    └──────────────┘
┌──────────┐               │
│Поставщик │───▶  [Каталог │компонентов / цен]
└──────────┘
```

### 2.2. Границы системы

**В системе:**
- Управление клиентами и устройствами.
- Полный цикл ремонта от приёмки до выдачи.
- Журнал действий и карта измерений.
- База компонентов со складским учётом.
- Документооборот и печать.
- Финансовый учёт в рамках сервисного центра.
- База знаний и RAG-поиск.
- Интеграция с LLM через единый адаптер.

**За пределами системы:**
- Бухгалтерский учёт (налоги, двойная запись) — только выгрузка данных.
- Интернет-витрина или портал самообслуживания клиентов.
- Автоматический парсинг схем и boardview (только просмотр и ручная аннотация).
- Управление несколькими филиалами (версия 2.0).

---

## 3. Роли и права доступа

### 3.1. Матрица прав

| Функция                         | Администратор | Инженер | Приёмщик | Кладовщик | Бухгалтер |
|---------------------------------|:---:|:---:|:---:|:---:|:---:|
| Управление пользователями        | ✔   | ✘   | ✘   | ✘   | ✘   |
| Настройки системы               | ✔   | ✘   | ✘   | ✘   | ✘   |
| Создание клиентов               | ✔   | ✔   | ✔   | ✘   | ✘   |
| Редактирование клиентов         | ✔   | ✔   | ✔   | ✘   | ✘   |
| Просмотр клиентов               | ✔   | ✔   | ✔   | ✘   | ✔   |
| Создание тикетов                | ✔   | ✔   | ✔   | ✘   | ✘   |
| Редактирование тикетов          | ✔   | ✔   | ✘   | ✘   | ✘   |
| Просмотр тикетов                | ✔   | ✔   | ✔   | ✘   | ✔   |
| Работа с журналом ремонта       | ✔   | ✔   | ✘   | ✘   | ✘   |
| Использование AI / LLM          | ✔   | ✔   | ✘   | ✘   | ✘   |
| Работа с базой знаний           | ✔   | ✔   | ✘   | ✘   | ✘   |
| Редактирование компонентов      | ✔   | ✔   | ✘   | ✔   | ✘   |
| Складские операции              | ✔   | ✘   | ✘   | ✔   | ✘   |
| Печать документов               | ✔   | ✔   | ✔   | ✘   | ✔   |
| Финансовые отчёты               | ✔   | ✘   | ✘   | ✘   | ✔   |
| Управление поставщиками         | ✔   | ✘   | ✘   | ✔   | ✘   |
| Резервное копирование           | ✔   | ✘   | ✘   | ✘   | ✘   |
| Журнал аудита                   | ✔   | ✘   | ✘   | ✘   | ✘   |

### 3.2. Спецификация сессии

- Сессия хранится в виде JWT-токена (время жизни: 8 часов, опционально — «Запомнить меня» 30 дней).
- При смене пароля все активные сессии пользователя аннулируются.
- Неактивная сессия автоматически завершается через 30 минут (настраивается).
- Максимальное число одновременных сессий одного пользователя: 3.

---

## 4. Спецификация данных

### 4.1. Сущность: `users`

```sql
CREATE TABLE users (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    username        VARCHAR(50)     UNIQUE NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,               -- bcrypt
    full_name       VARCHAR(150)    NOT NULL,
    role            ENUM('admin','master','receiver',
                         'storekeeper','accountant','viewer') NOT NULL,
    phone           VARCHAR(30),
    email           VARCHAR(100),
    is_active       BOOLEAN         DEFAULT TRUE,
    last_login_at   DATETIME,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Ограничения:**
- `username` — латинские буквы, цифры, знак подчёркивания, длина 3–50 символов.
- `password_hash` — bcrypt, cost factor ≥ 12.
- Удаление пользователя запрещено; используется флаг `is_active = FALSE`.

---

### 4.2. Сущность: `clients`

```sql
CREATE TABLE clients (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    full_name       VARCHAR(150)    NOT NULL,
    phone           VARCHAR(30)     UNIQUE,
    email           VARCHAR(100),
    address         TEXT,
    birth_date      DATE,
    notes           TEXT,
    is_blacklisted  BOOLEAN         DEFAULT FALSE,
    blacklist_reason TEXT,
    client_tier     ENUM('new','regular','vip') DEFAULT 'new',
    total_repairs   INT             DEFAULT 0,             -- триггер
    total_paid      DECIMAL(14,2)   DEFAULT 0.00,          -- триггер
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Бизнес-правило BR-001:** `client_tier` пересчитывается триггером при изменении `total_repairs`:
- `new` — 0–2 ремонта.
- `regular` — 3–9 ремонтов.
- `vip` — 10 и более ремонтов.

---

### 4.3. Сущность: `devices`

```sql
CREATE TABLE devices (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    client_id       BIGINT,
    device_type_id  BIGINT          NOT NULL,
    manufacturer_id BIGINT          NOT NULL,
    model_name      VARCHAR(150)    NOT NULL,
    platform_id     BIGINT,                                -- ревизия платы
    serial_number   VARCHAR(100),
    imei            VARCHAR(20),
    imei2           VARCHAR(20),
    device_password VARCHAR(512),                          -- AES-256
    condition_note  TEXT,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id)       REFERENCES clients(id),
    FOREIGN KEY (device_type_id)  REFERENCES device_types(id),
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
    FOREIGN KEY (platform_id)     REFERENCES platforms(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Ограничение:** `imei` — ровно 15 цифр (проверка на уровне приложения и CHECK-constraint).

---

### 4.4. Сущность: `repair_tickets`

```sql
CREATE TABLE repair_tickets (
    id                  BIGINT          PRIMARY KEY AUTO_INCREMENT,
    ticket_number       VARCHAR(30)     UNIQUE NOT NULL,    -- РМ-2026-00001
    client_id           BIGINT          NOT NULL,
    device_id           BIGINT          NOT NULL,
    receiver_id         BIGINT          NOT NULL,
    master_id           BIGINT,
    status              ENUM(
                          'new',            -- Принят
                          'diagnostics',    -- Диагностика
                          'in_repair',      -- В работе
                          'waiting_parts',  -- Ожидание деталей
                          'waiting_client', -- Ожидание клиента
                          'ready',          -- Готов
                          'delivered',      -- Выдан
                          'closed',         -- Закрыт
                          'warranty'        -- Гарантийный случай
                        ) NOT NULL DEFAULT 'new',
    priority            ENUM('normal','high','urgent') DEFAULT 'normal',
    problem_description TEXT            NOT NULL,
    diagnostic_result   TEXT,
    repair_description  TEXT,
    cost_estimate       DECIMAL(12,2)   DEFAULT 0.00,      -- смета
    cost_final          DECIMAL(12,2)   DEFAULT 0.00,      -- итог
    paid_amount         DECIMAL(12,2)   DEFAULT 0.00,
    warranty_months     TINYINT         DEFAULT 3,
    warranty_expires_at DATE,                               -- триггер
    notes               TEXT,
    accepted_at         DATETIME        DEFAULT CURRENT_TIMESTAMP,
    diagnostics_at      DATETIME,
    started_at          DATETIME,
    completed_at        DATETIME,
    delivered_at        DATETIME,
    closed_at           DATETIME,
    FOREIGN KEY (client_id)   REFERENCES clients(id),
    FOREIGN KEY (device_id)   REFERENCES devices(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id),
    FOREIGN KEY (master_id)   REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Бизнес-правило BR-002:** При переходе статуса в `delivered` триггер вычисляет `warranty_expires_at = delivered_at + INTERVAL warranty_months MONTH`.

**Бизнес-правило BR-003:** Генерация `ticket_number` — формат `РМ-YYYY-NNNNN`, где NNNNN — сквозной счётчик с дополнением нулями (auto-increment отдельной таблицы `ticket_sequences`).

---

### 4.5. Сущность: `repair_history`

```sql
CREATE TABLE repair_history (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    ticket_id       BIGINT          NOT NULL,
    user_id         BIGINT          NOT NULL,
    entry_type      ENUM(
                      'measurement',  -- Измерение
                      'replacement',  -- Замена компонента
                      'note',         -- Заметка
                      'ai_query',     -- Запрос к AI
                      'photo',        -- Фото
                      'solder',       -- Пайка
                      'flash',        -- Прошивка
                      'test',         -- Тест
                      'status_change',-- Смена статуса
                      'payment'       -- Оплата
                    ) NOT NULL,
    title           VARCHAR(255),
    content         TEXT,
    duration_sec    INT,                                    -- время на действие
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES repair_tickets(id),
    FOREIGN KEY (user_id)   REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.6. Сущность: `repair_measurements`

```sql
CREATE TABLE repair_measurements (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    ticket_id       BIGINT          NOT NULL,
    user_id         BIGINT          NOT NULL,
    line_name       VARCHAR(100)    NOT NULL,   -- например: +3VALW, VIN, VBAT
    value_measured  DECIMAL(10,4),              -- измеренное значение
    value_norm      DECIMAL(10,4),              -- норма
    unit            VARCHAR(20)     DEFAULT 'V',-- V, A, Ohm, mV
    status          ENUM('ok','fail','warn') DEFAULT 'ok',
    notes           VARCHAR(255),
    measured_at     DATETIME        DEFAULT CURRENT_TIMESTAMP,
    phase           ENUM('before','during','after') DEFAULT 'before',
    FOREIGN KEY (ticket_id) REFERENCES repair_tickets(id),
    FOREIGN KEY (user_id)   REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.7. Сущность: `components`

```sql
CREATE TABLE components (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    part_number     VARCHAR(100)    UNIQUE,
    name            VARCHAR(200)    NOT NULL,
    category        VARCHAR(80)     NOT NULL,   -- MOSFET, PMIC, Capacitor, etc.
    manufacturer    VARCHAR(100),
    package_type    VARCHAR(50),                -- QFN32, TO-220, 0603, etc.
    voltage_max     DECIMAL(8,3),
    current_max     DECIMAL(8,3),
    resistance      DECIMAL(12,6),
    frequency       DECIMAL(12,3),
    extra_params    JSON,                       -- дополнительные параметры
    description     TEXT,
    datasheet_path  VARCHAR(512),              -- путь к файлу в хранилище
    embedding_id    VARCHAR(100),              -- ID в Qdrant
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.8. Сущность: `component_analogs`

```sql
CREATE TABLE component_analogs (
    id                  BIGINT  PRIMARY KEY AUTO_INCREMENT,
    component_id        BIGINT  NOT NULL,
    analog_id           BIGINT  NOT NULL,
    compatibility       ENUM('full','partial','pinout_diff') DEFAULT 'full',
    notes               VARCHAR(255),
    FOREIGN KEY (component_id) REFERENCES components(id),
    FOREIGN KEY (analog_id)    REFERENCES components(id),
    UNIQUE KEY uq_analog_pair (component_id, analog_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

### 4.9. Сущность: `inventory`

```sql
CREATE TABLE inventory (
    component_id    BIGINT          PRIMARY KEY,
    quantity        INT             NOT NULL DEFAULT 0,
    quantity_reserved INT           DEFAULT 0,             -- зарезервировано в ремонтах
    min_stock       INT             DEFAULT 5,
    price_purchase  DECIMAL(10,2),
    price_sale      DECIMAL(10,2),
    location        VARCHAR(100),
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (component_id) REFERENCES components(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Бизнес-правило BR-004:** `quantity_available = quantity - quantity_reserved`. При `quantity_available < min_stock` система генерирует уведомление типа `low_stock`.

---

### 4.10. Сущность: `knowledge_base`

```sql
CREATE TABLE knowledge_base (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    title           VARCHAR(255)    NOT NULL,
    content         MEDIUMTEXT,
    source_type     ENUM('article','datasheet','manual',
                         'note','repair_case','forum') NOT NULL,
    source_ref_id   BIGINT,                                -- ссылка на repair_ticket или component
    tags            JSON,                                  -- ["lenovo","T14","pmic"]
    language        VARCHAR(10)     DEFAULT 'ru',
    is_published    BOOLEAN         DEFAULT TRUE,
    author_id       BIGINT,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.11. Сущность: `knowledge_chunks`

```sql
CREATE TABLE knowledge_chunks (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    kb_id           BIGINT          NOT NULL,
    chunk_index     INT             NOT NULL,
    chunk_text      TEXT            NOT NULL,
    embedding_id    VARCHAR(100)    UNIQUE,               -- ID вектора в Qdrant
    token_count     INT,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kb_id) REFERENCES knowledge_base(id) ON DELETE CASCADE,
    UNIQUE KEY uq_kb_chunk (kb_id, chunk_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.12. Сущность: `suppliers`

```sql
CREATE TABLE suppliers (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(150)    NOT NULL,
    website         VARCHAR(255),
    phone           VARCHAR(30),
    email           VARCHAR(100),
    contact_person  VARCHAR(150),
    country         VARCHAR(80),
    delivery_days   TINYINT,
    min_order_amount DECIMAL(10,2),
    notes           TEXT,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.13. Сущность: `payments`

```sql
CREATE TABLE payments (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    ticket_id       BIGINT          NOT NULL,
    user_id         BIGINT          NOT NULL,              -- кто принял оплату
    amount          DECIMAL(12,2)   NOT NULL,
    payment_type    ENUM('prepayment','final','refund') NOT NULL,
    method          ENUM('cash','card','transfer','other') DEFAULT 'cash',
    notes           VARCHAR(255),
    paid_at         DATETIME        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES repair_tickets(id),
    FOREIGN KEY (user_id)   REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4.14. Сущность: `audit_log`

```sql
CREATE TABLE audit_log (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT,
    user_id         BIGINT,
    action          VARCHAR(100)    NOT NULL,              -- CREATE_TICKET, DELETE_CLIENT и т.д.
    entity_type     VARCHAR(50),
    entity_id       BIGINT,
    old_value       JSON,
    new_value       JSON,
    ip_address      VARCHAR(45),
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 5. Спецификация функций

### 5.1. Функция F-001: Создание тикета

**Предусловие:** Пользователь авторизован с ролью `admin`, `master` или `receiver`.

**Входные данные:**

| Поле                | Тип           | Обязательно | Валидация                              |
|---------------------|---------------|:-----------:|----------------------------------------|
| `client_id`         | BIGINT        | Да          | Существующий клиент                    |
| `device_id`         | BIGINT        | Нет         | Если не передан — создаётся новое      |
| `problem_description` | TEXT        | Да          | Длина 5–5000 символов                  |
| `priority`          | ENUM          | Нет         | Значение из допустимого перечня        |
| `master_id`         | BIGINT        | Нет         | Инженер с ролью `master`               |
| `photos[]`          | FILE[]        | Нет         | JPEG/PNG, до 20 МБ каждый             |

**Алгоритм:**
1. Валидация входных данных.
2. Если `device_id` не передан — создать устройство.
3. Сгенерировать `ticket_number` через `ticket_sequences`.
4. Создать запись в `repair_tickets` со статусом `new`.
5. Сохранить фото в хранилище → добавить записи в `attachments`.
6. Добавить запись в `repair_history` типа `status_change`.
7. Добавить запись в `audit_log`.
8. Вернуть объект созданного тикета.

**Постусловие:** Тикет создан, номер уникален, фото сохранены, история начата.

---

### 5.2. Функция F-002: Смена статуса тикета

**Допустимые переходы статусов:**

```
new ──────────────────────▶ diagnostics
diagnostics ──────────────▶ in_repair
diagnostics ──────────────▶ waiting_parts
diagnostics ──────────────▶ waiting_client
in_repair ────────────────▶ waiting_parts
in_repair ────────────────▶ waiting_client
in_repair ────────────────▶ ready
waiting_parts ────────────▶ in_repair
waiting_client ───────────▶ in_repair
ready ────────────────────▶ delivered
delivered ────────────────▶ closed
delivered ────────────────▶ warranty (гарантийный случай)
warranty ─────────────────▶ in_repair
любой ────────────────────▶ closed (только admin)
```

**Алгоритм при смене статуса:**
1. Проверить допустимость перехода по матрице выше.
2. Обновить поле статуса и соответствующее поле метки времени.
3. Если статус `delivered`: вычислить `warranty_expires_at`.
4. Записать в `repair_history` тип `status_change` с указанием `old_status → new_status`.
5. Обновить `clients.total_repairs` при переходе в `closed`.
6. Записать в `audit_log`.

---

### 5.3. Функция F-003: Добавление измерения в карту

**Входные данные:**

| Поле             | Тип          | Обязательно | Описание                                |
|------------------|--------------|:-----------:|-----------------------------------------|
| `ticket_id`      | BIGINT       | Да          | ID тикета                               |
| `line_name`      | VARCHAR(100) | Да          | Название линии питания (VIN, +5V, и т.д.) |
| `value_measured` | DECIMAL      | Да          | Измеренное значение                     |
| `value_norm`     | DECIMAL      | Нет         | Нормальное значение                     |
| `unit`           | VARCHAR(20)  | Нет         | V / A / Ohm / mV (по умолчанию V)      |
| `phase`          | ENUM         | Нет         | before / during / after                 |

**Алгоритм:**
1. Сохранить в `repair_measurements`.
2. Вычислить `status`: если `value_norm` задан — сравнить с допуском ±10%.
3. Добавить запись в `repair_history` типа `measurement`.
4. Вернуть обновлённую карту измерений тикета.

---

### 5.4. Функция F-004: Запрос к LLM-диагностике

**Входные данные:**

| Поле         | Тип    | Описание                          |
|--------------|--------|-----------------------------------|
| `ticket_id`  | BIGINT | Текущий тикет                     |
| `mode`       | ENUM   | `next_step` / `chat` / `wizard`   |
| `user_query` | TEXT   | Вопрос пользователя (для `chat`)  |

**Алгоритм:**
1. Собрать контекст из тикета:
   - Устройство, платформа, симптомы.
   - Последние 20 записей журнала.
   - Все измерения.
   - Список заменённых компонентов.
2. Выполнить RAG-запрос в Qdrant (индексы `repair_vectors` + `datasheet_vectors`):
   - Top-5 похожих ремонтов.
   - Top-3 релевантных чанков даташитов.
3. Сформировать системный промпт с ролью инженера-диагностика.
4. Отправить запрос через LLM Adapter к выбранному провайдеру.
5. Сохранить запрос и ответ в `repair_history` типа `ai_query`.
6. Вернуть ответ пользователю со ссылками на источники RAG.

---

### 5.5. Функция F-005: Индексация документа в RAG

**Входные данные:** файл (PDF, TXT, MD), тип источника.

**Алгоритм:**
```
Входной файл
    │
    ├── PDF с текстовым слоем ──▶ pdfminer → текст
    ├── PDF-скан              ──▶ Tesseract OCR → текст
    └── TXT / MD              ──▶ прямое чтение
    │
    ▼
Очистка текста (удаление артефактов OCR, нормализация)
    │
    ▼
Разбивка на чанки (512 токенов, перекрытие 64 токена)
    │
    ▼
Сохранение чанков в MariaDB (knowledge_chunks)
    │
    ▼
Генерация эмбеддингов (BGE-M3 / nomic-embed-text)
    │
    ▼
Загрузка в Qdrant с payload: {kb_id, chunk_id, source_type}
    │
    ▼
Обновление embedding_id в knowledge_chunks
```

---

### 5.6. Функция F-006: Поиск аналога компонента

**Входные данные:** `part_number` или `component_id`.

**Алгоритм:**
1. Поиск прямых аналогов в `component_analogs`.
2. Если прямых нет — семантический поиск по Qdrant (индекс компонентов) по описанию и параметрам.
3. Фильтрация по корпусу и ключевым параметрам (напряжение ±15%, ток ±15%).
4. Возврат ранжированного списка с указанием совместимости.

---

### 5.7. Функция F-007: Генерация PDF-документа

**Входные данные:** `ticket_id`, `document_type`.

**Алгоритм:**
1. Загрузить данные тикета, клиента, устройства, компонентов, платежей.
2. Выбрать шаблон Jinja2 по `document_type`.
3. Рендеринг HTML из шаблона с данными.
4. Конвертация HTML → PDF через WeasyPrint.
5. Сохранение в хранилище: `storage/repairs/{ticket_id}/documents/`.
6. Создание записи в `documents`.
7. Добавление в `repair_history` типа `note`.
8. Возврат пути к файлу.

---

## 6. Спецификация интерфейсов

### 6.1. Главное окно приложения

**Структура навигации:**

```
Главное окно (QMainWindow)
├── Панель навигации (левая)
│   ├── 📋 Тикеты
│   ├── 👥 Клиенты
│   ├── 🔧 Компоненты
│   ├── 📚 База знаний
│   ├── 🏪 Склад
│   ├── 💰 Финансы
│   ├── 📊 Аналитика
│   └── ⚙️ Настройки
├── Панель уведомлений (верхняя)
│   └── Просроченные тикеты / Низкий склад
└── Рабочая область (центр)
    └── Вкладки открытых документов (MDI)
```

---

### 6.2. Карточка тикета (главный экран работы)

**Макет:**

```
┌─────────────────────────────────────────────────────────────────┐
│  РМ-2026-00123  │  Lenovo ThinkPad T14  │  Статус: В работе    │
│  Клиент: Иван Петров  │  Инженер: Смирнов А.  │  Приоритет: ✦   │
├─────────────────────────────────────────────────────────────────┤
│ [Журнал] [Измерения] [Компоненты] [AI Ассистент] [Документы]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Вкладка «Журнал»:                                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 10:01  [ПРИНЯТ]    Устройство принято на ремонт         │    │
│  │ 10:07  [ИЗМЕРЕНИЕ] VIN = 19.4V ✔  +3VALW = 3.3V ✔     │    │
│  │ 10:09  [ИЗМЕРЕНИЕ] +5VALW = 0V ✖                        │    │
│  │ 10:12  [AI]        Вероятность: TPS51225 62%            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  [+ Добавить запись]  [📷 Фото]  [🤖 Спросить AI]               │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6.3. Вкладка «AI Ассистент»

**Режимы (RadioButton):**
- 🎯 Следующий шаг — одно нажатие, получить рекомендацию.
- 🧙 Мастер диагностики — пошаговый интерактивный режим.
- 💬 Свободный чат — произвольный диалог с контекстом тикета.

**Панель результата:**
- Список гипотез с вероятностью (прогресс-бар).
- Рекомендуемое измерение с указанием точки на плате.
- Блок «Похожие ремонты» (ссылки на тикеты из RAG).
- Блок «Из даташита» (фрагмент с указанием источника).

---

### 6.4. API (FastAPI) — ключевые эндпоинты

**Аутентификация:**
```
POST /api/v1/auth/login          → {access_token, expires_in}
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
```

**Клиенты:**
```
GET    /api/v1/clients           → list
POST   /api/v1/clients           → create
GET    /api/v1/clients/{id}      → detail
PUT    /api/v1/clients/{id}      → update
GET    /api/v1/clients/{id}/tickets → история ремонтов
```

**Тикеты:**
```
GET    /api/v1/tickets           → list (фильтры: status, master, date)
POST   /api/v1/tickets           → create
GET    /api/v1/tickets/{id}      → detail (полный объект)
PATCH  /api/v1/tickets/{id}      → update fields
POST   /api/v1/tickets/{id}/status    → смена статуса
POST   /api/v1/tickets/{id}/measurements  → добавить измерение
POST   /api/v1/tickets/{id}/history      → добавить запись журнала
POST   /api/v1/tickets/{id}/attachments  → загрузить файл
GET    /api/v1/tickets/{id}/documents    → список документов
POST   /api/v1/tickets/{id}/documents    → сгенерировать документ
```

**AI:**
```
POST   /api/v1/ai/diagnose       → {ticket_id, mode, query} → ответ LLM
POST   /api/v1/ai/search         → семантический поиск
GET    /api/v1/ai/providers      → список доступных LLM-провайдеров
```

**Компоненты:**
```
GET    /api/v1/components        → list (поиск по part_number, name)
POST   /api/v1/components        → create
GET    /api/v1/components/{id}   → detail
GET    /api/v1/components/{id}/analogs → аналоги
GET    /api/v1/components/{id}/stats   → статистика использования
```

**Ответ API:**
```json
{
  "status": "ok" | "error",
  "data": { ... },
  "meta": { "total": 100, "page": 1, "per_page": 20 },
  "error": { "code": "VALIDATION_ERROR", "message": "...", "details": {} }
}
```

---

## 7. Спецификация интеграций

### 7.1. LLM Adapter

**Интерфейс адаптера (Python ABC):**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator

@dataclass
class LLMMessage:
    role: str          # "system" | "user" | "assistant"
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int

class BaseLLMAdapter(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
    ) -> AsyncGenerator[str, None]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

**Реализованные адаптеры:**

| Класс                  | Провайдер           | Базовый URL                             |
|------------------------|---------------------|-----------------------------------------|
| `GrokAdapter`          | xAI Grok            | `https://api.x.ai/v1`                  |
| `OpenAIAdapter`        | OpenAI              | `https://api.openai.com/v1`            |
| `AnthropicAdapter`     | Anthropic Claude    | `https://api.anthropic.com/v1`         |
| `OllamaAdapter`        | Ollama (локально)   | `http://localhost:11434`               |
| `OpenRouterAdapter`    | OpenRouter          | `https://openrouter.ai/api/v1`         |
| `LMStudioAdapter`      | LM Studio           | `http://localhost:1234/v1`             |
| `OpenAICompatAdapter`  | vLLM / llama.cpp    | Настраивается пользователем            |

---

### 7.2. Qdrant — спецификация коллекций

**Коллекция `repair_vectors`:**

```json
{
  "name": "repair_vectors",
  "vectors": { "size": 1024, "distance": "Cosine" },
  "payload_schema": {
    "ticket_id":   "integer",
    "chunk_id":    "integer",
    "status":      "keyword",
    "device_type": "keyword",
    "platform":    "keyword",
    "created_at":  "datetime"
  }
}
```

**Коллекция `datasheet_vectors`:**

```json
{
  "name": "datasheet_vectors",
  "vectors": { "size": 1024, "distance": "Cosine" },
  "payload_schema": {
    "kb_id":        "integer",
    "chunk_id":     "integer",
    "part_number":  "keyword",
    "component_id": "integer"
  }
}
```

**Коллекция `knowledge_vectors`:**

```json
{
  "name": "knowledge_vectors",
  "vectors": { "size": 1024, "distance": "Cosine" },
  "payload_schema": {
    "kb_id":       "integer",
    "chunk_id":    "integer",
    "source_type": "keyword",
    "tags":        "keyword[]"
  }
}
```

**Размерность эмбеддингов:** 1024 (BGE-M3) или 768 (nomic-embed-text). Выбор модели — в настройках системы. Изменение модели требует полной переиндексации.

---

### 7.3. MariaDB — индексы

```sql
-- Тикеты
CREATE INDEX idx_rt_status        ON repair_tickets(status);
CREATE INDEX idx_rt_client        ON repair_tickets(client_id);
CREATE INDEX idx_rt_master        ON repair_tickets(master_id);
CREATE INDEX idx_rt_accepted      ON repair_tickets(accepted_at);
CREATE INDEX idx_rt_number        ON repair_tickets(ticket_number);

-- Журнал
CREATE INDEX idx_rh_ticket        ON repair_history(ticket_id, created_at);
CREATE INDEX idx_rh_type          ON repair_history(entry_type);

-- Измерения
CREATE INDEX idx_rm_ticket        ON repair_measurements(ticket_id);
CREATE INDEX idx_rm_line          ON repair_measurements(line_name);

-- Компоненты
CREATE INDEX idx_comp_part        ON components(part_number);
CREATE INDEX idx_comp_category    ON components(category);

-- Клиенты
CREATE INDEX idx_cli_phone        ON clients(phone);
CREATE INDEX idx_cli_tier         ON clients(client_tier);

-- Знания
CREATE INDEX idx_kb_source        ON knowledge_base(source_type);
CREATE INDEX idx_kc_embedding     ON knowledge_chunks(embedding_id);

-- Аудит
CREATE INDEX idx_al_user          ON audit_log(user_id, created_at);
CREATE INDEX idx_al_entity        ON audit_log(entity_type, entity_id);
```

---

## 8. Спецификация RAG-подсистемы

### 8.1. Стартовый промпт для диагностики

```
Системный промпт (инвариантная часть):

Ты — опытный инженер по компонентному ремонту электроники с 15-летним 
стажем. Ты работаешь в режиме диагностики конкретного устройства.

Правила работы:
1. Не перескакивай через этапы диагностики.
2. Для каждого рекомендуемого измерения указывай: где именно измерять, 
   что должно быть в норме, что означает отклонение.
3. Оценивай вероятность каждой гипотезы в процентах.
4. После каждого нового измерения пересматривай гипотезы.
5. Не предлагай замену платы целиком, пока не исключены компонентные 
   неисправности.
6. Для ноутбуков всегда соблюдай последовательность:
   VIN → Защита → Дежурные напряжения → EC/MUX → Кнопка → S5 → 
   S3 → S0 → VRM CPU → Инициализация → Изображение.
7. Для смартфонов: VBAT → VPH_PWR → PMIC → основные линии → 
   потребление тока → нагрев → CPU/RAM/UFS.
```

### 8.2. Контекстный блок (генерируется динамически)

```
=== ТЕКУЩИЙ РЕМОНТ ===
Устройство: {device_manufacturer} {device_model}
Платформа: {platform_name}
Симптом: {problem_description}
Оборудование: {available_tools}

=== КАРТА ИЗМЕРЕНИЙ ===
{measurements_table}

=== ЖУРНАЛ РЕМОНТА (последние 10 записей) ===
{repair_history_last_10}

=== ПОХОЖИЕ РЕМОНТЫ ИЗ БАЗЫ ===
{rag_similar_repairs}

=== РЕЛЕВАНТНЫЕ ДАТАШИТЫ ===
{rag_datasheet_chunks}

=== ВОПРОС ИНЖЕНЕРА ===
{user_query}
```

### 8.3. Параметры RAG-поиска

| Параметр                     | Значение              |
|------------------------------|-----------------------|
| Top-K ремонтов               | 5                     |
| Top-K даташит-чанков         | 3                     |
| Минимальный score            | 0.72                  |
| Размер чанка                 | 512 токенов           |
| Перекрытие чанков            | 64 токена             |
| Размерность вектора          | 1024 (BGE-M3)         |
| Метрика расстояния           | Cosine similarity     |

---

## 9. Спецификация документооборота

### 9.1. Шаблоны документов

Все шаблоны — Jinja2 HTML, конвертируются через WeasyPrint.

**Реквизиты из настроек системы** (применяются ко всем документам):
```
org_name, org_inn, org_address, org_phone, org_email, org_logo_path
```

### 9.2. Квитанция о приёмке (`acceptance`)

**Обязательные поля:**
- Номер тикета, дата приёмки.
- ФИО клиента, телефон.
- Описание устройства (тип, производитель, модель, серийный номер).
- Комплектация (что принято вместе с устройством).
- Описание проблемы со слов клиента.
- Предварительная стоимость (если озвучена).
- Срок готовности (если установлен).
- Подписи: приёмщик / клиент.
- QR-код для проверки статуса.

### 9.3. Акт выполненных работ (`act`)

**Обязательные поля:**
- Номер тикета и акта.
- Описание выполненных работ.
- Перечень заменённых компонентов с ценами.
- Стоимость работ.
- Итого к оплате.
- Гарантийный срок.
- Подписи.

### 9.4. Дефектовочная ведомость (`defect`)

**Обязательные поля:**
- Выявленные неисправности.
- Перечень необходимых работ и компонентов.
- Предварительная стоимость.
- Согласие/отказ клиента.

### 9.5. Гарантийный талон (`warranty`)

**Обязательные поля:**
- Описание выполненных работ.
- Дата выдачи, срок гарантии, дата истечения.
- Условия гарантии (что покрывает, что не покрывает).
- Подпись мастера.

---

## 10. Спецификация безопасности

### 10.1. Аутентификация и авторизация

- Алгоритм хэширования паролей: bcrypt, cost factor = 12.
- JWT токен: алгоритм HS256, секрет ≥ 256 бит из `.env`.
- Время жизни access_token: 8 часов.
- Время жизни refresh_token: 30 дней (опционально).
- Rate limit на `/auth/login`: 10 попыток в минуту с одного IP, затем блокировка на 15 минут.

### 10.2. Шифрование чувствительных данных

- Поле `devices.device_password`: AES-256-GCM.
- Ключ шифрования хранится в `.env` (не в БД).
- API-ключи LLM-провайдеров: хранятся зашифрованными в `settings` таблице.

### 10.3. Аудит

Обязательному логированию в `audit_log` подлежат:

| Действие                      | Запись                              |
|-------------------------------|-------------------------------------|
| Вход / выход                  | `AUTH_LOGIN`, `AUTH_LOGOUT`         |
| Создание тикета               | `CREATE_TICKET`                     |
| Смена статуса тикета          | `TICKET_STATUS_CHANGE`              |
| Генерация документа           | `DOCUMENT_GENERATE`                 |
| Изменение данных клиента      | `UPDATE_CLIENT`                     |
| Удаление любой записи         | `DELETE_*`                          |
| Изменение настроек системы    | `UPDATE_SETTINGS`                   |
| Операции со складом           | `INVENTORY_MOVE`                    |
| Изменение данных пользователя | `UPDATE_USER`                       |

### 10.4. Сетевая безопасность

- FastAPI backend слушает только `127.0.0.1` (не публичный интерфейс).
- HTTPS для внутреннего API с самоподписанным сертификатом.
- Qdrant и MariaDB привязаны к localhost или Docker-сети.

---

## 11. Спецификация развёртывания

### 11.1. Docker Compose

```yaml
version: '3.9'

services:
  mariadb:
    image: mariadb:11.3
    environment:
      MARIADB_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MARIADB_DATABASE: repair_expert
      MARIADB_USER: ${DB_USER}
      MARIADB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - mariadb_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "127.0.0.1:3306:3306"
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:v1.9.0
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "127.0.0.1:6333:6333"
      - "127.0.0.1:6334:6334"
    restart: unless-stopped

  minio:                              # опциональный сервис
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
    restart: unless-stopped

volumes:
  mariadb_data:
  qdrant_data:
  minio_data:
```

### 11.2. Переменные окружения (`.env`)

```ini
# База данных
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=repair_expert
DB_USER=repairapp
DB_PASSWORD=<strong_password>

# Qdrant
QDRANT_HOST=127.0.0.1
QDRANT_PORT=6333

# Файловое хранилище
STORAGE_BACKEND=local          # local | minio
STORAGE_LOCAL_PATH=./storage

# MinIO (если STORAGE_BACKEND=minio)
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_USER=<user>
MINIO_PASSWORD=<password>
MINIO_BUCKET=repairexpert

# Безопасность
JWT_SECRET=<256-bit-random-string>
DEVICE_PASSWORD_KEY=<AES-256-key>

# LLM (заполняются в настройках GUI, здесь — дефолты)
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Эмбеддинги
EMBEDDING_MODEL=bge-m3
EMBEDDING_BASE_URL=http://localhost:11434

# OCR
TESSERACT_CMD=/usr/bin/tesseract
TESSERACT_LANG=rus+eng
```

### 11.3. Минимальные системные требования

| Параметр         | Минимум            | Рекомендуется           |
|------------------|--------------------|-------------------------|
| ОС               | Windows 10 64-bit  | Windows 11 / Ubuntu 22  |
| CPU              | 4 ядра             | 8 ядер                  |
| RAM              | 8 ГБ               | 16 ГБ (32 ГБ с локальной LLM) |
| Диск             | 20 ГБ SSD          | 100+ ГБ SSD             |
| GPU              | Не требуется        | NVIDIA (для локальной LLM) |

---

## 12. Нефункциональные спецификации

### 12.1. Производительность

| Операция                                  | Цель (p95) |
|-------------------------------------------|-----------|
| Открытие карточки тикета                  | ≤ 500 мс  |
| Поиск клиента по телефону                 | ≤ 200 мс  |
| Полнотекстовый поиск по ремонтам          | ≤ 1000 мс |
| Семантический RAG-поиск (Qdrant)          | ≤ 2000 мс |
| Генерация PDF-документа                   | ≤ 3000 мс |
| Ответ LLM (зависит от провайдера/модели)  | ≤ 30 с    |
| Индексация одного PDF-даташита (A4, 50 стр) | ≤ 60 с  |
| Запуск приложения (холодный старт)        | ≤ 5 с     |

### 12.2. Надёжность

- Транзакции MariaDB: InnoDB с `transaction_isolation = READ-COMMITTED`.
- Graceful shutdown: при закрытии приложения — ожидание завершения текущих операций (таймаут 5 с).
- Автобэкап по расписанию: ежедневно в 03:00. Хранение последних 30 резервных копий.
- Восстановление из резервной копии: полный процесс за ≤ 15 минут.

### 12.3. Сопровождаемость

- Версионирование схемы БД через Alembic (каждое изменение — отдельная миграция).
- Все настройки через `.env` и GUI настроек (не в коде).
- Логи приложения: ротация по размеру (10 МБ), хранение 7 последних файлов.
- Уровни логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

---

## 13. Матрица трассировки требований

| ID требования ТЗ | Функция / Сущность                    | Раздел спецификации   | Статус     |
|------------------|---------------------------------------|-----------------------|------------|
| ТЗ-2.1           | CRM, карточка клиента                | 4.2, F-001            | Определён  |
| ТЗ-2.2           | Приёмка, тикет, печать               | 4.4, F-001, §9        | Определён  |
| ТЗ-2.3           | Журнал ремонта, измерения            | 4.5, 4.6, F-003       | Определён  |
| ТЗ-2.4           | LLM-диагностика                      | F-004, §7.1, §8       | Определён  |
| ТЗ-2.5           | RAG и база знаний                    | 4.10, 4.11, F-005, §8 | Определён  |
| ТЗ-2.6           | База знаний                          | 4.10, §6              | Определён  |
| ТЗ-2.7           | Компоненты, аналоги                  | 4.7, 4.8, F-006       | Определён  |
| ТЗ-2.8           | База платформ                        | 4.1 (platforms)       | Определён  |
| ТЗ-2.9           | Склад, поставщики                    | 4.9, 4.12             | Определён  |
| ТЗ-2.10          | Финансы, платежи                     | 4.13                  | Определён  |
| ТЗ-2.11          | Документооборот, PDF                 | F-007, §9             | Определён  |
| ТЗ-2.12          | Файловое хранилище                   | §11.1 (MinIO/local)   | Определён  |
| ТЗ-3.1           | Технический стек                     | §11                   | Определён  |
| ТЗ-3.4           | Безопасность                         | §10                   | Определён  |
| ТЗ-3.6           | Оффлайн-режим                        | §7.1 (OllamaAdapter)  | Определён  |

---

*Документ является формализованной спецификацией к ТЗ RepairExpert AI v1.0.*  
*Версия спецификации: 1.0. Дата: 17 июня 2026.*  
*Все спецификации подлежат уточнению в процессе проектирования и согласования с заказчиком.*
