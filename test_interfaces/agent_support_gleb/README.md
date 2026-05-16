# Тестовые интерфейсы `agent_support_gleb`

Мини-приложения для ручной проверки интеграций с **vendor-support-agent** (и при необходимости с оркестратором). Каждое живёт в своей подпапке и слушает **свой порт**, чтобы можно было запускать параллельно.

## Структура

| Папка | Порт по умолчанию | Назначение |
|-------|-------------------|------------|
| [`chats/`](chats/) | **8788** | Тестовая консоль **operator API**: список диалогов, лента сообщений, ответы оператора, переключение «ИИ / менеджер» |
| [`widjet/`](widjet/) | **8789** | Тест **виджета**: плавающая кнопка на странице, отправка сообщений в `POST /api/v1/widget/invoke` |
| [`console/`](console/) | **8790** | Полноценный тест‑интерфейс: виджет + управление знаниями, промптами и чатами через оркестратор и агента |

Добавляя новые интерфейсы, задайте другой `PORT` в их `.env` / `package.json` и допишите строку в эту таблицу.

## Общие принципы

- Все приложения работают поверх **runtime-агента** (`vendor-support-agent`), а не через оркестратор.
- Ключи доступа (`OPERATOR_API_KEY`, `WIDGET_API_KEY`) хранятся только в **Node‑прокси** и не попадают в браузер.
- Внутренние форматы и эндпоинты:
  - operator UI (`chats/`) → `GET/POST /api/v1/operator/...`
  - виджет (`widjet/`) → `POST /api/v1/widget/invoke` c телом `InvokeRequest` (`channel="widget"`, `conversation_id`, `user_id`, `message`, `context`).

Подробности по настройке и запуску — в `README.md` внутри каждой подпапки.

## Запуск через Docker (рекомендуется)

Из **корня репозитория** (нужны `.env` в корне и в `apps/...`, см. корневой `README.md`):

```bash
docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build
```

Тестовые UI поднимаются вместе с **vendor-support-agent** и **orchestrator-api**:

| URL | Сервис compose |
|-----|----------------|
| http://localhost:8788 | `test-ui-chats` |
| http://localhost:8789 | `test-ui-widjet` |
| http://localhost:8790 | `test-ui-console` |

Ключи `WIDGET_API_KEY` / `OPERATOR_API_KEY` / `API_KEY_DEV` подхватываются из `.env` агента и оркестратора (файлы не коммитятся).

## Локально без Docker

В каждой подпапке: `npm install`, скопировать `.env.example` → `.env.local`, `npm start`.
