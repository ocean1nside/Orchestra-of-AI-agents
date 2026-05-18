# Handoff для внешних интеграций

Локальные файлы (не в git, см. корневой `.gitignore`):

| Файл | Назначение |
|------|------------|
| `all-secrets.local.md` | Все секреты и URL |
| `external-widget-integration.local.md` | Текст для внешних разработчиков |
| `demo-widget.local.html` | Демо-виджет: открыть в браузере двойным кликом |

Для `demo-widget.local.html` на prod нужен CORS на `/api/v1/widget/invoke` (см. `scripts/agent-webhook.nginx`).
