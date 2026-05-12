# HTTP API — полный справочник

Карта всей документации: [`README.md`](README.md).

Два сервиса в dev (см. `infra/docker-compose.dev.yml`):

| Сервис | Базовый URL (локально) | Живой OpenAPI |
|--------|------------------------|---------------|
| **orchestrator-api** | `http://localhost:8000` | `GET /openapi.json`, UI: `/docs`, `/redoc` |
| **vendor-support-agent** | `http://localhost:8010` | `GET /openapi.json`, UI: `/docs`, `/redoc` |

Статические копии спецификаций (упрощённые): `docs/api/orchestrator-openapi.yaml`, `docs/api/agent-openapi.yaml`.

Переменные окружения: `docs/handover/environment.md`.

---

## Аутентификация

### orchestrator-api

Если **`ORCHESTRATOR_REQUIRE_API_KEY=true`**, для всех путей **кроме** перечисленных ниже нужен ключ:

- Заголовок **`X-Api-Key: <API_KEY_DEV>`** или **`Authorization: Bearer <API_KEY_DEV>`**.

**Пути без ключа** (всегда): `/`, `/favicon.ico`, `/api/v1/health`, `/api/v1/status`, `/api/v1/infrastructure/status`, `/docs`, `/redoc`, `/openapi.json` и ресурсы под `/docs/`, `/redoc/`.

При `ORCHESTRATOR_REQUIRE_API_KEY=false` остальные маршруты тоже доступны без ключа.

### vendor-support-agent

| Механизм | Где нужен |
|----------|-----------|
| **`WIDGET_API_KEY`** (если задан в `.env`) | `POST /api/v1/invoke`, `POST /api/v1/widget/invoke` — заголовок **`Authorization: Bearer …`** или **`X-Widget-Api-Key`** |
| **`OPERATOR_API_KEY`** (если задан) | Все `GET/POST /api/v1/operator/...` — **`Authorization: Bearer …`** или **`X-Operator-Api-Key`**; если `OPERATOR_API_KEY` пуст, используется тот же ключ, что и **`WIDGET_API_KEY`** (и те же заголовки) |
| **`TELEGRAM_WEBHOOK_SECRET`** (если задан) | `POST /api/v1/telegram/webhook` — заголовок **`X-Telegram-Bot-Api-Secret-Token`** (= `secret_token` в `setWebhook`) |
| **`MAX_WEBHOOK_SECRET`** (если задан) | `POST /api/v1/max/webhook` — заголовок **`X-Max-Bot-Api-Secret`** |

Вебхуки Telegram/MAX **не** используют `WIDGET_API_KEY`.

---

## vendor-support-agent — все маршруты

Префикс каналов и invoke — без версии в health (корень приложения).

### `GET /health`

Проверка живости процесса.

**Ответ 200:** `{"status":"ok"}`

---

### `GET /metadata`

Идентификатор агента для интеграций.

**Ответ 200:** `{"agent_id":"vendor-support-agent","version":"0.1.0"}`

---

### `POST /api/v1/invoke`

Тело: **`InvokeRequest`** (JSON).

```json
{
  "channel": "widget",
  "conversation_id": "session-uuid-or-stable-id",
  "user_id": "user-123",
  "message": "Текст вопроса",
  "context": null
}
```

- **`channel`:** `"widget"` | `"telegram"` | `"max"`
- **`conversation_id`:** для Telegram/MAX — обычно строковый **`chat_id`**; для виджета — id сессии на стороне клиента (до 64 символов иначе хешируется внутри).
- **`message`:** непустая строка.

**Заголовки (если задан `WIDGET_API_KEY`):** `Authorization: Bearer <ключ>` или `X-Widget-Api-Key: <ключ>`

**Ответ 200:** **`InvokeResponse`**

```json
{
  "status": "success",
  "answer": "…",
  "sources": [
    {"document_id": "…", "chunk_id": "…", "title": "…"}
  ],
  "meta": {
    "confidence": 0.42,
    "needs_human": false,
    "escalated": false,
    "escalation_reasons": [],
    "conversation_holder": "ai",
    "ai_muted": false
  }
}
```

- **`meta.conversation_holder`:** `ai` \| `human` — кто ведёт диалог (см. `POST .../operator/.../control` и колонку БД `conversation_holder`).
- **`meta.ai_muted`:** если `true`, ответ ИИ не генерировался (контроль у `human`); в Telegram/MAX вебхук **не** шлёт сообщение в чат.

---

### `POST /api/v1/widget/invoke`

Семантика и тело — **как у** `POST /api/v1/invoke` (алиас для виджета).

---

### `POST /api/v1/telegram/invoke`

