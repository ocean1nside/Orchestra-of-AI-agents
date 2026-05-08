# Техническое задание: backend-окружение для агента поддержки вендоров

## 1. Назначение проекта

Нужно разработать backend-окружение для работы ИИ-агента технической поддержки вендоров.

Агент должен помогать вендорам отвечать на технические вопросы по приложению/кабинету, которым они пользуются: настройки, загрузка товаров, работа с разделами, уведомления, частые ошибки, инструкции и прочая документация.

На текущем этапе система не является мультивендорной платформой, CRM, личным кабинетом или системой управления пользователями. Вендоры как бизнес-сущность остаются во внешней системе заказчика.

В рамках этого проекта разрабатываются:

- backend-оркестр для управления знаниями, промтами, индексами, статусами и технической инфраструктурой;
- один агент `vendor-support-agent`;
- единая база знаний на основе документации приложения;
- каналы входа для виджета, Telegram и MAX;
- Docker-окружение;
- техническая и пользовательская документация;
- подготовка проекта к индексации через SocratiCode для работы в Cursor/Codex.

Пользовательский интерфейс не разрабатывается. Внешний интерфейс, админка или личный кабинет будут реализованы отдельно внешней системой заказчика поверх API.

---

## 2. Главный принцип архитектуры

Оркестр — это management/control API.

Оркестр не является runtime-прокси для пользовательских вопросов.

Пользовательские запросы идут напрямую в агентский слой:

```text
Widget  ───────┐
Telegram ──────┼──> vendor-support-agent ──> Postgres / Qdrant ──> LLM ──> response
MAX ───────────┘
```

Оркестр используется для управления техническими данными:

```text
orchestrator-api ──> Postgres / Qdrant / Redis / File Storage
```

Оркестр отвечает за:

- загрузку документов;
- хранение документов;
- запуск индексации;
- статусы индексации;
- управление чанками;
- управление промтами;
- просмотр статусов сервисов;
- технические логи;
- аудит действий;
- OpenAPI-документацию.

Агент имеет прямой доступ к общей БД и векторному индексу. Агент не должен обращаться к оркестру за знаниями через API.

---

## 3. Что не входит в MVP

В MVP не нужно делать:

- пользовательский интерфейс;
- админку;
- мультивендорный кабинет;
- управление внешними вендорами;
- управление пользователями заказчика;
- роли и права внешней системы;
- товары, заказы, каталоги, финансовые операции;
- отдельные базы знаний на каждого вендора;
- отдельные таблицы на каждого вендора;
- маршрутизацию runtime-запросов через оркестр;
- сложную аналитику;
- биллинги;
- Kubernetes.

---

## 4. Состав системы

### 4.1. `orchestrator-api`

Backend-сервис управления системой.

Назначение:

- Documents API;
- Indexing API;
- Prompts API;
- Agents Status API;
- Logs API;
- Health API;
- OpenAPI;
- техническая точка управления базой знаний.

### 4.2. `vendor-support-agent`

Основной агент технической поддержки вендоров.

Назначение:

- принимать сообщения из виджета;
- принимать сообщения через Telegram-адаптер;
- принимать сообщения через MAX-адаптер;
- искать релевантные чанки документации;
- собирать промт;
- вызывать LLM;
- возвращать ответ;
- сохранять runtime-логи.

### 4.3. `telegram-adapter`

Модуль или подпакет внутри `vendor-support-agent`, который принимает webhook Telegram, нормализует входящее сообщение и передаёт его в общий движок агента.

### 4.4. `max-adapter`

Модуль или подпакет внутри `vendor-support-agent`, который принимает webhook MAX, нормализует входящее сообщение и передаёт его в общий движок агента.

### 4.5. `widget-api`

HTTP-вход для виджета. Может быть реализован как endpoint внутри `vendor-support-agent`.

### 4.6. Postgres

Основная реляционная БД для:

- документов;
- чанков;
- промтов;
- статусов;
- задач индексации;
- runtime-логов;
- сообщений;
- аудита;
- технических настроек.

