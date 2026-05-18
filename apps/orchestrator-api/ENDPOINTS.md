# orchestrator-api — HTTP API

Сервис **control plane**: управление базой знаний, индексацией, промптами в БД, статусами и логами.  
**Не** принимает пользовательские вопросы в runtime — это **vendor-support-agent** (:8010).

| | |
|---|---|
| **Порт по умолчанию** | `8000` |
| **Живая спека** | `GET /docs`, `GET /redoc`, `GET /openapi.json` |
| **Полный справочник репозитория** | `docs/http-api-reference.md` |
| **Runtime-агент** | `apps/agents/vendor-support-agent/ENDPOINTS.md` |

---

## Аутентификация

Переменные в `apps/orchestrator-api/.env`:

| Переменная | Смысл |
|------------|--------|
| `ORCHESTRATOR_REQUIRE_API_KEY` | `true` — ключ обязателен на защищённых путях |
| `API_KEY_DEV` | Значение ключа |

**Заголовки:** `X-Api-Key: <key>` или `Authorization: Bearer <key>`.

**Без ключа** (всегда доступны):

- `GET /api/v1/health`
- `GET /api/v1/status`
- `GET /api/v1/infrastructure/status`
- `GET /docs`, `GET /redoc`, `GET /openapi.json`

При `ORCHESTRATOR_REQUIRE_API_KEY=true` и пустом/`change-me` `API_KEY_DEV` защищённые запросы вернут **503**.

---

## 1. Служебные и инфраструктура

### `GET /api/v1/health`

**Назначение:** liveness API.

**Ответ:** `{"status": "ok"}`

---

### `GET /api/v1/status`

**Назначение:** лёгкий статус с меткой времени (MVP).

**Ответ:** `{"status": "ok", "time": "<ISO-8601 UTC>"}`

---

### `GET /api/v1/infrastructure/status`

**Назначение:** проверка всей связки для деплоя и мониторинга.

**Проверяет:**

| Сервис в ответе | Что смотрит |
|-----------------|-------------|
| `orchestrator_api` | всегда `ok` |
| `postgres` | `SELECT 1` |
| `redis` | `PING` |
| `qdrant` | `GET /collections` |
| `storage` | существует ли `STORAGE_PATH` (обычно `/storage/knowledge`) |
| `indexing_worker` | есть ли RQ workers в Redis |
| `vendor_support_agent` | `GET {VENDOR_SUPPORT_AGENT_BASE_URL}/health` |

**Ответ:** `{"status": "ok"|"degraded", "services": { ... } }`  
`degraded` — если хотя бы один сервис `error` или `degraded` (например, worker не запущен).

---

### `GET /docs`, `GET /redoc`, `GET /openapi.json`

**Назначение:** интерактивная и машинная документация FastAPI.

---

## 2. База знаний (документы)

Префикс: **`/api/v1/knowledge`**.

Файлы оригиналов: **`STORAGE_PATH`** на диске (в Docker: volume `storage/knowledge`).  
Метаданные и чанки: **Postgres** (`kb_documents`, `kb_document_versions`, `kb_chunks`).  
Вектора после индексации: **Qdrant** (`QDRANT_COLLECTION`, по умолчанию `knowledge_chunks`).

Статусы документа: `uploaded` → `pending_index` / `indexing` → `indexed` | `failed` | `deleted`.

---

### `GET /api/v1/knowledge/documents`

**Назначение:** список всех документов (новые сверху).

**Ответ:**

