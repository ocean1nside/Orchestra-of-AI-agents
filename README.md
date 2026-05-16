# Orkester Gleba — Vendor Support Orchestrator (backend-only)

Этот репозиторий содержит **backend-only** окружение для:

- **`orchestrator-api`** — management/control API для документов, индексации, промтов, статусов, логов и health;
- **`vendor-support-agent`** — агент поддержки вендоров (runtime), который **напрямую** работает с Postgres и Qdrant.

## Ключевые принципы (важно)

- **Оркестр не является runtime-прокси**: пользовательские сообщения не идут через `orchestrator-api`.
- **Одна общая база знаний**: без мультивендорности на этом этапе.
- **Агент имеет прямой доступ к Postgres и Qdrant** (не через HTTP-оркестр).

Спецификации:

- `cursor_prompt_vendor_support_orchestrator.md`
- `technical_spec_vendor_support_orchestrator.md`

## Структура (MVP)

```text
apps/
  orchestrator-api/
  agents/
    vendor-support-agent/
infra/
docs/
  README.md              ← карта всей документации
  http-api-reference.md
  technical-spec.md
  architecture.md
  development-plan.md
  api/                   ← OpenAPI YAML + README
  handover/              ← старт, .env, каналы (см. handover/README.md)
storage/
```

## Документация

**С чего начать:** [`docs/README.md`](docs/README.md) — оглавление по «полкам» (спека, архитектура, API, handover) и таблица «задача → файл».

Ключевые файлы:

- [`docs/http-api-reference.md`](docs/http-api-reference.md) — все HTTP API (оркестратор + агент), аутентификация, примеры `curl`
- [`docs/technical-spec.md`](docs/technical-spec.md) — консолидированная спека MVP
- [`docs/architecture.md`](docs/architecture.md) — сервисы и границы control/runtime
- [`docs/development-plan.md`](docs/development-plan.md) — план работ, SocratiCode
- [`docs/handover/README.md`](docs/handover/README.md) — индекс запуска и каналов
- [`docs/api/README.md`](docs/api/README.md) — YAML-спеки и живой `/openapi.json`

## Быстрый старт (локально)

1. Переменные окружения (файлы `.env` не коммитятся). В корне — только Postgres; приложения — в `apps/...`:

```bash
copy env.example .env
copy apps\orchestrator-api\.env.example apps\orchestrator-api\.env
copy apps\agents\vendor-support-agent\.env.example apps\agents\vendor-support-agent\.env
```

Заполните секреты и URL в двух последних файлах по комментариям внутри. Подробнее: `docs/handover/environment.md`. **Перенос на сервер:** `docs/handover/server-deploy.md`.

2. Запускайте compose **из корня репозитория** (важно для `${POSTGRES_*}` и `../.env` в compose-файлах):

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build
```

С профилем **`devtools`** дополнительно поднимаются тестовые UI (`test_interfaces/agent_support_gleb/`): **8788** (чаты оператора), **8789** (виджет), **8790** (консоль + оркестратор). Ключи берутся из `apps/agents/vendor-support-agent/.env` (и оркестратора для console).

**Вариант ближе к серверу** (без профиля devtools, порты **8000** и **8010** на хосте):

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

3. Проверки:

- `http://localhost:8000/api/v1/health`
- `http://localhost:8000/api/v1/infrastructure/status`
- `http://localhost:8010/health`

4. Индекс кода в Cursor: см. `docs/handover/socraticode.md` и `scripts/refresh-project-index.ps1`.

5. Каналы агента: `docs/handover/channel-entrypoints.md`; Telegram — `docs/handover/telegram.md`; MAX — `docs/handover/max.md`.

6. **Стенд / тесты как на проде**: в `apps/orchestrator-api/.env` выставьте `ORCHESTRATOR_REQUIRE_API_KEY=true` и сильный `API_KEY_DEV`; в `apps/agents/vendor-support-agent/.env` задайте `WIDGET_API_KEY` и передавайте его в `widget/invoke`. После `docker compose up` запустите `python scripts/smoke_stack.py --api-key <ваш ключ>`.

7. **Smoke без pytest**: из корня репозитория при запущенных контейнерах — `python scripts/smoke_stack.py` (при необходимости `--orchestrator`, `--agent`, `--api-key`).

## Как понять, что «деплой» (docker compose) завершён

Имеется в виду: образы собраны, контейнеры пересозданы и сервисы реально отвечают.

1. **Команда завершилась без ошибки** — `docker compose ... up -d --build` в конце пишет `Started` / `Running`, код выхода **0** (в PowerShell: `$LASTEXITCODE -eq 0`).
2. **Состояние контейнеров** — из корня репозитория:  
   `docker compose -f infra/docker-compose.dev.yml ps`  
   У нужных сервисов колонка **State** — `running` (не `restarting`).
3. **Health** — открываются URL из п.3 быстрого старта или снова:  
   `python scripts/smoke_stack.py` (с `--api-key`, если включён ключ оркестратора).  
   Для оркестратора смотрите строку **`overall=`** в выводе: `ok` лучше, чем `degraded` (часто воркер/Redis до первой задачи).
4. **Логи без падений** при старте, например:  
   `docker compose -f infra/docker-compose.dev.yml logs --tail 30 vendor-support-agent`  
   Нет повторяющегося traceback при каждом запросе.

**Когда имеет смысл пересобирать агента** (`--build vendor-support-agent` или полный `up --build`): изменились код Python, `Dockerfile`, зависимости или файлы в **`apps/agents/vendor-support-agent/prompts/`** (они копируются в образ). После успешного `up --build` снова проверьте п.2–3. Пересобирать только из привычки не нужно: если меняли только `.env` в корне — достаточно **`docker compose ... up -d`** без `--build` (контейнер подхватит env при пересоздании).

