# Перенос на сервер (быстрый старт)

← [`README.md`](README.md) · [`setup.md`](setup.md) · [`environment.md`](environment.md)

## 1. Что берётся из Git (достаточно для кода)

```bash
git clone https://github.com/ocean1nside/Orchestra-of-AI-agents.git
cd Orchestra-of-AI-agents
```

В репозитории уже есть: приложения, миграции Alembic, `infra/docker-compose.yml`, тестовые UI в `test_interfaces/` (опционально).

**Не в git** (и не должны попадать): `.env`, `storage/`, Docker volumes, секреты.

## 2. Что перенести физически (файлами)

| Что | Куда на сервере | Обязательно? |
|-----|-----------------|--------------|
| **Три `.env`** | см. ниже | **Да** — без них сервисы не стартуют с вашими ключами |
| **`storage/knowledge/`** | `storage/knowledge/` в корне клона | Нет, если заново загрузите документы через API. **Да**, если нужны уже загруженные DOCX/MD без повторной загрузки |
| Бэкап Postgres / Qdrant | volumes Docker или дамп | Нет для «чистого» стенда. **Да**, если переносите историю чатов и индекс как есть |

### Три файла `.env` (создать на сервере, не коммитить)

```bash
cp env.example .env
cp apps/orchestrator-api/.env.example apps/orchestrator-api/.env
cp apps/agents/vendor-support-agent/.env.example apps/agents/vendor-support-agent/.env
```

Заполнить по [`environment.md`](environment.md). Минимум на сервере:

**Корень `.env`:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (сильный пароль).

**`apps/orchestrator-api/.env`:** `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `STORAGE_PATH=/storage/knowledge`, `API_KEY_DEV`, `ORCHESTRATOR_REQUIRE_API_KEY=true` (рекомендуется), `EMBED_PROVIDER` + `OPENAI_API_KEY` при `openai`, `VENDOR_SUPPORT_AGENT_BASE_URL=http://vendor-support-agent:8010`.

**`apps/agents/vendor-support-agent/.env`:** `DATABASE_URL`, `QDRANT_URL`, `LLM_API_KEY`, `LLM_MODEL`, `WIDGET_API_KEY`, `OPERATOR_API_KEY`, токены Telegram/MAX при использовании каналов, `ESCALATION_*` при необходимости.

Проще всего: скопировать с рабочей машины **три `.env` по SCP/SFTP** в те же пути (проверить, что `DATABASE_URL` и хосты — `postgres`, `qdrant`, `redis`, а не `127.0.0.1`).

### `storage/knowledge/` (опционально)

С локальной машины:

```bash
rsync -avz ./storage/knowledge/ user@server:/path/to/Orchestra-of-AI-agents/storage/knowledge/
```

После копировании файлов на сервере всё равно нужен **reindex** (или перенос БД+Qdrant), иначе метаданные в Postgres/Qdrant не совпадут с файлами.

## 3. Запуск на сервере (штатный режим, only-backend)

Из **корня** репозитория:

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Проверки:

```bash
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8010/health
```

С ключом оркестратора:

```bash
curl -s -H "X-Api-Key: YOUR_API_KEY_DEV" http://localhost:8000/api/v1/infrastructure/status
```

Миграции применяются при старте `orchestrator-api`. `indexing-worker` миграции не гоняет (только RQ).

## 4. После старта (обязательно для «всё работает»)

1. **Документы:** `POST /api/v1/knowledge/documents` → `POST /api/v1/knowledge/reindex` → дождаться `completed` job.
2. **Агент:** `POST /api/v1/widget/invoke` с `WIDGET_API_KEY` — ответ с непустыми `sources`.
3. **Telegram/MAX:** HTTPS URL сервера, `setWebhook` на `https://<host>/api/v1/telegram/webhook` и `/api/v1/max/webhook` (см. `telegram.md`, `max.md`).
4. **Фаервол:** открыть только нужные порты (80/443 через reverse proxy; 8000/8010 — не в интернет без nginx и TLS).

## 5. Тестовые UI на сервере (не prod, по желанию)

Только для отладки, с профилем `devtools`:

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build test-ui-studio
```

Порт **8790** (Agent Support Studio). В проде лучше не публиковать наружу.

## 6. Что не переносить

- `node_modules`, `.venv`, `__pycache__`
- `.env.local` из `test_interfaces/` (не нужны в Docker — ключи из `.env` агента)
- Содержимое `postgres_data` / `qdrant_data` volumes с другой машины без понимания версий схемы

## 7. Reverse proxy (рекомендуется)

Перед контейнерами: nginx/Caddy с TLS, маршруты например:

- `https://api.example.com` → `orchestrator-api:8000`
- `https://agent.example.com` → `vendor-support-agent:8010`

Вебхуки Telegram/MAX должны указывать на публичный URL агента.
