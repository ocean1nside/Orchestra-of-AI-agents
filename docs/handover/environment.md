# Environment

Индекс `handover/`: [`README.md`](README.md). Карта `docs/`: [`../README.md`](../README.md).

## Слои `.env` (Docker Compose)

В `infra/docker-compose.dev.yml` и **`infra/docker-compose.yml`** задано одинаково по смыслу:

| Сервис | Файлы окружения (по порядку) |
|--------|------------------------------|
| **postgres** | только корневой `../.env` (нужны `POSTGRES_*`) |
| **orchestrator-api**, **indexing-worker** | корневой `../.env` (обязателен), затем опционально `apps/orchestrator-api/.env` |
| **vendor-support-agent** | корневой `../.env`, затем опционально `apps/agents/vendor-support-agent/.env` |

Поздний файл **переопределяет** переменные раннего.

- В корне репозитория держите минимум **`POSTGRES_*`** (см. `env.example`).
- Оркестратор и worker: `apps/orchestrator-api/.env` по образцу `apps/orchestrator-api/.env.example`.
- Агент: `apps/agents/vendor-support-agent/.env` по образцу `apps/agents/vendor-support-agent/.env.example`.

## orchestrator-api

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=knowledge_chunks
STORAGE_PATH=/storage/knowledge
API_KEY_DEV=change-me
# ORCHESTRATOR_REQUIRE_API_KEY=true — тогда для API кроме health/status/infrastructure/openapi нужен X-Api-Key или Bearer с тем же значением, что API_KEY_DEV (не используйте change-me в проде).
ORCHESTRATOR_REQUIRE_API_KEY=false

# Индексация: эмбеддинги
# hash — детерминированные локальные векторы (dev, без внешних вызовов)
# openai — OpenAI Embeddings API (нужен OPENAI_API_KEY)
EMBED_PROVIDER=hash
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DIMENSIONS=384

VENDOR_SUPPORT_AGENT_BASE_URL=http://vendor-support-agent:8010
```

## vendor-support-agent

Полный список — `apps/agents/vendor-support-agent/.env.example`. HTTP-эндпоинты и ключи — **[`../http-api-reference.md`](../http-api-reference.md)**. Важно:

- **`WIDGET_API_KEY`** — если задан, обязателен для `POST /api/v1/widget/invoke` и `POST /api/v1/invoke` (заголовки см. `docs/handover/telegram.md`).
- **`TELEGRAM_WEBHOOK_SECRET`** — опционально, должен совпадать с `secret_token` в `setWebhook`.
- **`ESCALATION_TELEGRAM_CHAT_ID`** — ID супергруппы (`-100…`), куда бот шлёт эскалации со всех каналов; бот должен быть в группе **администратором**. Пусто — эскалация отключена. Опционально **`ESCALATION_CONTEXT_BASE_URL`** — заглушка ссылки «открыть контекст» для widget/max (к query добавляются `channel`, `conversation_id`, `user_id`).
- **`EMBED_PROVIDER`**: для осмысленного поиска в Qdrant в проде лучше **`openai`** и переиндексация с тем же провайдером; в dev при **`hash`** агент использует лексический поиск по `kb_chunks` (см. код `rag_service.py`).
- **`OPENAI_API_KEY`** + **`KNOWLEDGE_NORMALIZE_MODEL`**: кнопка Studio «Подготовить через ИИ → Markdown» (`POST /api/v1/knowledge/normalize-file`).
- **`OPENAI_API_KEY`** + **`PROMPT_TUNE_MODEL`**: вкладка Studio «Промпты → Тюнинг» (`POST /api/v1/prompts/tune`, `…/tune/apply`). Журнал правок — блок `tuning_log` (не попадает в ответы пользователю).
- **`ESCALATION_CONTEXT_BASE_URL`**: хост Studio (напр. `https://212-67-10-140.sslip.io`) — в Telegram-группу эскалации уходит ссылка `…/studio/?view=chats&conversation_id=<id из runtime_conversations>`.
- **`USER_MEMORY_ENABLED`** / **`USER_MEMORY_USE_LLM`**: из сообщений пользователя извлекаются факты (имя, телефон, email, адрес, компания…) в `runtime_user_facts` и подмешиваются в промпт. В Studio: блок «Память о пользователе» в карточке диалога.
- **`LLM_MODEL`**: модель для ответов пользователю (OpenAI Chat Completions). Настраивается **в `.env` конкретного агента** (`apps/agents/<имя-агента>/.env`); у каждого будущего агента — свой файл и свои значения. Пустое значение в коде трактуется как `gpt-4o-mini`. Типичные значения: `gpt-4o-mini`, `gpt-4.1-mini` (или снапшот с датой из документации OpenAI).

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=knowledge_chunks
EMBED_PROVIDER=hash
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DIMENSIONS=384
LLM_PROVIDER=openai
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
TELEGRAM_BOT_TOKEN=
MAX_BOT_TOKEN=
WIDGET_API_KEY=
```
