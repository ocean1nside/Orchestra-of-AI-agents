"""Исходящие вызовы API MAX (ответ пользователю в чат)."""

from __future__ import annotations

import httpx

DEFAULT_MAX_API_BASE = "https://platform-api.max.ru"


async def send_message_text(
    *,
    access_token: str,
    chat_id: int,
    text: str,
    api_base: str = DEFAULT_MAX_API_BASE,
) -> None:
    """POST /messages?chat_id=… см. https://dev.max.ru/docs-api/methods/POST/messages"""
    max_len = 4000
    payload = text if len(text) <= max_len else text[: max_len - 20] + "\n…(обрезано)"
    base = api_base.rstrip("/")
    url = f"{base}/messages"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            params={"chat_id": chat_id},
            headers={
                "Authorization": access_token,
                "Content-Type": "application/json",
            },
            json={"text": payload},
        )
        r.raise_for_status()
