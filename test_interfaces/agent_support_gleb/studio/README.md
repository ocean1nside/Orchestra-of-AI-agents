# Agent Support Studio

Единый тестовый интерфейс для **vendor-support-agent** и **orchestrator-api**: виджет, диалоги оператора, база знаний, промпты, статус инфраструктуры.

Порт по умолчанию: **8790**.

## Локально

```bash
cd test_interfaces/agent_support_gleb/studio
npm install
cp .env.example .env.local
# заполнить WIDGET_API_KEY, OPERATOR_API_KEY, ORCHESTRATOR_API_KEY
npm start
```

Открыть http://127.0.0.1:8790

## Docker (dev)

Из корня репозитория:

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build test-ui-studio
```

Ключи подхватываются из `apps/agents/vendor-support-agent/.env` и `apps/orchestrator-api/.env`.
