# vendor-support-agent — HTTP API

Сервис **runtime**: принимает сообщения пользователей, ищет по базе знаний (Postgres + Qdrant) и отвечает через LLM.  
**Не** управляет загрузкой документов и промптами в БД оркестратора — это `orchestrator-api` (:8000).

| | |
|---|---|
| **Порт по умолчанию** | `8010` |
| **Живая спека** | `GET /docs`, `GET /redoc`, `GET /openapi.json` |
| **Полный справочник репозитория** | `docs/http-api-reference.md` (агент + оркестратор) |

---

## Аутентификация (кратко)

| API | Когда нужен ключ | Заголовки |
|-----|------------------|-----------|
| **Invoke / widget** | Если в `.env` задан `WIDGET_API_KEY` | `Authorization: Bearer <key>` или `X-Widget-Api-Key` |
| **Operator** | Если задан `OPERATOR_API_KEY` или `WIDGET_API_KEY` | `Authorization: Bearer <key>` или `X-Operator-Api-Key` |
| **Telegram webhook** | Опционально `TELEGRAM_WEBHOOK_SECRET` | `X-Telegram-Bot-Api-Secret-Token` |
| **MAX webhook** | Опционально `MAX_WEBHOOK_SECRET` | `X-Max-Bot-Api-Secret` |
| **Health, metadata** | Нет | — |
| **telegram/max invoke** (ручные) | **Нет** в коде | Ограничивайте на сетевом уровне |

Пустой `WIDGET_API_KEY` = invoke без ключа (только для dev).

---

## 1. Служебные

### `GET /health`

**Назначение:** liveness (Docker, балансировщик).

**Ответ:** `{"status": "ok"}`

---

### `GET /metadata`

**Назначение:** идентификатор и версия агента.

**Ответ:** `{"agent_id": "vendor-support-agent", "version": "0.1.0"}`

---

### `GET /docs`, `GET /redoc`, `GET /openapi.json`

**Назначение:** интерактивная и машинная документация FastAPI (автогенерация из кода).

---

## 2. Runtime — вызов агента (Invoke)

Общий движок: **`AgentEngine.invoke`**. Сохраняет сообщение пользователя и ответ в Postgres (`runtime_conversations`, `runtime_messages`).  
При `conversation_holder = human` ИИ **не** генерирует ответ (`meta.ai_muted: true`, пустой `answer`).

### Тело запроса — `InvokeRequest`

```json
{
  "channel": "widget",
  "conversation_id": "строка-id-диалога",
  "user_id": "строка-id-пользователя",
  "message": "текст вопроса",
  "context": {}
}
```

| Поле | Значения | Смысл |
|------|----------|--------|
| `channel` | `widget` \| `telegram` \| `max` | Канал (влияет на эскалацию и логику) |
| `conversation_id` | строка | Один диалог; для Telegram/MAX обычно **числовой chat_id** строкой |
| `user_id` | строка | Пользователь в канале |
| `message` | строка, min 1 | Вопрос пользователя |
| `context` | объект или `null` | Доп. контекст (опционально) |

### Ответ — `InvokeResponse`

```json
{
  "status": "success",
  "answer": "текст ответа",
  "sources": [
    { "document_id": "...", "chunk_id": "...", "title": "..." }
  ],
  "meta": {
    "confidence": 0.0,
    "needs_human": false,
    "escalated": false,
    "escalation_reasons": [],
    "conversation_holder": "ai",
    "ai_muted": false
  }
}
```

| Поле `meta` | Смысл |
|-------------|--------|
| `conversation_holder` | Кто ведёт диалог: `ai` или `human` |
| `ai_muted` | `true` — LLM не вызывался (режим только оператор) |
| `sources` | Фрагменты из базы знаний, использованные при ответе |
| `escalated` | Отправлено уведомление в Telegram-группу эскалации (если настроено) |

---

### `POST /api/v1/invoke`

**Назначение:** универсальный invoke (то же, что widget).

**Аутентификация:** `WIDGET_API_KEY` (если задан).

**Тело / ответ:** `InvokeRequest` → `InvokeResponse`.

---

### `POST /api/v1/widget/invoke`

**Назначение:** основной эндпоинт **веб-виджета** (алиас по смыслу к `/invoke`).

**Аутентификация:** `WIDGET_API_KEY` (если задан).

**Тело / ответ:** `InvokeRequest` → `InvokeResponse`. Ожидается `channel: "widget"`.

---

### `POST /api/v1/telegram/invoke`

**Назначение:** **ручная** проверка без Telegram Update (curl, Postman).

**Аутентификация:** нет в коде.

**Тело:** `InvokeRequest` с `channel: "telegram"`. **Ответ:** `InvokeResponse` (без отправки в Telegram).

---

### `POST /api/v1/max/invoke`

**Назначение:** **ручная** проверка без объекта MAX Update.

**Аутентификация:** нет в коде.

**Тело:** `InvokeRequest` с `channel: "max"`. **Ответ:** `InvokeResponse` (без отправки в MAX).

---

## 3. Telegram

### `POST /api/v1/telegram/webhook`

**Назначение:** **продакшен-вход** из Telegram Bot API. Тело — JSON **Update**.

**Аутентификация:** если задан `TELEGRAM_WEBHOOK_SECRET` — заголовок `X-Telegram-Bot-Api-Secret-Token` должен совпадать.

**Поведение:**

- `/start`, `/help` — приветствие и справка.
- Другие `/команды` — короткая подсказка.
- Обычный текст → RAG + LLM → ответ в чат (`sendMessage` / `editMessageText` с эффектом набора).
- Чат из `ESCALATION_TELEGRAM_CHAT_ID` не обрабатывается как пользовательский диалог.
- При `human` и `ai_muted` — в чат **не** отправляется ответ бота (сообщение пользователя в БД сохраняется).

