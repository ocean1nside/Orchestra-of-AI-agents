# Cursor Prompt: создать backend-окружение для агента поддержки вендоров

## Роль

Ты работаешь как senior backend engineer / architect.

Твоя задача — создать backend-only проект по ТЗ из `docs/technical-spec.md`.

Проект нужен для запуска ИИ-агента технической поддержки вендоров. Агент отвечает на вопросы по документации приложения, которым пользуются вендоры.
Пиши систему так, чтобы в нее можно было удобно и гибко в будущем добавлять новых агентов. Агенты будут разрабатываться и вставляться в оркестр в папку агентов.

Система должна быть гибкая под реализацию новых агентов с разными задачами.

Сначала внимательно прочитай:

```text
docs/technical-spec.md
AGENTS.md
README.md
```

Если файлов пока нет — создай их согласно этому промту и поддерживай в актуальном состоянии.

---

## Ключевые архитектурные правила

### 1. Не делать интерфейс

Не создавай frontend, админку, React-приложение, HTML-страницы, UI-компоненты или моковые панели.

Проект backend-only.

Внешний интерфейс будет делать другая система поверх API.

Разрешены только:

- backend API;
- OpenAPI;
- документация;
- Docker;
- миграции;
- тесты;
- технические health/status endpoint'ы.

---

### 2. Оркестр не является runtime-прокси

Пользовательские вопросы не должны идти через оркестр.

Нельзя строить схему:

```text
user -> orchestrator -> agent
```

Правильная схема:

```text
widget/telegram/max -> vendor-support-agent -> Postgres/Qdrant -> LLM
```

Оркестр нужен только для управления:

- документами;
- знаниями;
- чанками;
- индексами;
- промтами;
- статусами;
- логами;
- health/status;
- техническими настройками.

---

### 3. Не делать Vendors API

На текущем этапе не создавать:

- Vendors API;
- vendor management;
- vendor profiles;
- vendor roles;
- vendor permissions;
- отдельные базы знаний на каждого вендора;
- отдельные таблицы на каждого вендора.

Сейчас используется одна общая база знаний по документации приложения.

---

### 4. Агент имеет прямой доступ к БД и Qdrant

Агент не должен ходить в оркестр за знаниями через HTTP.

Агентский runtime pipeline должен работать так:

```text
incoming message
  -> normalize channel
  -> search Qdrant
  -> load chunk metadata/content from Postgres
  -> build prompt
  -> call LLM
  -> save runtime log
  -> return response
```

---

### 5. Одни мозги для всех каналов

Виджет, Telegram и MAX должны использовать один общий движок:

```text
vendor_support_agent.core.agent_engine
```

Не дублируй логику ответа по каналам.

Каналы должны только:

- принять входящее сообщение;
- привести его к общему формату;
- вызвать общий `AgentEngine`;
- вернуть ответ в нужном формате.

---

## Технологический стек

Используй:

- Python 3.12;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2;
- Alembic;
- PostgreSQL;
- Qdrant;
- Redis;
- Celery или RQ для фоновой индексации;
- Docker Compose;
- pytest;
- httpx;
- Ruff/Black.

Если выбираешь Celery или RQ — зафиксируй выбор в `docs/architecture.md`.

LLM-клиент должен быть абстракцией. Нельзя жёстко завязывать бизнес-логику на одного провайдера.

---

## Структура проекта

Создай структуру:

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

Если технически удобнее немного изменить структуру — можно, но сначала убедись, что смысл ТЗ сохранён.

---

## Сервисы Docker Compose

Создай Docker Compose для MVP:

```text
orchestrator-api
vendor-support-agent
indexing-worker
postgres
qdrant
redis
nginx
```

Файлы:

```text
infra/docker-compose.yml
infra/docker-compose.dev.yml
```

Production compose не должен запускать SocratiCode.

SocratiCode — только dev/handover инструмент.

---

## База данных

Используй PostgreSQL.

Настрой Alembic.

Таблицы должны иметь префиксы по зоне ответственности.

Минимальный набор таблиц:

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

Не создавай физические таблицы под каждого вендора.

Не создавай `vendor_*` таблицы на этом этапе.

---

## Qdrant

Создай одну collection:

```text
knowledge_chunks
```

Payload векторов должен включать:

```json
{
  "chunk_id": "chunk_123",
  "document_id": "doc_456",
  "title": "Инструкция",
  "category": "instruction",
  "source_type": "knowledge_document"
}
```

---

## Orchestrator API

Реализуй management API.

### Documents API

```http
GET    /api/v1/knowledge/documents
POST   /api/v1/knowledge/documents
GET    /api/v1/knowledge/documents/{document_id}
PATCH  /api/v1/knowledge/documents/{document_id}
DELETE /api/v1/knowledge/documents/{document_id}
```

`POST /api/v1/knowledge/documents` должен принимать:

1. `multipart/form-data` файл;
2. JSON с `title`, `content`, `metadata`.

После загрузки документ должен получить статус:

```text
uploaded
```

Или сразу:

```text
pending_index
```

если автоматически ставится задача индексации.

### Indexing API

```http
POST /api/v1/knowledge/reindex
GET  /api/v1/knowledge/index/status
GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
```

Режимы:

```text
full
incremental
document
```

