# Operator API (консоль поддержки)

← [Карта `docs/`](../README.md) · [Индекс handover](README.md)

Сервис: **`vendor-support-agent`**. Все пути с префиксом **`/api/v1/operator`**.

Полный перечень вместе с остальными API агента и оркестратора: **[`../http-api-reference.md`](../http-api-reference.md)** (раздел operator и примеры `curl`).

## Аутентификация

Заголовок **`Authorization: Bearer <OPERATOR_API_KEY>`** или **`X-Operator-Api-Key`**.

Если **`OPERATOR_API_KEY`** не задан в окружении агента, используется **`WIDGET_API_KEY`** (удобно для dev; в проде лучше отдельный ключ).

## Эндпоинты

### `POST /api/v1/operator/conversations/{conversation_id}/control`

Тело: `{ "holder": "ai" }` или `{ "holder": "human" }`.

- **`human`** — ИИ **не** отвечает на новые сообщения пользователя в этом чате (вебхуки Telegram/MAX не шлют ответ; виджет получает пустой ответ и `meta.ai_muted: true`).
- **`ai`** — снова отвечает агент.

Диалог должен уже существовать в `runtime_conversations` (после первого сообщения пользователя).

### `GET /api/v1/operator/conversations`

Список диалогов по всем каналам (`widget`, `telegram`, `max`), сортировка по времени последнего сообщения.

Query:

- `limit` (1–200, по умолчанию 50)
- `offset` (по умолчанию 0)
- `channel` — опционально: `widget` | `telegram` | `max`
- `include_hidden` — по умолчанию `false`: в списке **нет** диалогов с `hidden: true`; при `true` показываются и скрытые.

Ответ: `items[]` с полями `id`, `channel`, `user_id`, `created_at`, `last_message_at`, `conversation_holder`, **`hidden`**.

`id` — тот же идентификатор, что **`conversation_id`** в `InvokeRequest` и в вебхуках (для Telegram/MAX это обычно числовой `chat_id` строкой).

### `GET /api/v1/operator/conversations/{conversation_id}`

Карточка одного диалога (те же поля, что в элементе списка, в т.ч. **`hidden`**).

### `GET /api/v1/operator/conversations/{conversation_id}/messages`

История сообщений по возрастанию времени. Роли: `user`, `assistant`, **`operator`** (ответ из консоли).

Query: `limit` (1–1000, по умолчанию 500).

### `POST /api/v1/operator/conversations/{conversation_id}/visibility`

Скрыть или снова показать диалог в списке оператора (**без** удаления строк и истории в БД).

Тело: `{ "hidden": true }` или `{ "hidden": false }`.

Ответ: `{ "ok": true, "conversation_id": "…", "hidden": true|false }`. **404** — диалог не найден.

### `POST /api/v1/operator/conversations/{conversation_id}/reply`

Тело JSON: `{ "text": "..." }` (до 12000 символов).

Поведение:

| Канал | Доставка |
|-------|----------|
| **telegram** | `sendMessage` в чат `conversation_id` (числовой id). Требуется **`TELEGRAM_BOT_TOKEN`**. |
| **max** | API MAX `POST /messages` в чат `conversation_id`. Требуется **`MAX_BOT_TOKEN`**. |
| **widget** | Сообщение **только пишется в БД** (`delivery: "stored"`). Пуша в браузер нет: ваш бэкенд/виджет должен опросом подтянуть новые сообщения через этот же API и отдать пользователю (или свой WebSocket поверх). |

Ответ: `delivery` = `sent` | `stored`, плюс `channel`, `conversation_id`.

## Пример

```bash
curl -sS -H "Authorization: Bearer $OPERATOR_API_KEY" \
  "http://localhost:8010/api/v1/operator/conversations?limit=20"
```

```bash
curl -sS -X POST -H "Authorization: Bearer $OPERATOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Здравствуйте, по вашему вопросу...\"}" \
  "http://localhost:8010/api/v1/operator/conversations/822350012/reply"
```

Подставьте реальный `conversation_id` из списка.
