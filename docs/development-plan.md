# План разработки (от текущей точки)

Цель MVP: сценарий из ТЗ — compose → health → загрузка документа → reindex → вопрос в агент → ответ с `sources` + логи в Postgres.

## Сделано (состояние на сейчас)

- Docker Compose (dev/prod-like), единый корневой `env.example` + локальный `.env` для сервисов.
- `orchestrator-api`: документы, jobs/reindex, пайплайн индексации (текст → чанки → Postgres + Qdrant), промпты (таблицы + API), заглушки audit/indexing logs + runtime logs list, agents list, health с реальными проверками Postgres/Redis/Qdrant/агента/хранилища.
- `vendor-support-agent`: RAG (Qdrant + Postgres), mock LLM без ключа, запись `runtime_*`, ответ с `sources`.
- `indexing-worker` (RQ) в compose.
- SocratiCode: индекс проекта в Cursor через MCP; контейнер `socraticode` в dev — вспомогательный.

## Ближайшие шаги (приоритет)

1. **Индексация**: PDF/DOCX как planned extractors; `idx_job_events` в UI/фильтрах; прогресс job по документам/чанкам точнее.
2. **Промпты**: синхронизация файлов `apps/agents/vendor-support-agent/prompts/*.md` ↔ версии в БД (опционально job).
3. **Агент**: Telegram/MAX нормализация webhook payload (сейчас общий JSON); реальные ответы LLM при `LLM_API_KEY`.
4. **Оркестр**: `audit_events`, полноценный `GET /logs/indexing`; статусы агентов из health/heartbeat.
5. **Тесты**: pytest e2e (compose profile), моки Qdrant/OpenAI.
6. **Nginx** (по ТЗ) как единая точка входа для dev.

## Поддержка индекса SocratiCode (чтобы всегда было быстро «что угодно найти»)

Индекс живёт в **MCP SocratiCode** (Cursor), не в Postgres.

Рекомендуемый регламент:

- После `git pull` и крупных рефакторингов: в Cursor вызвать **`codebase_update`** или **`codebase_index`** для `c:\1CP\orkester_gleba`, затем **`codebase_watch` → start** (если не активен).
- В репозитории есть скрипт `scripts/refresh-project-index.ps1` — он печатает чеклист (MCP нельзя вызвать из PowerShell напрямую).

## Контроль готовности

- `GET /api/v1/infrastructure/status` — все ключевые сервисы `ok`.
- `POST /api/v1/knowledge/documents` → `POST /api/v1/knowledge/reindex` → `GET /api/v1/jobs/{id}` → `completed`.
- `POST http://localhost:8010/api/v1/widget/invoke` — `sources` не пустые после индексации.
