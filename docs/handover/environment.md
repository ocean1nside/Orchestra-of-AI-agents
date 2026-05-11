# Environment

Этот документ описывает переменные окружения сервисов. Будет расширяться по мере реализации.

## orchestrator-api

Ожидаемые переменные (пример из спеки):

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
```

## vendor-support-agent

Актуальный список — в корневом `env.example`. Важно:

- **`WIDGET_API_KEY`** — если задан, обязателен для `POST /api/v1/widget/invoke` и `POST /api/v1/invoke` (заголовки см. `docs/handover/telegram.md`).
- **`TELEGRAM_WEBHOOK_SECRET`** — опционально, должен совпадать с `secret_token` в `setWebhook`.

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