### 4.7. Qdrant

Векторная база для embeddings/chunks.

Используется одна Qdrant collection для общей базы знаний.

### 4.8. Redis

Используется для очередей и фоновых задач индексации.

### 4.9. File Storage

Хранилище оригинальных документов.

На MVP достаточно Docker volume:

```text
/storage/knowledge/originals/
```

Позже можно заменить на S3/MinIO.

---

## 5. Технологический стек

Рекомендуемый стек для MVP:

- Python 3.12;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2;
- Alembic;
- PostgreSQL;
- Qdrant;
- Redis;
- Celery или RQ для фоновых задач;
- Docker Compose;
- pytest;
- httpx;
- Ruff/Black;
- OpenAPI из FastAPI;
- Markdown-документация.

LLM-провайдер должен быть абстрагирован через отдельный клиент. Нельзя жёстко зашивать конкретного поставщика в бизнес-логику агента.

---

## 6. Единая база знаний

На текущем этапе используется одна общая база знаний.

Она строится на документации приложения, которым пользуются вендоры.

Примеры документов:

- инструкция по работе с кабинетом;
- инструкция по загрузке товаров;
- настройка профиля;
- настройка уведомлений;
- работа с заказами;
- FAQ;
- типовые ошибки;
- инструкции по настройкам;
- технические регламенты;
- ограничения;
- справочная документация.

Документы загружаются через API оркестра.

После загрузки документ должен пройти индексацию:

```text
file/content upload
  -> save original
  -> extract text
  -> split into chunks
  -> create embeddings
  -> save chunks to Postgres
  -> save vectors to Qdrant
  -> update document/indexing status
```

---

## 7. Оркестр

### 7.1. Роль оркестра

Оркестр не управляет внешними вендорами и не хранит бизнес-логику заказчика.

Оркестр работает только с теми техническими данными, которые ему передали:

- документы;
- тексты;
- промты;
- настройки агентов;
- статусы;
- логи;
- индексы.

Оркестр не должен содержать Vendors API в MVP.

### 7.2. Documents API

```http
GET    /api/v1/knowledge/documents
POST   /api/v1/knowledge/documents
GET    /api/v1/knowledge/documents/{document_id}
PATCH  /api/v1/knowledge/documents/{document_id}
DELETE /api/v1/knowledge/documents/{document_id}
```

Поддерживаемые варианты загрузки:

1. `multipart/form-data` с файлом;
2. JSON с текстовым `content`.

Пример JSON-загрузки:

```json
{
  "title": "Инструкция по загрузке товаров",
  "content": "Для загрузки товара необходимо...",
  "metadata": {
    "category": "instruction",
    "source": "manual_upload"
  }
}
```

Пример ответа:

```json
{
  "status": "uploaded",
  "document_id": "doc_123",
  "indexing_status": "pending_index"
}
```

### 7.3. Indexing API

```http
POST /api/v1/knowledge/reindex
GET  /api/v1/knowledge/index/status
GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
```

Режимы индексации:

- `full` — полная переиндексация;
- `incremental` — новые/изменённые документы;
- `document` — конкретный документ.

Пример запуска:

```json
{
  "mode": "full"
}
```

Пример статуса:

```json
{
  "job_id": "job_789",
  "status": "processing",
  "progress": {
    "total_documents": 12,
    "processed_documents": 7,
    "total_chunks": 350,
    "indexed_chunks": 210
  },
  "error_message": null
}
```

### 7.4. Prompts API

```http
GET /api/v1/prompts
GET /api/v1/prompts/{prompt_key}
PUT /api/v1/prompts/{prompt_key}
GET /api/v1/prompts/{prompt_key}/versions
```

Промты должны версионироваться.

На MVP достаточно:

- `system`;
- `answer_policy`;
- `fallback`;
- `channel_style`.

### 7.5. Agents API

```http
GET /api/v1/agents
GET /api/v1/agents/{agent_id}
GET /api/v1/agents/{agent_id}/status
```

Для MVP есть один агент:

```text
vendor-support-agent
```

