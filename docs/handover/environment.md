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

# Индексация: эмбеддинги
# hash — детерминированные локальные векторы (dev, без внешних вызовов)
# openai — OpenAI Embeddings API (нужен OPENAI_API_KEY)
EMBED_PROVIDER=hash
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DIMENSIONS=384
```

## vendor-support-agent

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

