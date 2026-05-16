# Console — единый тест‑интерфейс

Полноценная тестовая консоль поверх **orchestrator-api** и **vendor-support-agent**. В одном UI собраны:

- виджет (канал `widget` → `POST /api/v1/widget/invoke`),
- база знаний (документы оркестратора),
- промпты оркестратора,
- операторские чаты (operator API агента).

Сервис работает на **одном порту** и отдаёт SPA:

- `/` — главная страница,
- `/widjet` — та же страница, сразу с фокусом на виджет,
- `/agents` — та же страница, с фокусом на вкладки агента.

## Требования

- Node.js 18+
- Запущенный Docker‑стек из `orkester_gleba` (минимум оркестратор + агент)

## Настройка

```bash
cd console
copy .env.example .env.local
```

Отредактируйте `.env.local`:

- `AGENT_URL` — база агента (по умолчанию `http://127.0.0.1:8010`)
- `ORCHESTRATOR_URL` — база оркестратора (по умолчанию `http://127.0.0.1:8000`)
- `ORCHESTRATOR_API_KEY` — `API_KEY_DEV` из `apps/orchestrator-api/.env`
- `WIDGET_API_KEY` — `WIDGET_API_KEY` агента
- `OPERATOR_API_KEY` — `OPERATOR_API_KEY` агента (если пустой, можно использовать тот же, что и `WIDGET_API_KEY`)
- `PORT` — порт UI+proxy (по умолчанию **8790**)

## Запуск

```bash
npm install
npm start
```

Откройте в браузере: `http://127.0.0.1:8790` (или ваш `PORT`).

## Используемые эндпоинты

### Агент (`vendor-support-agent`, `AGENT_URL`)

- **Виджет**
  - `POST /api/v1/widget/invoke` — тело `InvokeRequest` (`channel: "widget"`, `conversation_id`, `user_id`, `message`, `context`), заголовок `Authorization: Bearer WIDGET_API_KEY`.
- **Operator API (чаты)**
  - `GET /api/v1/operator/conversations`
  - `GET /api/v1/operator/conversations/{conversation_id}`
  - `GET /api/v1/operator/conversations/{conversation_id}/messages`
  - `POST /api/v1/operator/conversations/{conversation_id}/reply`
  - `POST /api/v1/operator/conversations/{conversation_id}/control`

### Оркестратор (`orchestrator-api`, `ORCHESTRATOR_URL`)

Все вызовы идут с заголовками:

- `X-Api-Key: ORCHESTRATOR_API_KEY`
- `Authorization: Bearer ORCHESTRATOR_API_KEY`

Используемые пути:

- **Знания**
  - `GET /api/v1/knowledge/documents` — список документов.
  - `GET /api/v1/knowledge/documents/{document_id}` — карточка документа (в демо содержимое режется на «чанки» на клиенте для превью; в бою можно заменить на реальные чанки из своей БД/Qdrant).
  - `POST /api/v1/knowledge/documents` (JSON‑вариант) — создание документа:
    - `{ "title": "...", "content": "plain/markdown", "metadata": {}, "auto_index": false }`.
- **Промпты**
  - `GET /api/v1/prompts/{prompt_key}` — получение актуальной версии (используется поле `content`).
  - `PUT /api/v1/prompts/{prompt_key}` — сохранение новой версии: `{ "content": "…" }`.

## Поведение UI (как ориентир для внешней команды)

- **Виджет**
  - Плавающая кнопка в правом нижнем углу.
  - `conversation_id` и `user_id` сохраняются в `localStorage`, чтобы продолжать диалог между перезагрузками.
  - Ответ ассистента отображается вместе со списком источников (`sources.title`).

- **Вкладка Chats**
  - Список диалогов с опросом `GET /api/v1/operator/conversations` каждые 5 c.
  - При выборе чата — опрос `GET .../messages` каждые 2 c.
  - Кнопка «Отправить» → `POST .../reply`.
  - Кнопки «ИИ» / «Менеджер» → `POST .../control` с `{"holder":"ai"|"human"}`.

- **Вкладка Knowledge**
  - Список документов оркестратора, выбор документа.
  - При выборе — загрузка содержимого и разделение на виртуальные «чанки» фиксированного размера (для наглядности).
  - Форма создания нового документа через JSON‑вариант `POST /api/v1/knowledge/documents`.

- **Вкладка Prompts**
  - Поле `prompt_key`, кнопка «Загрузить» (`GET /api/v1/prompts/{key}`).
  - Текстовое поле `content`, кнопка «Сохранить» (`PUT /api/v1/prompts/{key}`).

Демо не навязывает схему фронтенда — его цель показать, как именно оркестратор и агент ожидают входящие запросы и что отдают в ответ. Внешняя команда может воспроизвести логику у себя, сохранив те же HTTP‑контракты.