```json
{
  "items": [
    {
      "document_id": "...",
      "title": "...",
      "status": "indexed",
      "metadata": {},
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

---

### `POST /api/v1/knowledge/documents`

**Назначение:** создать документ — **либо JSON**, **либо multipart-файл** (не оба сразу).

**Вариант A — JSON** (`Content-Type: application/json`):

```json
{
  "title": "Название",
  "content": "текст в UTF-8 (сохранится как content.md)",
  "metadata": {},
  "auto_index": false
}
```

| Поле | Смысл |
|------|--------|
| `auto_index` | `true` → статус `pending_index` (индексация всё равно через **reindex**) |

**Вариант B — файл** (`multipart/form-data`, поле `file`):

- Заголовок `title` берётся из имени файла.
- Поддерживается извлечение текста при индексации (например **DOCX** через worker).

**Ответ:**

```json
{
  "status": "uploaded",
  "document_id": "...",
  "indexing_status": "uploaded"
}
```

**Ошибки:** **400** — пустой файл, оба варианта сразу или ни одного.

После загрузки вызовите **`POST /api/v1/knowledge/reindex`**, чтобы попасть в Qdrant.

---

### `GET /api/v1/knowledge/documents/{document_id}`

**Назначение:** карточка одного документа.

**Ответ:** объект `DocumentOut`. **404** — не найден.

---

### `PATCH /api/v1/knowledge/documents/{document_id}`

**Назначение:** обновить заголовок и/или `metadata` (не перезаливает файл автоматически).

**Тело:**

```json
{
  "title": "новое имя",
  "metadata": { "key": "value" }
}
```

Поля опциональны. **Ответ:** обновлённый `DocumentOut`. **404** — не найден.

---

### `DELETE /api/v1/knowledge/documents/{document_id}`

**Назначение:** мягкое удаление — статус документа **`deleted`** (строка в БД остаётся).

**Ответ:** `{"status": "deleted", "document_id": "..."}`. **404** — не найден.

---

## 3. Индексация (jobs)

Очередь **Redis (RQ)**; выполняет контейнер **`indexing-worker`**.

Пайплайн: извлечь текст → разбить на чанки → эмбеддинги (`EMBED_PROVIDER`: `hash` или `openai`) → Postgres + Qdrant.

---

### `POST /api/v1/knowledge/reindex`

**Назначение:** поставить задачу индексации в очередь.

**Тело — `ReindexRequest`:**

```json
{
  "mode": "full",
  "document_id": null
}
```

| `mode` | Смысл |
|--------|--------|
| `full` | переиндексация всех активных документов |
| `incremental` | только документы, требующие обновления (по логике worker) |
| `document` | один документ — **обязателен** `document_id` |

**Ответ — `JobOut`:** `job_id`, `mode`, `status` (`pending` → `processing` → `completed`|`failed`), `progress`, `error_message`, timestamps.

**Ошибки:** **400** — `mode=document` без `document_id`.

---

### `GET /api/v1/jobs`

**Назначение:** список всех indexing jobs (новые сверху).

**Ответ:** `{ "items": [ JobOut, ... ] }`

---

### `GET /api/v1/jobs/{job_id}`

**Назначение:** статус и прогресс одной задачи.

**Ответ:** `JobOut`. **404** — не найден.

**Прогресс:**

| Поле | Смысл |
|------|--------|
| `total_documents` / `processed_documents` | документы в job |
| `total_chunks` / `indexed_chunks` | чанки |

---

### `GET /api/v1/knowledge/index/status`

**Назначение:** сводка по jobs без перебора списка.

**Ответ:**

```json
{
  "job_counts_by_status": { "completed": 3, "pending": 0 },
  "latest_job": { ... JobOut или null }
}
```

---

## 4. Промпты (версии в Postgres)

Таблицы: `prompt_templates`, `prompt_versions`.  
При миграции создаются ключи: **`system`**, **`answer_policy`**, **`fallback`**, **`channel_style`**.

> **Важно:** **vendor-support-agent** сейчас читает промпты из **файлов** `prompts/*.md`, а не из этой БД.  
> `PUT` здесь сохраняет версию в оркестраторе; чтобы агент использовал текст, нужна синхронизация в файлы/образ агента (или будущая доработка кода).

---

### `GET /api/v1/prompts`

**Назначение:** список шаблонов с номером последней версии.

**Ответ:**

```json
{
  "items": [
    { "prompt_key": "system", "description": "...", "latest_version": 2 }
  ]
}
```

---

### `GET /api/v1/prompts/{prompt_key}`

**Назначение:** текст **последней** версии промпта.

**Ответ:**

```json
{
  "prompt_key": "system",
  "version": 2,
  "content": "...",
  "updated_at": "..."
}
```

**404** — неизвестный `prompt_key` или нет версий.

---

### `PUT /api/v1/prompts/{prompt_key}`

**Назначение:** создать **новую версию** (старые не перезаписываются).

**Тело:** `{ "content": "полный текст промпта" }`

**Ответ:** `PromptOut` с увеличенным `version`.

**404** — `prompt_key` не зарегистрирован в `prompt_templates`.

---

### `GET /api/v1/prompts/{prompt_key}/versions`

**Назначение:** история версий (без полного `content` в списке).

**Ответ:**

```json
{
  "items": [
    { "id": "pv_...", "version": 2, "created_at": "..." }
  ]
}
```

Сортировка: от новых к старым.

---

## 5. Реестр агентов (MVP)

Префикс: **`/api/v1/agents`**.  
Сейчас **заглушка**: один агент `vendor-support-agent`, статус не опрашивается из health агента автоматически.

---

### `GET /api/v1/agents`

**Назначение:** список зарегистрированных агентов (статический MVP).

**Ответ:**

```json
{
  "items": [
    {
      "agent_id": "vendor-support-agent",
      "title": "Vendor support",
      "status": "unknown"
    }
  ]
}
```

---

### `GET /api/v1/agents/{agent_id}`

**Назначение:** карточка агента.

**Ответ:** `agent_id`, `title`, `metadata`.  
**404** — если `agent_id` не `vendor-support-agent`.

---

### `GET /api/v1/agents/{agent_id}/status`

**Назначение:** статус агента (MVP: не подключён heartbeat).

**Ответ:** `{"agent_id": "...", "status": "unknown", "detail": "MVP: status polling not wired yet"}`

Для реальной проверки агента используйте **`GET /api/v1/infrastructure/status`** → `vendor_support_agent`.

---

## 6. Логи и аудит

---

### `GET /api/v1/logs/runtime`

**Назначение:** последние записи **`runtime_agent_logs`** (технические payload с runtime-агента).

**Query:** `limit` (1–500, по умолчанию 50).

**Ответ:**

```json
{
  "items": [
    {
      "id": "...",
      "conversation_id": "...",
      "payload": {},
      "created_at": "..."
    }
  ]
}
```

Диалоги и сообщения пользователей — через **operator API агента**, не здесь.

---

### `GET /api/v1/logs/indexing`

**Назначение:** заглушка MVP.

**Ответ:** `{"items": [], "note": "MVP: use idx_job_events / jobs API for indexing logs"}`

---

### `GET /api/v1/audit/events`

**Назначение:** заглушка MVP (таблица `audit_events` не реализована).

**Ответ:** `{"items": [], "note": "MVP: audit_events table not implemented yet"}`

---

## Сводная таблица путей

| Метод | Путь | Группа |
|-------|------|--------|
| GET | `/api/v1/health` | служебные |
| GET | `/api/v1/status` | служебные |
| GET | `/api/v1/infrastructure/status` | служебные |
| GET | `/docs`, `/redoc`, `/openapi.json` | служебные |
| GET | `/api/v1/knowledge/documents` | знания |
| POST | `/api/v1/knowledge/documents` | знания |
| GET | `/api/v1/knowledge/documents/{id}` | знания |
| PATCH | `/api/v1/knowledge/documents/{id}` | знания |
| DELETE | `/api/v1/knowledge/documents/{id}` | знания |
| POST | `/api/v1/knowledge/reindex` | индексация |
| GET | `/api/v1/knowledge/index/status` | индексация |
| GET | `/api/v1/jobs` | индексация |
| GET | `/api/v1/jobs/{job_id}` | индексация |
| GET | `/api/v1/prompts` | промпты |
| GET | `/api/v1/prompts/{key}` | промпты |
| PUT | `/api/v1/prompts/{key}` | промпты |
| GET | `/api/v1/prompts/{key}/versions` | промпты |
| GET | `/api/v1/agents` | агенты |
| GET | `/api/v1/agents/{agent_id}` | агенты |
| GET | `/api/v1/agents/{agent_id}/status` | агенты |
| GET | `/api/v1/logs/runtime` | логи |
| GET | `/api/v1/logs/indexing` | логи (stub) |
| GET | `/api/v1/audit/events` | аудит (stub) |

---

## Типовой сценарий «знания работают»

1. `POST /api/v1/knowledge/documents` — загрузить DOCX/MD.  
2. `POST /api/v1/knowledge/reindex` с `"mode": "full"`.  
3. `GET /api/v1/jobs/{job_id}` — дождаться `status: "completed"`.  
4. Проверить агента: `POST http://agent:8010/api/v1/widget/invoke` (см. ENDPOINTS агента).

---

## Данные оркестратора (не HTTP)

| Хранилище | Назначение |
|-----------|------------|
| **Postgres** | документы, версии, чанки, jobs, промпты, runtime-логи (чтение) |
| **Qdrant** | векторный индекс (запись worker) |
| **Redis** | очередь RQ |
| **Диск `storage/knowledge/`** | оригиналы загруженных файлов |

**Runtime-чаты** (`runtime_conversations`, `runtime_messages`) пишет **агент**; оркестратор может читать логи через `/logs/runtime`, управление чатами — только у агента.
