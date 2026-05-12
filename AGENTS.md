# Agents & Orchestrator overview

## Что здесь считается агентом

**Агент** — это runtime-сервис, который принимает сообщения из каналов (виджет/Telegram/MAX), выполняет RAG-поиск по базе знаний и вызывает LLM.

Важно:

- Агент **не запрашивает** знания у `orchestrator-api` по HTTP.
- Агент **напрямую** использует Postgres (метаданные/чанки/логи) и Qdrant (вектора).

## Оркестр (management/control plane)

`orchestrator-api` отвечает только за управление:

- документы и их статусы;
- индексация и job-статусы;
- промты и их версии;
- статусы агентов;
- технические логи и аудит;
- health/status endpoints.

Оркестр **не** является runtime-прокси для пользовательских вопросов.

## Текущие агенты

### `vendor-support-agent`

- **Назначение**: отвечать на вопросы по документации приложения/кабинета вендора.
- **Единый движок**: все каналы вызывают общий `AgentEngine`.
- **Каналы**: widget, Telegram webhook, MAX webhook.
- **Модель LLM**: задаётся в `apps/agents/vendor-support-agent/.env` переменной **`LLM_MODEL`** (и **`LLM_API_KEY`**); у каждого будущего агента — свой `.env` в своей папке. См. `docs/handover/environment.md` и `.env.example` агента.

## Где читать детали

- **Карта всей документации:** `docs/README.md`
- Спека: `docs/technical-spec.md`
- Архитектура: `docs/architecture.md`
- Все HTTP-эндпоинты: `docs/http-api-reference.md`
- OpenAPI (YAML + живой `/openapi.json`): `docs/api/README.md`
- Запуск и каналы: `docs/handover/README.md`

