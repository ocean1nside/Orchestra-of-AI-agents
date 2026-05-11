"""Отправка ответов пользователю в Telegram (Bot API)."""

from __future__ import annotations

import httpx

TELEGRAM_API = "https://api.telegram.org"


async def send_message(*, bot_token: str, chat_id: int, text: str) -> None:
    """sendMessage; текст обрезается до лимита Telegram."""
    max_len = 4096
    payload = text if len(text) <= max_len else text[: max_len - 20] + "\n…(обрезано)"
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            json={"chat_id": chat_id, "text": payload},
        )
        r.raise_for_status()
