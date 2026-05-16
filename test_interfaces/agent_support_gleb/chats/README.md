# Chats — тестовая консоль operator API

Двухколоночный UI: слева список чатов и карточка выбранного, справа переписка и отправка ответа оператором. Запросы к агенту идут через небольшой **Node proxy** (ключ operator API не светится в браузере).

## Требования

- Node.js 18+
- Запущенный **vendor-support-agent** (например `http://127.0.0.1:8010`)
- В `.env` агента задан **`OPERATOR_API_KEY`** или **`WIDGET_API_KEY`** (тот же ключ подставьте сюда)

## Настройка

```bash
cd chats
copy .env.example .env.local
```

Отредактируйте `.env.local`:

- `AGENT_URL` — база агента (по умолчанию `http://127.0.0.1:8010`)
- `OPERATOR_API_KEY` — тот же ключ, что для `GET/POST /api/v1/operator/...`
- `PORT` — порт UI+proxy (по умолчанию **8788**)

## Запуск

```bash
npm install
npm start
```

Откройте в браузере: `http://127.0.0.1:8788` (или ваш `PORT`).

## Используемые эндпоинты агента

Через прокси `server.mjs` идут запросы в **vendor-support-agent**:

- `GET /api/v1/operator/conversations` — список runtime‑диалогов (все каналы), с `conversation_holder`.
- `GET /api/v1/operator/conversations/{conversation_id}` — карточка одного диалога.
- `GET /api/v1/operator/conversations/{conversation_id}/messages` — лента сообщений (`user` / `assistant` / `operator`).
- `POST /api/v1/operator/conversations/{conversation_id}/reply` — ответ оператора (отправка в Telegram/MAX или только в БД для `widget`).
- `POST /api/v1/operator/conversations/{conversation_id}/control` — переключение, кто отвечает: `{"holder":"ai"|"human"}`.

## Поведение UI

- **Список чатов** — опрос `GET /api/v1/operator/conversations` каждые 5 с.
- **Сообщения** — при выборе чата опрос `GET .../messages` каждые 2 с.
- **Отправить** — `POST .../reply`; ответ оператора появляется и в UI, и в канале (если это Telegram/MAX).
- **ИИ / Менеджер** — `POST .../control`. При `holder="human"` агент не вызывает LLM на новые сообщения пользователя в этом чате (вебхуки Telegram/MAX не шлют ответ бота, в метаданных `ai_muted=true`).

Важно: после добавления поля `conversation_holder` в БД нужно пересобрать/перезапустить контейнеры **orchestrator-api** (Alembic) и **vendor-support-agent**, чтобы операторская консоль корректно работала с новой схемой.