### 7.6. Health API

```http
GET /api/v1/health
GET /api/v1/status
GET /api/v1/infrastructure/status
```

Должны отображаться статусы:

- orchestrator-api;
- vendor-support-agent;
- Postgres;
- Redis;
- Qdrant;
- File Storage;
- indexing worker.

### 7.7. Logs API

```http
GET /api/v1/logs/runtime
GET /api/v1/logs/indexing
GET /api/v1/audit/events
```

---

## 8. Агент поддержки вендоров

### 8.1. Общий принцип

`vendor-support-agent` содержит единый движок ответа.

Все каналы используют один и тот же движок:

```text
widget -> normalize -> agent_engine
telegram -> normalize -> agent_engine
max -> normalize -> agent_engine
```

Нельзя делать отдельную бизнес-логику ответа для каждого канала.

### 8.2. Endpoint'ы агента

```http
GET  /health
GET  /metadata
POST /api/v1/invoke
POST /api/v1/widget/invoke
POST /api/v1/telegram/webhook
POST /api/v1/max/webhook
```

`POST /api/v1/invoke` — универсальный внутренний формат для вызова агента.

Пример входа:

```json
{
  "channel": "widget",
  "conversation_id": "conv_123",
  "user_id": "user_456",
  "message": "Как настроить уведомления?",
  "context": {
    "source": "vendor_dashboard"
  }
}
```

Пример ответа:

```json
{
  "status": "success",
  "answer": "Чтобы настроить уведомления, откройте раздел...",
  "sources": [
    {
      "document_id": "doc_123",
      "chunk_id": "chunk_456",
      "title": "Инструкция по уведомлениям"
    }
  ],
  "meta": {
    "confidence": 0.84,
    "needs_human": false
  }
}
```

### 8.3. Внутренний pipeline агента

```text
1. Принять сообщение.
2. Нормализовать канал.
3. Сохранить входящее сообщение.
4. Выполнить поиск по Qdrant.
5. Получить metadata чанков из Postgres.
6. Собрать prompt.
7. Вызвать LLM.
8. Сохранить ответ.
9. Вернуть ответ в канал.
```

---

## 9. Таблицы и нейминг

Все таблицы должны иметь префикс по зоне ответственности.

Использовать физические отдельные таблицы на каждого вендора нельзя.

Рекомендуемые префиксы:

```text
orch_       системные настройки оркестра
agent_      агенты и их конфиги
kb_         база знаний
idx_        индексация
prompt_     промты
runtime_    runtime-запросы и ответы
channel_    данные каналов
audit_      аудит действий
job_        фоновые задачи
```

Минимальный набор таблиц MVP:

```text
orch_settings
orch_api_keys

agent_registry
agent_status

kb_documents
kb_document_versions
kb_chunks

idx_jobs
idx_job_events

prompt_templates
prompt_versions

runtime_conversations
runtime_messages
runtime_agent_logs

channel_telegram_users
channel_telegram_messages
channel_max_users
channel_max_messages
channel_widget_sessions

audit_events
```

---

## 10. Qdrant

Используется одна collection:

```text
knowledge_chunks
```

Payload каждого вектора:

```json
{
  "chunk_id": "chunk_123",
  "document_id": "doc_456",
  "title": "Инструкция по загрузке товаров",
  "category": "instruction",
  "source_type": "knowledge_document"
}
```

Поиск выполняется по общей базе знаний.

На MVP не требуется фильтрация по vendor_id.

---

## 11. Индексация документов

Статусы документа:

```text
uploaded
pending_index
indexing
indexed
failed
deleted
```

Статусы задачи:

```text
pending
processing
completed
failed
cancelled
```

Индексация должна быть фоновой задачей.

После загрузки документа можно либо автоматически поставить задачу индексации, либо дать возможность запустить её вручную через API.

---

## 12. Docker Compose

Нужны минимум два compose-файла:

```text
infra/docker-compose.yml
infra/docker-compose.dev.yml
```

Сервисы:

```text
orchestrator-api
vendor-support-agent
indexing-worker
postgres
qdrant
redis
nginx
```

