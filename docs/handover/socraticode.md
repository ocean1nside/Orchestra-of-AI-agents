# SocratiCode (dev-only)

← [Карта `docs/`](../README.md) · [Индекс handover](README.md)

SocratiCode используется **только** для разработки/передачи проекта и подключения MCP в Cursor.
В production/runtime он не используется и не должен входить в `infra/docker-compose.yml`.

## Требования

- установлен Docker

## Подключение MCP в Cursor

1. Убедитесь, что существует файл `.vscode/mcp.json` (создаётся в этом репозитории).
2. Откройте проект в Cursor.
3. Включите MCP-сервер(а) согласно конфигурации.

## Индексация проекта

### Вариант A (локально через Cursor)

По умолчанию MCP-сервер SocratiCode запускается **локально** (см. `.vscode/mcp.json`) и контейнер не обязателен.

Рекомендуемый режим для скорости работы агента:

- включить MCP `socraticode`;
- сделать **полную индексацию** проекта один раз;
- включить **watcher**, чтобы индекс обновлялся автоматически при изменениях файлов.

### Вариант B (через Docker dev-compose)

В `infra/docker-compose.dev.yml` добавлен опциональный сервис `socraticode` (dev-only) под профилем `devtools`.

Запуск:

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d socraticode
```

Production compose (`infra/docker-compose.yml`) **не** включает SocratiCode по требованиям ТЗ.

Примечание: контейнер в этом репозитории — **dev-утилита** (с volume на проект). Реальная индексация/графы для ускорения работы агента идут через **MCP-сервер SocratiCode** в Cursor.

## Как понять, что индекс актуальный

SocratiCode умеет:

- **`codebase_index`** — запустить индексацию (асинхронно);
- **`codebase_status`** — проверить прогресс/статус;
- **`codebase_watch`** — включить watcher (авто-обновление индекса);
- **`codebase_update`** — инкрементально обновить индекс (синхронно);
- **`codebase_graph_build`** — собрать “граф” (зависимости/вызовы) для impact/flow.

Политика для этого репо:

- при начале работы с проектом: `codebase_status` → если индекса нет, запустить `codebase_index`;
- держать `codebase_watch` в состоянии `active`;
- если были массовые изменения (переезды/рефакторинг) — запускать `codebase_update` или полный `codebase_index`.


