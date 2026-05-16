# Handover — старт, окружение, каналы

Папка **`docs/handover/`**: практические инструкции для разработчика и эксплуатации. Общая карта всего `docs/`: **[`../README.md`](../README.md)**.

---

## Файлы по смыслу

### Запуск и конфигурация

| Файл | Зачем |
|------|--------|
| [`setup.md`](setup.md) | Compose, prerequisites, Alembic, ссылки на env и API |
| [`server-deploy.md`](server-deploy.md) | **Перенос на сервер:** git clone, что копировать файлами, запуск prod-compose |
| [`environment.md`](environment.md) | Слои `.env` (корень / orchestrator-api / vendor-support-agent), переменные, эскалация |

### Агент: входы и операторы

| Файл | Зачем |
|------|--------|
| [`channel-entrypoints.md`](channel-entrypoints.md) | Три канала → один `AgentEngine`; таблица эндпоинтов |
| [`telegram.md`](telegram.md) | Webhook, секрет, ngrok, ссылка на полный HTTP-справочник |
| [`max.md`](max.md) | Webhook MAX, подписка, ссылка на полный HTTP-справочник |
| [`operator-api.md`](operator-api.md) | Консоль поддержки: список чатов, история, ответ в канал |

Полный перечень HTTP (включая operator): **[`../http-api-reference.md`](../http-api-reference.md)**.

### Инструменты и сбои

| Файл | Зачем |
|------|--------|
| [`socraticode.md`](socraticode.md) | Индекс проекта в Cursor через MCP, скрипты |
| [`troubleshooting.md`](troubleshooting.md) | Заготовка под типовые проблемы (Docker, миграции, очереди) |

---

## Рекомендуемый порядок чтения

1. [`../README.md`](../README.md) — карта всей документации  
2. [`setup.md`](setup.md) + [`environment.md`](environment.md)  
3. [`../http-api-reference.md`](../http-api-reference.md) — если интегрируетесь по HTTP  
4. [`channel-entrypoints.md`](channel-entrypoints.md) и нужный канал (`telegram` / `max`)  
5. При консоли оператора — [`operator-api.md`](operator-api.md)

Тестовые UI в репозитории: **`test_interfaces/agent_support_gleb/`** — в dev-compose с профилем **`devtools`** (порты 8788–8790), прокси к **vendor-support-agent** и при необходимости к **orchestrator-api**. См. [`../../test_interfaces/agent_support_gleb/README.md`](../../test_interfaces/agent_support_gleb/README.md).
