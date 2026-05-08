# Architecture

## Services

- **`orchestrator-api`**: control plane для управления знаниями (документы/чанки), индексацией, промтами, статусами, логами и аудитом.
- **`vendor-support-agent`**: runtime-агент, который отвечает пользователям из каналов (widget/Telegram/MAX).
- **`indexing-worker`**: фоновые задачи индексации (extract → chunk → embed → Postgres → Qdrant).
- **Postgres**: источник истины для документов/чанков/промтов/статусов/логов.
- **Qdrant**: векторный поиск по чанкам (`knowledge_chunks`).
- **Redis**: очередь/брокер для фоновых задач.

## Control plane vs Runtime plane

### Control plane (`orchestrator-api`)

Управляет:

- загрузкой и хранением документов;
- постановкой задач индексации;
- состоянием индексации;
- версионированием промтов;
- аудитом и тех. логами.

### Runtime plane (`vendor-support-agent`)

Обрабатывает пользовательские сообщения:

```text
incoming -> normalize -> search Qdrant -> load chunks from Postgres -> build prompt -> call LLM -> save logs -> response
```

Оркестр **не** участвует в runtime-цепочке.

## Decisions (фиксируем по мере развития)

- **Background queue**: TBD (Celery vs RQ). Выбор будет зафиксирован при реализации `indexing-worker`.
- **LLM provider abstraction**: интерфейс клиента должен позволять переключать провайдера без переписывания бизнес-логики.

