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
- `docs/api/` — OpenAPI спек-файлы
- `docs/handover/` — инструкции по запуску/окружению/отладке

