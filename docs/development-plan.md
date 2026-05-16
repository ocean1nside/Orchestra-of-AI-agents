# План разработки (от текущей точки)

Карта документации: [`README.md`](README.md).

Цель MVP: сценарий из ТЗ — compose → health → загрузка документа → reindex → вопрос в агент → ответ с `sources` + логи в Postgres.

## Сделано (состояние на сейчас)

- Docker Compose (dev/prod-like): корневой `env.example` (только `POSTGRES_*`) + `apps/orchestrator-api/.env` и `apps/agents/vendor-support-agent/.env` по примерам.
- `orchestrator-api`: документы, jobs/reindex, пайплайн индексации (текст → чанки → Postgres + Qdrant), промпты (таблицы + API), заглушки audit/indexing logs + runtime logs list, agents list, health с реальными проверками Postgres/Redis/Qdrant/агента/хранилища.
- `vendor-support-agent`: RAG (Qdrant + Postgres), LLM при `LLM_API_KEY`, запись `runtime_*`, ответ с `sources`; три входа: **виджет** (`/widget/invoke`, опционально `WIDGET_API_KEY`), **Telegram** (реальный `Update` + `sendMessage`), **MAX** (реальный `Update` + `platform-api.max.ru/messages`); **operator API** (`/api/v1/operator/...`, список чатов и ответ оператора). Все HTTP-методы: **[`http-api-reference.md`](http-api-reference.md)**.
- Защита оркестратора: **`ORCHESTRATOR_REQUIRE_API_KEY`** + **`API_KEY_DEV`** (заголовки `X-Api-Key` / `Bearer`); smoke: **`scripts/smoke_stack.py`**; **infrastructure/status** учитывает **RQ workers** для `indexing_worker`.
- `indexing-worker` (RQ) в compose.
- SocratiCode: индекс проекта в Cursor через MCP; контейнер `socraticode` в dev — вспомогательный.
- **Тестовые UI** в `test_interfaces/agent_support_gleb/` (chats / widjet / console): в dev-compose, профиль `devtools`, порты 8788–8790 — только для проверки backend, не prod.

## Ближайшие шаги (приоритет)

1. **Индексация**: PDF/DOCX как planned extractors; `idx_job_events` в UI/фильтрах; прогресс job по документам/чанкам точнее.
2. **Промпты**: синхронизация файлов `apps/agents/vendor-support-agent/prompts/*.md` ↔ версии в БД (опционально job).
3. **Агент**: расширение каналов (вложения, callback), лимиты и ретраи исходящих API.
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
