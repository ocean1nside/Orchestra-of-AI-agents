# Три точки входа в агента (`vendor-support-agent`)

← [Карта `docs/`](../README.md) · [Индекс handover](README.md)

Все каналы в итоге вызывают один **`AgentEngine`**: RAG по Qdrant + Postgres, промпт, LLM, запись runtime-логов.

| Канал | Кто инициатор | Наш HTTP-эндпоинт | Исходящие вызовы |
|--------|----------------|------------------|-------------------|
| **Виджет** (внешняя система) | Клиент / CRM шлёт JSON | `POST /api/v1/widget/invoke` (и дубль `POST /api/v1/invoke`) | Нет — ответ в теле HTTP |
| **Telegram** | Telegram шлёт Update на наш URL | `POST /api/v1/telegram/webhook` | `https://api.telegram.org/bot…/sendMessage` |
| **MAX** | MAX шлёт Update на наш URL | `POST /api/v1/max/webhook` | `POST https://platform-api.max.ru/messages?chat_id=…` |

## Аутентификация

- **Виджет / общий invoke**: опционально `WIDGET_API_KEY` → заголовки `Authorization: Bearer …` или `X-Widget-Api-Key` (см. `telegram.md`).
- **Telegram webhook**: опционально `TELEGRAM_WEBHOOK_SECRET` ↔ заголовок `X-Telegram-Bot-Api-Secret-Token` (и `secret_token` в `setWebhook`).
- **MAX webhook**: опционально `MAX_WEBHOOK_SECRET` ↔ заголовок `X-Max-Bot-Api-Secret` (и поле `secret` в `POST https://platform-api.max.ru/subscriptions`).

## Ручная отладка (без реального webhook)

- `POST /api/v1/telegram/invoke` — тело как у виджета (`InvokeRequest`, `channel: "telegram"`).
- `POST /api/v1/max/invoke` — то же, `channel: "max"`.

Оркестратор (`orchestrator-api`) в этих потоках **не участвует** как прокси сообщений пользователя; он нужен для документов, индексации и управления.

## Консоль оператора (внешняя страница)

Список чатов, история и ответ в тот же канал / чат: **[`operator-api.md`](operator-api.md)** (кратко) и полностью — **[`../http-api-reference.md`](../http-api-reference.md)** (раздел `vendor-support-agent`, operator).
