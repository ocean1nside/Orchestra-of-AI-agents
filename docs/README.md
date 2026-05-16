# Документация репозитория

Здесь лежит **вся** продуктовая и техническая документация по Orkester Gleba (оркестратор + агент поддержки). Корень репозитория: отдельные большие промпты/ТЗ (`cursor_prompt_…`, `technical_spec_…`) — исторические входы; **актуальная** сводка — в `docs/technical-spec.md`.

---

## С чего начать

| Задача | Документ |
|--------|----------|
| Понять границы MVP и требования | [`technical-spec.md`](technical-spec.md) |
| Понять сервисы и кто за что отвечает | [`architecture.md`](architecture.md) |
| Поднять окружение и `.env` | [`handover/setup.md`](handover/setup.md) → [`handover/environment.md`](handover/environment.md) |
| Все HTTP-запросы (оркестратор + агент) | [`http-api-reference.md`](http-api-reference.md) |
| Каналы агента (виджет / Telegram / MAX) | [`handover/channel-entrypoints.md`](handover/channel-entrypoints.md) |
| План работ и индекс SocratiCode | [`development-plan.md`](development-plan.md) |

---

## Полки (структура `docs/`)

### 1. Продукт и требования

| Файл | Содержание |
|------|------------|
| [`technical-spec.md`](technical-spec.md) | Консолидированная спека MVP, non-goals, ссылки на полный API-справочник |

### 2. Архитектура и планирование

| Файл | Содержание |
|------|------------|
| [`architecture.md`](architecture.md) | Control plane vs runtime, сервисы, поток данных, ссылки на API |
| [`development-plan.md`](development-plan.md) | Сделано / ближайшие шаги, SocratiCode |

### 3. API (машины и люди)

| Файл | Содержание |
|------|------------|
| [`http-api-reference.md`](http-api-reference.md) | **Единый** список путей, методов, тел JSON, заголовков, `curl` |
| [`api/README.md`](api/README.md) | Зачем YAML в репо, где живой OpenAPI (`/openapi.json`) |
| [`api/orchestrator-openapi.yaml`](api/orchestrator-openapi.yaml) | Краткое дерево путей оркестратора |
| [`api/agent-openapi.yaml`](api/agent-openapi.yaml) | Краткое дерево путей агента + operator |

### 4. Старт, окружение, отладка (`handover/`)

Индекс папки: **[`handover/README.md`](handover/README.md)**.

Типовые сценарии: установка, compose, переменные, каналы, операторская консоль, Cursor/MCP, типовые сбои.

### 5. Корень репозитория (вне `docs/`)

Длинные материалы для контекста ИИ / история ТЗ:

- `cursor_prompt_vendor_support_orchestrator.md`
- `technical_spec_vendor_support_orchestrator.md`
- `AGENTS.md` — кратко «кто такой агент» и куда смотреть в `docs/`

---

## Связи «что к чему»

```text
Требования (technical-spec)
       ↓
Архитектура (architecture) ←── HTTP (http-api-reference) ←── api/*.yaml + /openapi.json
       ↓
Запуск (handover/setup, environment)
       ↓
Каналы (handover/channel-entrypoints → telegram, max, operator-api)
```

Оркестратор **не** проксирует вопросы пользователя; runtime только у **vendor-support-agent** — см. `architecture.md` и `AGENTS.md`.

### Тестовые UI (dev-only, в репозитории)

**`test_interfaces/agent_support_gleb/`** — Node-прокси для ручной проверки агента и оркестратора. В Docker: профиль **`devtools`** в `infra/docker-compose.dev.yml` (порты **8788** / **8789** / **8790**). Не часть production runtime.
