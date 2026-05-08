# Technical spec (consolidated)

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

### Orchestrator API

- Documents:
  - `GET /api/v1/knowledge/documents`
  - `POST /api/v1/knowledge/documents`
  - `GET /api/v1/knowledge/documents/{document_id}`
  - `PATCH /api/v1/knowledge/documents/{document_id}`
  - `DELETE /api/v1/knowledge/documents/{document_id}`
- Indexing:
  - `POST /api/v1/knowledge/reindex`
  - `GET /api/v1/knowledge/index/status`
  - `GET /api/v1/jobs`
  - `GET /api/v1/jobs/{job_id}`
- Prompts:
  - `GET /api/v1/prompts`
  - `GET /api/v1/prompts/{prompt_key}`
  - `PUT /api/v1/prompts/{prompt_key}`
  - `GET /api/v1/prompts/{prompt_key}/versions`
- Agents:
  - `GET /api/v1/agents`
  - `GET /api/v1/agents/{agent_id}`
  - `GET /api/v1/agents/{agent_id}/status`
- Health:
  - `GET /api/v1/health`
  - `GET /api/v1/status`
  - `GET /api/v1/infrastructure/status`
- Logs:
  - `GET /api/v1/logs/runtime`
  - `GET /api/v1/logs/indexing`
  - `GET /api/v1/audit/events`

### Vendor Support Agent API

- `GET /health`
- `GET /metadata`
- `POST /api/v1/invoke`
- `POST /api/v1/widget/invoke`
- `POST /api/v1/telegram/webhook`
- `POST /api/v1/max/webhook`

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

