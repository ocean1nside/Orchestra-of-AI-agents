# SocratiCode (dev-only)

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

### Вариант B (через Docker dev-compose)

В `infra/docker-compose.dev.yml` добавлен опциональный сервис `socraticode` (dev-only) под профилем `devtools`.

Запуск:

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d socraticode
```

Production compose (`infra/docker-compose.yml`) **не** включает SocratiCode по требованиям ТЗ.