SocratiCode не должен быть частью production compose.

Для SocratiCode нужно добавить отдельную инструкцию и конфиги для Cursor/Codex.

---

## 13. SocratiCode

Проект должен быть подготовлен к индексации через SocratiCode.

Нужно добавить:

```text
.vscode/mcp.json
.cursor/rules/project-rules.mdc
AGENTS.md
docs/handover/socraticode.md
.socraticodeignore
```

Пример `.vscode/mcp.json`:

```json
{
  "servers": {
    "socraticode": {
      "command": "npx",
      "args": ["-y", "socraticode"]
    }
  }
}
```

SocratiCode используется только для разработки и передачи проекта. Он не участвует в production runtime.

---

## 14. Документация

Документация должна создаваться параллельно с разработкой.

Обязательные файлы:

```text
README.md
AGENTS.md
docs/technical-spec.md
docs/architecture.md
docs/api/orchestrator-openapi.yaml
docs/api/agent-openapi.yaml
docs/handover/setup.md
docs/handover/environment.md
docs/handover/socraticode.md
docs/handover/troubleshooting.md
```

Каждая новая возможность считается готовой только если обновлены:

- код;
- миграции;
- тесты;
- OpenAPI;
- документация;
- AGENTS.md при изменении архитектуры;
- README/setup при изменении запуска.

---

## 15. Рекомендуемая структура проекта

```text
project-root/
  apps/
    orchestrator-api/
      src/
        api/
        modules/
          knowledge/
          indexing/
          prompts/
          agents/
          logs/
          health/
        core/
        schemas/
      Dockerfile

    agents/
      vendor-support-agent/
        src/
          api/
          core/
            agent_engine.py
            rag_service.py
            prompt_builder.py
            llm_client.py
          channels/
            widget/
            telegram/
            max/
          db/
          schemas/
        prompts/
          system.md
          answer_policy.md
          fallback.md
          channel_style.md
        Dockerfile
        .env.example

  packages/
    shared-types/
    rag-core/

  infra/
    docker-compose.yml
    docker-compose.dev.yml
    nginx/
    postgres/
    qdrant/
    redis/

  docs/
    technical-spec.md
    architecture.md
    api/
      orchestrator-openapi.yaml
      agent-openapi.yaml
    handover/
      setup.md
      environment.md
      socraticode.md
      troubleshooting.md

  storage/
    knowledge/
      originals/

  .vscode/
    mcp.json

  .cursor/
    rules/
      project-rules.mdc

  README.md
  AGENTS.md
```

---

## 16. Первый MVP-сценарий

Система должна позволять выполнить полный сценарий:

```text
1. Запустить проект через Docker Compose.
2. Открыть orchestrator-api.
3. Загрузить документ в базу знаний.
4. Запустить индексацию.
5. Проверить статус индексации.
6. Отправить вопрос в vendor-support-agent через widget endpoint.
7. Агент должен найти релевантные чанки.
8. Агент должен вызвать LLM.
9. Агент должен вернуть ответ с sources.
10. Runtime-запрос и ответ должны сохраниться в логах.
```

---

## 17. Требования к качеству

- Не писать монолитную кашу.
- Разносить API, services, repositories, schemas, models.
- Использовать миграции Alembic.
- Использовать `.env.example` для каждого сервиса.
- Не хранить секреты в коде.
- Покрыть основные сервисы базовыми тестами.
- Все ответы API должны иметь понятный JSON-формат.
- Ошибки должны быть стандартизированы.
- Логи должны быть структурированными.
- Код должен быть понятен Cursor/Codex через AGENTS.md и документацию.

---

## 18. Итоговая формулировка

Система представляет собой backend-only окружение для работы агента технической поддержки вендоров.

Оркестр управляет базой знаний, документами, индексами, промтами, статусами и техническими логами.

Пользовательские сообщения не проходят через оркестр. Сообщения из виджета, Telegram и MAX поступают в агентский слой.

Все каналы используют один общий движок агента и одну общую базу знаний.
