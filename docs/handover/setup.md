# Setup (MVP)

Индекс папки `handover/`: [`README.md`](README.md). Карта всего `docs/`: [`../README.md`](../README.md).

## Prerequisites

- Docker + Docker Compose
- Git

## Запуск

- **Локально с отладкой / SocratiCode-профилем:** `infra/docker-compose.dev.yml` (см. корневой `README.md`).
- **Стенд или сервер без лишних сервисов:** `infra/docker-compose.yml` — те же слои `.env`, порты **8000** (оркестратор) и **8010** (агент) на хосте, без профиля `devtools`.

Команда из **корня репозитория** (важно для путей `../.env`):

**Dev** (порты наружу + тестовые UI 8788–8790 и SocratiCode):

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build
```

**Стенд / сервер** (без тестовых UI):

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Тестовые интерфейсы: [`../../test_interfaces/agent_support_gleb/README.md`](../../test_interfaces/agent_support_gleb/README.md).

## Переменные окружения

- Корень: `env.example` → `.env` (минимум `POSTGRES_*`).
- Оркестратор и worker: `apps/orchestrator-api/.env.example` → `apps/orchestrator-api/.env`.
- Агент: `apps/agents/vendor-support-agent/.env.example` → `apps/agents/vendor-support-agent/.env`.

Слои в compose: см. `docs/handover/environment.md`. Сервисы подключают `../.env` и при необходимости профильный `.env` (путь относительно `infra/`).

HTTP API обоих сервисов: **[`../http-api-reference.md`](../http-api-reference.md)**.

После изменений схемы БД (новые alembic-миграции) обязательно **пересоберите образы** контейнеров оркестра:

```bash
docker compose -f infra/docker-compose.yml build orchestrator-api indexing-worker
docker compose -f infra/docker-compose.yml up -d orchestrator-api indexing-worker
```

### Автоматические миграции Alembic

Образ `orchestrator-api` запускает `alembic upgrade head` перед стартом API (ENTRYPOINT контейнера).

Если вдруг понадобилось выполнить вручную:

```bash
docker compose -f infra/docker-compose.yml exec orchestrator-api alembic upgrade head
```

