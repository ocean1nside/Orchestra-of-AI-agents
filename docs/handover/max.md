# MAX: webhook и ответы

Официальная документация: [dev.max.ru](https://dev.max.ru/docs-api/methods/POST/subscriptions), объект [Update](https://dev.max.ru/docs-api/objects/Update).

## Эндпоинты

- **`POST /api/v1/max/webhook`** — тело: JSON **Update** (например `update_type: "message_created"`). Агент отвечает через **`POST /messages`** на `platform-api.max.ru` с заголовком `Authorization: <MAX_BOT_TOKEN>`.
- **`POST /api/v1/max/invoke`** — ручной тест: тело **`InvokeRequest`** с `"channel": "max"`.

## Переменные `.env`

| Переменная | Назначение |
|------------|------------|
| `MAX_BOT_TOKEN` | Токен бота (платформа MAX → Интеграция → Получить токен) |
| `MAX_WEBHOOK_SECRET` | Необязательно: тот же `secret`, что при `POST /subscriptions`; проверяется заголовок `X-Max-Bot-Api-Secret` |
| `MAX_API_BASE` | По умолчанию `https://platform-api.max.ru` |

## Подписка на webhook

Пример (подставьте URL и токен):

```bash
curl -X POST "https://platform-api.max.ru/subscriptions" \
  -H "Authorization: <MAX_BOT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-host.example/api/v1/max/webhook",
    "update_types": ["message_created", "message_edited", "bot_started"],
    "secret": "<тот же MAX_WEBHOOK_SECRET что в .env>"
  }'
```

Требования MAX: **HTTPS**, валидный TLS (самоподписанный на стороне MAX для webhook endpoint в общем случае не подойдёт — см. их доку). Для локальной разработки обычно туннель с публичным HTTPS (аналогично Telegram).

Сообщения от самого бота (`sender.is_bot`) игнорируются, чтобы не зациклить ответы.
