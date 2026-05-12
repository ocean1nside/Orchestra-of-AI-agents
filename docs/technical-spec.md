# Technical spec (consolidated)

Оглавление документации репозитория: [`README.md`](README.md).

Этот документ — **консолидированная** версия требований для MVP.

Источники:

- `cursor_prompt_vendor_support_orchestrator.md`
- `technical_spec_vendor_support_orchestrator.md`

## Summary

Нужно разработать backend-only окружение:

- `orchestrator-api` — management/control API для документов, индексации, промтов, статусов, логов, health;
- `vendor-support-agent` — runtime-агент, который принимает сообщения из каналов и отвечает по базе знаний через RAG (Qdrant + Postgres) и LLM.

## Non-goals (MVP)

Не делаем:

- frontend/админку/личные кабинеты;
- Vendors API / управление вендорами;
- user/role/permission management;
- отдельные базы знаний и таблицы под каждого вендора;
- runtime-маршрутизацию запросов через оркестр;
- Kubernetes.

## Architecture rules

- Оркестр — **control plane**, не runtime-proxy.
- Агент имеет **прямой** доступ к Postgres и Qdrant.
- Один движок (`AgentEngine`) для всех каналов.
- Одна общая Qdrant collection: `knowledge_chunks`.

## API (MVP)

Полный перечень методов, путей, тел запросов, заголовков и примеров: **[`http-api-reference.md`](http-api-reference.md)**.

Кратко: **orchestrator-api** — управление документами, индексацией, промтами, jobs, логами, health; **vendor-support-agent** — invoke/widget/Telegram/MAX webhooks, ручные invoke, health, **operator API** (список чатов и ответ оператора).

## Data model (high-level)

Минимальные таблицы (см. первичную спеку):

- `orch_settings`, `orch_api_keys`
- `agent_registry`, `agent_status`
- `kb_documents`, `kb_document_versions`, `kb_chunks`
- `idx_jobs`, `idx_job_events`
- `prompt_templates`, `prompt_versions`
- `runtime_conversations`, `runtime_messages`, `runtime_agent_logs`
- `channel_*`
- `audit_events`

