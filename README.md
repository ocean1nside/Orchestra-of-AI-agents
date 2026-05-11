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
storage/
```

## Документация

- `docs/technical-spec.md` — актуальная консолидированная спека (на основе файлов в корне)
- `docs/architecture.md` — архитектурные решения и принятые компромиссы
- `docs/development-plan.md` — план работ от текущей точки + регламент индекса SocratiCode
- `docs/api/` — OpenAPI спек-файлы
- `docs/handover/` — инструкции по запуску/окружению/отладке

## Быстрый старт (локально)

1. Скопируйте `env.example` → `.env` в корне репозитория (файл `.env` не коммитится):

```bash
copy env.example .env
```

2. Запускайте compose **из корня репозитория** (важно для `${POSTGRES_*}` и `../.env` в compose-файлах):

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build
```

3. Проверки:

- `http://localhost:8000/api/v1/health`
- `http://localhost:8000/api/v1/infrastructure/status`
- `http://localhost:8010/health`

4. Индекс кода в Cursor: см. `docs/handover/socraticode.md` и `scripts/refresh-project-index.ps1`.

5. Каналы агента: `docs/handover/channel-entrypoints.md`; Telegram — `docs/handover/telegram.md`; MAX — `docs/handover/max.md`.

6. **Стенд / тесты как на проде**: в `.env` выставьте `ORCHESTRATOR_REQUIRE_API_KEY=true` и сильный `API_KEY_DEV`; для агента задайте `WIDGET_API_KEY` и передавайте его в `widget/invoke`. После `docker compose up` запустите `python scripts/smoke_stack.py --api-key <ваш ключ>`.

7. **Smoke без pytest**: из корня репозитория при запущенных контейнерах — `python scripts/smoke_stack.py` (при необходимости `--orchestrator`, `--agent`, `--api-key`).

