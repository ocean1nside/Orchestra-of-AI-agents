# Setup (MVP)

## Prerequisites

- Docker + Docker Compose
- Git

## Запуск (будет дополнено по мере реализации)

MVP будет запускаться через:

- `infra/docker-compose.dev.yml` (dev)
- `infra/docker-compose.yml` (prod-like, без SocratiCode)

## Переменные окружения

Используйте корневой файл:

- `env.example` (в репозитории)
- `.env` (локально, **не коммитится**): `copy env.example .env`

Сервисы `docker-compose` подключают `../.env` (путь относительно `infra/`).

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

