# Тест «виджета» (widget invoke)

Локальная страница с плавающей кнопкой и чатом: сообщения уходят в **vendor-support-agent** через `POST /api/v1/widget/invoke` (канал `widget`). Ключ доступа к агенту хранится только в Node‑прокси.

## Запуск

```bash
cd widjet
copy .env.example .env.local
# заполнить WIDGET_API_KEY (как у vendor-support-agent)
npm install
npm start
```

По умолчанию страница доступна на **http://127.0.0.1:8789** (operator UI из `chats/` слушает **8788**).

## Используемый эндпоинт агента

Node‑прокси (`server.mjs`) принимает:

- `POST /api/widget/invoke` — тело запроса как у настоящего виджета:
  - `channel: "widget"`
  - `conversation_id: string`
  - `user_id: string`
  - `message: string`
  - `context: object` (опционально, произвольный JSON)

И проксирует его в **vendor-support-agent**:

- `POST /api/v1/widget/invoke` c заголовком `Authorization: Bearer WIDGET_API_KEY`.

Ответ от агента (структура `InvokeResponse`) целиком пробрасывается обратно в браузер и отображается в «пузырях».

## Поведение UI

- **Плавающая кнопка** в правом нижнем углу открывает/закрывает чат.
- `conversation_id` и `user_id` хранятся в `localStorage`, чтобы диалог продолжался между перезагрузками страницы.
- Блок с ответом показывает текст ассистента и список источников (`sources.title`), если они есть.
