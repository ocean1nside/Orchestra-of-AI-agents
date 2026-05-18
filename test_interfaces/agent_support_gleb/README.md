# Тестовые интерфейсы `agent_support_gleb`

## Agent Support Studio (основной)

**[`studio/`](studio/)** — единый интерфейс на порту **8790**:

- виджет (`POST /api/v1/widget/invoke`);
- диалоги оператора (все каналы, скрытие, контроль ИИ/менеджер);
- база знаний оркестратора (загрузка файлов, reindex, удаление);
- промпты;
- health / infrastructure status.

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build test-ui-studio
```

→ http://localhost:8790

## Устаревшие (не использовать)

| Папка | Порт | Замена |
|-------|------|--------|
| `chats/` | 8788 | Studio → «Диалоги» |
| `widjet/` | 8789 | Studio → «Виджет» |
| `console/` | 8790 | Studio |

Сервисы `test-ui-chats`, `test-ui-widjet`, `test-ui-console` удалены из `docker-compose.dev.yml`.

## Принципы

- Ключи (`WIDGET_API_KEY`, `OPERATOR_API_KEY`, `ORCHESTRATOR_API_KEY`) только в Node-прокси, не в браузере.
- Runtime-вопросы идут в **агента**; управление знаниями и промптами — в **оркестратор**.

Подробности: [`studio/README.md`](studio/README.md).
