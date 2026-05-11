# Telegram: вебхук и проверка

## Что реализовано

- **`POST /api/v1/telegram/webhook`** — принимает настоящий [Update](https://core.telegram.org/bots/api#update) от Telegram, вызывает агента и отвечает пользователю через **`sendMessage`**.
- **`POST /api/v1/telegram/invoke`** — тот же JSON, что и для виджета (`InvokeRequest`), удобно для Postman без Telegram.

Переменные в корневом `.env`:

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Опционально: тот же секрет, что передаёте в `setWebhook` как `secret_token`; иначе любой POST на URL вебхука сможет дергать бота |

## Локальная проверка (HTTPS)

Telegram принимает только **HTTPS** для `url` в `setWebhook`. Для машины за NAT используйте туннель, например [ngrok](https://ngrok.com/):

```bash
ngrok http 8010
```

Дальше (подставьте URL и токены):

```bash
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://<ваш-ngrok>.ngrok-free.app/api/v1/telegram/webhook" \
  -d "secret_token=<тот же TELEGRAM_WEBHOOK_SECRET что в .env>"
```

Перезапустите контейнер агента после правки `.env`.

## Ключ для внешнего виджета

См. `env.example`: **`WIDGET_API_KEY`**. Если задан, запросы к **`POST /api/v1/widget/invoke`** и **`POST /api/v1/invoke`** должны передавать ключ:

- заголовок `Authorization: Bearer <ключ>`, или
- заголовок `X-Widget-Api-Key: <ключ>`

Вебхук Telegram этот ключ **не** использует (аутентификация вебхука — через `secret_token` / заголовок `X-Telegram-Bot-Api-Secret-Token`).
