"""Отправка ответов пользователю в Telegram (Bot API)."""

from __future__ import annotations

import httpx

TELEGRAM_API = "https://api.telegram.org"


def _clip(text: str, max_len: int = 4096) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n…(обрезано)"


async def send_chat_action(*, bot_token: str, chat_id: int, action: str = "typing") -> None:
    """sendChatAction — «печатает» и др.; клиент сбрасывает статус после ответа бота."""
    url = f"{TELEGRAM_API}/bot{bot_token}/sendChatAction"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, json={"chat_id": chat_id, "action": action})
        r.raise_for_status()


async def send_message(*, bot_token: str, chat_id: int, text: str) -> None:
    """Обычное сообщение в чат (sendMessage)."""
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = _clip(text)
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json={"chat_id": chat_id, "text": payload})
        r.raise_for_status()


async def send_message_get_id(*, bot_token: str, chat_id: int, text: str) -> int:
    """sendMessage, возвращает message_id (для editMessageText при стриминге в группах)."""
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = _clip(text)
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json={"chat_id": chat_id, "text": payload})
        r.raise_for_status()
        data = r.json()
    return int(data["result"]["message_id"])


async def edit_message_text(*, bot_token: str, chat_id: int, message_id: int, text: str) -> None:
    url = f"{TELEGRAM_API}/bot{bot_token}/editMessageText"
    payload = _clip(text)
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            url,
            json={"chat_id": chat_id, "message_id": message_id, "text": payload},
        )
        r.raise_for_status()
