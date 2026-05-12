# OpenAPI YAML в репозитории

Папка **`docs/api/`** — машиночитаемые черновики рядом с человекочитаемым справочником.

Общая карта документации репозитория: **[`../README.md`](../README.md)**.

Здесь лежат **упрощённые** статические описания для обзора в Git и diff в PR.

## Актуальная спецификация у запущенного сервиса

| Сервис | URL (dev) |
|--------|-----------|
| orchestrator-api | `http://localhost:8000/openapi.json` |
| vendor-support-agent | `http://localhost:8010/openapi.json` |

Интерактивно: `/docs` и `/redoc` на том же хосте/порту.

## Файлы в этой папке

| Файл | Назначение |
|------|------------|
| `orchestrator-openapi.yaml` | Основные пути control plane (дублирует структуру из кода) |
| `agent-openapi.yaml` | Пути runtime-агента + operator API |

Человекочитаемый справочник с примерами тел и `curl`: **`../http-api-reference.md`**.