### Prompts API

```http
GET /api/v1/prompts
GET /api/v1/prompts/{prompt_key}
PUT /api/v1/prompts/{prompt_key}
GET /api/v1/prompts/{prompt_key}/versions
```

Создай стартовые промты:

```text
system
answer_policy
fallback
channel_style
```

### Agents API

```http
GET /api/v1/agents
GET /api/v1/agents/{agent_id}
GET /api/v1/agents/{agent_id}/status
```

Добавь стартовую запись/конфиг для:

```text
vendor-support-agent
```

### Health API

```http
GET /api/v1/health
GET /api/v1/status
GET /api/v1/infrastructure/status
```

### Logs API

```http
GET /api/v1/logs/runtime
GET /api/v1/logs/indexing
GET /api/v1/audit/events
```

---

## Vendor Support Agent API

Реализуй:

```http
GET  /health
GET  /metadata
POST /api/v1/invoke
POST /api/v1/widget/invoke
POST /api/v1/telegram/webhook
POST /api/v1/max/webhook
```

### Общий формат входа

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

### Ответ

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

---

## AgentEngine

Создай единый класс/сервис:

```text
AgentEngine
```

Он должен выполнять:

```text
1. validate input
2. save incoming message
3. search relevant chunks
4. build prompt
5. call LLM
6. save answer
7. return normalized response
```

Каналы не должны содержать RAG/LLM-логику.

---

## Индексация

Создай indexing pipeline:

```text
document upload
  -> original file storage
  -> text extraction
  -> chunking
  -> embeddings
  -> Postgres chunks
  -> Qdrant vectors
  -> document status update
```

Статусы документа:

```text
uploaded
pending_index
indexing
indexed
failed
deleted
```

Статусы job:

```text
pending
processing
completed
failed
cancelled
```

На первом этапе можно сделать простые extractors для:

```text
.md
.txt
```

PDF/DOCX можно заложить интерфейсом и пометить как planned, если не успеешь безопасно реализовать.

---

## Промты

Промты должны лежать в:

```text
apps/agents/vendor-support-agent/prompts/
```

И также управляться через `prompt_templates` / `prompt_versions`.

Стартовые файлы:

```text
system.md
answer_policy.md
fallback.md
channel_style.md
```

Требования к поведению агента:

- отвечать только по базе знаний, если вопрос связан с документацией;
- если данных не хватает — честно говорить, что информации нет;
- не выдумывать инструкции;
- прикладывать источники, если ответ основан на чанках;
- если вопрос не относится к системе — мягко вернуть пользователя к теме поддержки;
- при низкой уверенности ставить `needs_human: true`.

---

## SocratiCode

Подготовь проект для SocratiCode.

Добавь:

```text
.vscode/mcp.json
.cursor/rules/project-rules.mdc
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

В `docs/handover/socraticode.md` опиши:

- что нужен Docker;
- что SocratiCode используется только для разработки;
- как подключить MCP в Cursor;
- как попросить Cursor проиндексировать проект;
- что SocratiCode не входит в production compose.

---

## Документация

Поддерживай документацию с первого коммита.

Создай/обнови:

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

Каждый созданный API должен быть описан.

Каждая переменная окружения должна быть описана.

---

## .env

Для каждого сервиса создать `.env.example`.

Минимально:

### orchestrator-api

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
STORAGE_PATH=/storage/knowledge
API_KEY_DEV=change-me
```

### vendor-support-agent

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator
QDRANT_URL=http://qdrant:6333
LLM_PROVIDER=openai
LLM_API_KEY=
LLM_MODEL=
TELEGRAM_BOT_TOKEN=
MAX_BOT_TOKEN=
```

Не хранить реальные ключи в репозитории.

---

## Тесты

Добавь базовые тесты:

- health endpoints;
- document upload schema;
- indexing job creation;
- prompt retrieval;
- agent invoke schema;
- RAG service mock test;
- LLM client mock test.

---

## Критерии готовности MVP

MVP считается готовым, если можно выполнить сценарий:

```text
1. Запустить docker compose.
2. Открыть orchestrator-api health.
3. Загрузить .md или .txt документ через orchestrator-api.
4. Запустить индексацию.
5. Проверить статус индексации.
6. Отправить вопрос в vendor-support-agent через /api/v1/widget/invoke.
7. Агент найдёт релевантные чанки.
8. Агент соберёт промт.
9. Агент вызовет LLM или mock LLM в dev-режиме.
10. Агент вернёт ответ с sources.
11. Runtime log сохранится в Postgres.
12. Документация и OpenAPI будут актуальны.
```

---

## Важные запреты

Не делай:

- frontend;
- vendor management;
- user management;
- CRM;
- e-commerce entities;
- товары/заказы;
- отдельные базы знаний на каждого вендора;
- отдельные таблицы на каждого вендора;
- runtime-маршрутизацию через оркестр;
- сложный Kubernetes;
- неиспользуемые demo-файлы;
- декоративные моковые страницы.

---

## Работай итерационно

Сначала сделай каркас проекта и Docker.

Потом БД и миграции.

Потом orchestrator-api.

Потом индексацию.

Потом vendor-support-agent.

Потом каналы.

Потом документацию и тесты.

Не пытайся реализовать всё хаотично в одном файле.