**Ответ:** `{"ok": true}` (в т.ч. для игнорируемых апдейтов).

**Требует:** `TELEGRAM_BOT_TOKEN` в `.env`.

---

## 4. MAX

### `POST /api/v1/max/webhook`

**Назначение:** **продакшен-вход** из MAX. Тело — JSON **Update** (`message_created`, `message_edited`).

**Аутентификация:** опционально `MAX_WEBHOOK_SECRET` → `X-Max-Bot-Api-Secret`.

**Поведение:** текст пользователя → `AgentEngine` → ответ через `POST /messages` (platform-api.max.ru). При `ai_muted` ответ не шлётся.

**Ответ:** `{"ok": true}`.

**Требует:** `MAX_BOT_TOKEN`, при необходимости `MAX_API_BASE`.

---

## 5. Operator API — консоль поддержки

Префикс: **`/api/v1/operator`**.  
Данные из Postgres (`runtime_*`). Для **внешней** CRM/админки.

**Аутентификация на всех маршрутах ниже:** `OPERATOR_API_KEY` или, если пусто, `WIDGET_API_KEY`.

---

### `GET /api/v1/operator/conversations`

**Назначение:** список диалогов по всем каналам, сортировка по времени последнего сообщения.

**Query:**

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `limit` | 50 | 1–200 |
| `offset` | 0 | пагинация |
| `channel` | — | `widget` \| `telegram` \| `max` |
| `include_hidden` | `false` | `true` — показать скрытые диалоги |

**Ответ:** `{ "items": [ ... ], "limit", "offset" }` — элемент: `id`, `channel`, `user_id`, `created_at`, `last_message_at`, `conversation_holder`, `hidden`.

`id` = `conversation_id` в invoke/webhook.

---

### `GET /api/v1/operator/conversations/{conversation_id}`

**Назначение:** карточка одного диалога.

**Ответ:** как элемент списка. **404** — не найден.

---

### `GET /api/v1/operator/conversations/{conversation_id}/messages`

**Назначение:** история сообщений по возрастанию времени.

**Query:** `limit` (1–1000, по умолчанию 500).

**Ответ:** `{ "conversation_id", "messages": [ { "id", "role", "content", "created_at" } ] }`  
Роли: `user`, `assistant`, `operator`.

---

### `POST /api/v1/operator/conversations/{conversation_id}/reply`

**Назначение:** ответ **оператора** пользователю.

**Тело:** `{ "text": "..." }` (1–12000 символов).

**Поведение:**

| Канал | `delivery` |
|-------|------------|
| `telegram` | `sent` — `sendMessage` в чат (`conversation_id` = chat id) |
| `max` | `sent` — API MAX |
| `widget` | `stored` — только запись в БД; доставку в браузер делает ваш фронт (опрос messages) |

**Ответ:** `{ "ok", "conversation_id", "channel", "delivery" }`  
**Ошибки:** **400** (неверный id для канала), **404**, **502** (сбой внешнего API).

---

### `POST /api/v1/operator/conversations/{conversation_id}/control`

**Назначение:** кто ведёт диалог — **ИИ** или **только менеджер**.

**Тело:** `{ "holder": "ai" }` или `{ "holder": "human" }`.

| `holder` | Эффект |
|----------|--------|
| `ai` | Агент снова отвечает на новые сообщения |
| `human` | ИИ молчит; вебхуки не шлют ответ; виджет получает `ai_muted` |

**Ответ:** `{ "ok", "conversation_id", "conversation_holder" }`. **404** — диалог не найден.

---

### `POST /api/v1/operator/conversations/{conversation_id}/visibility`

**Назначение:** **скрыть** или **показать** диалог в списке оператора (soft hide, данные не удаляются).

**Тело:** `{ "hidden": true }` или `{ "hidden": false }`.

**Ответ:** `{ "ok", "conversation_id", "hidden" }`. **404** — не найден.

---

## Сводная таблица путей

| Метод | Путь | Группа |
|-------|------|--------|
| GET | `/health` | служебные |
| GET | `/metadata` | служебные |
| GET | `/docs`, `/redoc`, `/openapi.json` | служебные |
| POST | `/api/v1/invoke` | invoke |
| POST | `/api/v1/widget/invoke` | invoke |
| POST | `/api/v1/telegram/invoke` | invoke (ручной) |
| POST | `/api/v1/max/invoke` | invoke (ручной) |
| POST | `/api/v1/telegram/webhook` | telegram |
| POST | `/api/v1/max/webhook` | max |
| GET | `/api/v1/operator/conversations` | operator |
| GET | `/api/v1/operator/conversations/{id}` | operator |
| GET | `/api/v1/operator/conversations/{id}/messages` | operator |
| POST | `/api/v1/operator/conversations/{id}/reply` | operator |
| POST | `/api/v1/operator/conversations/{id}/control` | operator |
| POST | `/api/v1/operator/conversations/{id}/visibility` | operator |

---

## Что агент **не** отдаёт по HTTP

- Загрузка/удаление документов знаний → **orchestrator-api** `/api/v1/knowledge/...`
- Редактирование промптов в БД → **orchestrator-api** `/api/v1/prompts/...`  
  (сами промпты ответа агента сейчас читаются из файлов `prompts/*.md` в этом пакете)

## Данные, к которым агент обращается напрямую (не HTTP)

| Хранилище | Использование |
|-----------|----------------|
| **Postgres** | `runtime_*`, чтение `kb_chunks` для RAG |
| **Qdrant** | векторный поиск по `knowledge_chunks` |
| **Файлы `prompts/`** | system / policy / style для LLM |
