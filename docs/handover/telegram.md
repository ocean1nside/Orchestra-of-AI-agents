# Telegram: вебхук и проверка

← [Карта `docs/`](../README.md) · [Индекс handover](README.md)

Полный перечень HTTP-методов, тел и заголовков: **[`../http-api-reference.md`](../http-api-reference.md)**.

## Что реализовано

- **`POST /api/v1/telegram/webhook`** — принимает настоящий [Update](https://core.telegram.org/bots/api#update) от Telegram, вызывает агента и отвечает пользователю. Пока идёт вызов LLM: **`sendChatAction`** (статус «печатает»). Ответ сначала **полностью** генерируется на сервере, затем в чат уходит **одно** сообщение; при длинном тексте — быстрый «набор» через **`editMessageText`** (без пары draft+sendMessage, из‑за которой в клиенте часто видно два пузыря).
- Команды **`/start`** и **`/help`** обрабатываются локально (без LLM); любая другая **`/команда`** — короткая подсказка писать текстом без `/`.
- **`POST /api/v1/telegram/invoke`** — тот же JSON, что и для виджета (`InvokeRequest`), удобно для Postman без Telegram.
- Если задан **`ESCALATION_TELEGRAM_CHAT_ID`** (группа `-100…` для уведомлений операторам), апдейты **из этого чата** в вебхуке **игнорируются** — бот туда только шлёт эскалации и не ведёт там диалог.

Переменные в `apps/agents/vendor-support-agent/.env` (или раньше в корневом `.env`):

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Опционально: тот же секрет, что передаёте в `setWebhook` как `secret_token`; иначе любой POST на URL вебхука сможет дергать бота |
| `ESCALATION_TELEGRAM_CHAT_ID` | Опционально: супергруппа для уведомлений эскалации; сообщения **из** этого чата в вебхуке не обрабатываются как запросы к агенту |

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

См. `apps/agents/vendor-support-agent/.env.example`: **`WIDGET_API_KEY`**. Если задан, запросы к **`POST /api/v1/widget/invoke`** и **`POST /api/v1/invoke`** должны передавать ключ:

- заголовок `Authorization: Bearer <ключ>`, или
- заголовок `X-Widget-Api-Key: <ключ>`

Вебхук Telegram этот ключ **не** использует (аутентификация вебхука — через `secret_token` / заголовок `X-Telegram-Bot-Api-Secret-Token`).
