from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

from vendor_support_agent.core.agent_engine import AgentEngine
from vendor_support_agent.core.settings import get_settings
from vendor_support_agent.core.telegram_outbound import send_message
from vendor_support_agent.schemas.invoke import InvokeRequest
from vendor_support_agent.schemas.telegram import TelegramUpdate

logger = logging.getLogger(__name__)

router = APIRouter()
_engine = AgentEngine()


@router.post("/api/v1/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, bool]:
    """
    Реальный вебхук Telegram: тело — Update JSON.
    Ответ пользователю уходит через sendMessage (ответ HTTP для Telegram — просто ok).
    """
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN is not configured")

    secret = (settings.telegram_webhook_secret or "").strip()
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    try:
        upd = TelegramUpdate.model_validate(body)
    except ValidationError:
        return {"ok": True}

    msg = upd.message or upd.edited_message
    if not msg or not msg.text or not (text := msg.text.strip()):
        return {"ok": True}

    uid = str(msg.from_user.id) if msg.from_user else str(msg.chat.id)
    req = InvokeRequest(
        channel="telegram",
        conversation_id=str(msg.chat.id),
        user_id=uid,
        message=text,
    )

    try:
        resp = await _engine.invoke(req)
        await send_message(bot_token=token, chat_id=msg.chat.id, text=resp.answer)
    except Exception:
        logger.exception("telegram webhook handling failed")
        try:
            await send_message(
                bot_token=token,
                chat_id=msg.chat.id,
                text="Не удалось обработать сообщение. Попробуйте позже.",
            )
        except Exception:
            logger.exception("telegram sendMessage after error failed")

    return {"ok": True}
