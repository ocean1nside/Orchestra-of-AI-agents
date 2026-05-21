# Agent Support Studio (доступ)

**URL:** https://212-67-10-140.sslip.io/studio/

Логин и пароль — в корневом `.env`: `STUDIO_HTTP_USER`, `STUDIO_HTTP_PASSWORD`.

Порт 8790 только на `127.0.0.1`; снаружи — nginx (TLS) + HTTP Basic Auth (диалог браузера).

**База знаний:** «+ Добавить документ» (модалка) и «Как подготовить файл». Подробный гайд: [`docs/handover/knowledge-documents-guide.md`](../docs/handover/knowledge-documents-guide.md).

**Эскалация:** в `apps/agents/vendor-support-agent/.env` задайте `ESCALATION_CONTEXT_BASE_URL=https://212-67-10-140.sslip.io` — в группу придёт ссылка вида  
`https://212-67-10-140.sslip.io/studio/?view=chats&conversation_id=<id>` (откроется нужный диалог в Studio).