Ручной вызов в формате `InvokeRequest` без Telegram `Update` (отладка, Postman).

Тело и ответ — как у `POST /api/v1/invoke` с `channel: "telegram"`.

**Аутентификация:** **`WIDGET_API_KEY` не проверяется** на этом маршруте; для публичного ingress ограничьте доступ (VPN, IP allowlist, отдельный секрет на reverse-proxy).

---

### `POST /api/v1/telegram/webhook`

Тело: объект **[Update](https://core.telegram.org/bots/api#update)** (JSON от Telegram).

**Заголовок (опционально):** `X-Telegram-Bot-Api-Secret-Token` = `TELEGRAM_WEBHOOK_SECRET`.

**Ответ 200:** `{"ok": true}` (в т.ч. для игнорируемых апдейтов).

Поведение: команды `/start`, `/help`; иные `/команды` — короткая подсказка; обычный текст — RAG+LLM, ответ в чат через Bot API. Чат из **`ESCALATION_TELEGRAM_CHAT_ID`** не обрабатывается как диалог пользователя.

---

### `POST /api/v1/max/webhook`

Тело: объект **Update** MAX (см. `docs/handover/max.md`).

**Заголовок (опционально):** `X-Max-Bot-Api-Secret` = `MAX_WEBHOOK_SECRET`.

**Ответ 200:** `{"ok": true}`

---

### `POST /api/v1/max/invoke`

Ручной вызов: тело **`InvokeRequest`** с `channel: "max"`, ответ **`InvokeResponse`**.

**Аутентификация:** как у `POST /api/v1/telegram/invoke` — **`WIDGET_API_KEY` не проверяется**; ограничьте доступ на сетевом уровне при необходимости.

---

### `GET /api/v1/operator/conversations`

Список диалогов runtime (все каналы).

**Query:**

| Параметр | По умолчанию | Описание |
|----------|---------------|----------|
| `limit` | 50 | 1–200 |
| `offset` | 0 | смещение |
| `channel` | — | опционально: `widget` \| `telegram` \| `max` |
| `include_hidden` | `false` | при `true` в выборку попадают диалоги с **`hidden: true`** (по умолчанию они скрыты из списка) |

**Заголовки:** см. раздел «OPERATOR_API_KEY» выше.

**Ответ 200:** `{ "items": [ { "id", "channel", "user_id", "created_at", "last_message_at", "conversation_holder", "hidden" } ], "limit", "offset" }` — `conversation_holder`: `ai` \| `human`; **`hidden`**: boolean.

---

### `GET /api/v1/operator/conversations/{conversation_id}`

Карточка одного диалога (`conversation_id` = поле `id` из списка).

**Ответ 200:** объект диалога (в т.ч. **`hidden`**). **404** — не найден.

---

### `GET /api/v1/operator/conversations/{conversation_id}/messages`

История сообщений.

**Query:** `limit` (1–1000, по умолчанию 500).

**Ответ 200:** `{ "conversation_id", "messages": [ { "id", "role", "content", "created_at" } ] }`

Роли: `user`, `assistant`, **`operator`**.

---

### `POST /api/v1/operator/conversations/{conversation_id}/reply`

Операторский ответ в тот же канал / чат.

**Тело:**

```json
{ "text": "Текст ответа оператора" }
```

**Ответ 200:**

```json
{
  "ok": true,
  "conversation_id": "…",
  "channel": "telegram",
  "delivery": "sent"
}
```

- **`delivery`:** `sent` — ушло в Telegram или MAX; **`stored`** — только БД (канал **widget**; доставку в браузер делает ваш бэкенд через опрос этого API).

**Ошибки:** **400** — неверный `conversation_id` для канала (например не число для Telegram); **404** — диалог не найден; **401** — нет/неверный ключ оператора; **502** — сбой отправки во внешний API.

---

### `POST /api/v1/operator/conversations/{conversation_id}/control`

Зафиксировать, **кто ведёт диалог**: отвечает агент (`ai`) или только оператор (`human`). При `human` новые пользовательские сообщения в этом чате **не** вызывают LLM и в Telegram/MAX **не** отправляется ответ бота (сообщение пользователя в БД сохраняется).

**Тело:**

```json
{ "holder": "human" }
```

Значения: `"ai"` \| `"human"`.

**Ответ 200:** `{ "ok": true, "conversation_id": "…", "conversation_holder": "human" }`

**404** — диалог не найден (часто: ещё не было ни одного сообщения в этом `conversation_id`).

---

### `POST /api/v1/operator/conversations/{conversation_id}/visibility`

Пометить диалог как скрытый из списка оператора или снова показать (**soft hide**, данные и история не удаляются).

**Тело:**

```json
{ "hidden": true }
```

**Ответ 200:** `{ "ok": true, "conversation_id": "…", "hidden": true }`

**404** — диалог не найден.

---

## orchestrator-api — все маршруты

Префикс API: **`/api/v1`** (кроме документов знаний: **`/api/v1/knowledge/...`**).

### `GET /api/v1/health`

**Ответ 200:** сервис жив.

---

### `GET /api/v1/status`

Лёгкий статус (MVP).

---

### `GET /api/v1/infrastructure/status`

Проверки Postgres, Redis, Qdrant, агента, хранилища и т.д.

---

### `GET /api/v1/knowledge/documents`

Список документов базы знаний.

**Ответ 200:** `{ "items": [ DocumentOut, … ] }`

---

### `POST /api/v1/knowledge/documents`

Создание документа: **либо** JSON, **либо** `multipart/form-data` с файлом (не оба).

**Вариант A — JSON** (`Content-Type: application/json`):

```json
{
  "title": "Название",
  "content": "Текст или markdown",
  "metadata": {},
  "auto_index": false
}
```

**Вариант B — multipart:** поле файла (`file`) + имя файла как заголовок.

**Ответ 200:** `{ "status", "document_id", "indexing_status" }`

---

### `GET /api/v1/knowledge/documents/{document_id}`

**Ответ 200:** `DocumentOut`. **404** — не найден.

---

### `PATCH /api/v1/knowledge/documents/{document_id}`

**Тело:** `{ "title": "…", "metadata": {} }` (поля опциональны).

**Ответ 200:** `DocumentOut`

---

### `DELETE /api/v1/knowledge/documents/{document_id}`

Мягкое удаление: статус `deleted`.

**Ответ 200:** `{ "status": "deleted", "document_id": "…" }`

---

### `POST /api/v1/knowledge/reindex`

Постановка задачи индексации в очередь (Redis/RQ).

**Тело:**

```json
{
  "mode": "full",
  "document_id": null
}
```

- **`mode`:** `"full"` | `"incremental"` | `"document"`
- при **`mode": "document"`** поле **`document_id`** обязательно (строка id документа).

**Ответ 200:** объект задачи (`job_id`, `mode`, `status`, `progress`, …).

---

### `GET /api/v1/knowledge/index/status`

Сводка по задачам индексации: счётчики по статусам, последняя job.

**Ответ 200:** JSON с `job_counts_by_status`, `latest_job`.

---

### `GET /api/v1/jobs`

Список задач индексации.

**Ответ 200:** `{ "items": [ JobOut, … ] }`

---

### `GET /api/v1/jobs/{job_id}`

**Ответ 200:** `JobOut`. **404** — не найдена.

---

### `GET /api/v1/prompts`

Список шаблонов промтов и последних версий.

---

### `GET /api/v1/prompts/{prompt_key}`

Актуальное содержимое последней версии.

**Ответ 404:** неизвестный `prompt_key` или нет версий.

---

### `PUT /api/v1/prompts/{prompt_key}`

**Тело:** `{ "content": "…" }` — новая версия.

**Ответ 200:** `PromptOut`

---

### `GET /api/v1/prompts/{prompt_key}/versions`

Список версий.

---

### `GET /api/v1/agents`

Список зарегистрированных агентов (MVP — фиксированный список).

---

### `GET /api/v1/agents/{agent_id}`

**Ответ 404:** только `vendor-support-agent` поддерживается в MVP.

---

### `GET /api/v1/agents/{agent_id}/status`

MVP: заглушка статуса.

---

### `GET /api/v1/logs/runtime`

Логи runtime-агента из Postgres.

**Query:** `limit` (1–500, по умолчанию 50).

---

### `GET /api/v1/logs/indexing`

Заглушка: `{ "items": [], "note": "…" }`

---

### `GET /api/v1/audit/events`

Заглушка: `{ "items": [], "note": "…" }`

---

## Примеры `curl`

Оркестратор с ключом:

```bash
curl -sS -H "X-Api-Key: YOUR_API_KEY_DEV" http://localhost:8000/api/v1/knowledge/documents
```

Агент (invoke + ключ виджета):

```bash
curl -sS -X POST http://localhost:8010/api/v1/widget/invoke \
  -H "Authorization: Bearer YOUR_WIDGET_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"widget\",\"conversation_id\":\"demo-1\",\"user_id\":\"u1\",\"message\":\"Привет\"}"
```

Оператор: список чатов:

```bash
curl -sS -H "Authorization: Bearer YOUR_OPERATOR_OR_WIDGET_KEY" \
  "http://localhost:8010/api/v1/operator/conversations?limit=20"
```
