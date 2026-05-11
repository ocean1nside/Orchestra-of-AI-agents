from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

from vendor_support_agent.core.agent_engine import AgentEngine
from vendor_support_agent.core.max_outbound import send_message_text
from vendor_support_agent.core.settings import get_settings
from vendor_support_agent.schemas.invoke import InvokeRequest, InvokeResponse
from vendor_support_agent.schemas.max_messenger import MaxUpdate

logger = logging.getLogger(__name__)

router = APIRouter()
_engine = AgentEngine()


@router.post("/api/v1/max/webhook")
async def max_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None, alias="X-Max-Bot-Api-Secret"),
) -> dict[str, bool]:
    """
    Webhook MAX: тело — объект Update (см. dev.max.ru docs-api/objects/Update).
    Ответ пользователю — POST /messages на platform-api.max.ru.
    """
    settings = get_settings()
    token = settings.max_bot_token.strip()
    if not token:
        raise HTTPException(status_code=503, detail="MAX_BOT_TOKEN is not configured")

    secret = (settings.max_webhook_secret or "").strip()
    if secret and x_max_bot_api_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid MAX webhook secret")

    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    try:
        upd = MaxUpdate.model_validate(body)
    except ValidationError:
        return {"ok": True}

    if upd.update_type not in ("message_created", "message_edited"):
        return {"ok": True}

    msg = upd.message
    if not msg or not msg.body:
        return {"ok": True}

    if msg.sender and msg.sender.is_bot:
        return {"ok": True}

    text = (msg.body.text or "").strip()
    if not text:
        return {"ok": True}

    chat_id = msg.recipient.chat_id
    if chat_id is None:
        return {"ok": True}

    uid = str(msg.sender.user_id) if msg.sender else str(chat_id)
    req = InvokeRequest(
        channel="max",
        conversation_id=str(chat_id),
        user_id=uid,
        message=text,
    )

    try:
        resp = await _engine.invoke(req)
        await send_message_text(
            access_token=token,
            chat_id=chat_id,
            text=resp.answer,
            api_base=settings.max_api_base,
        )
    except Exception:
        logger.exception("max webhook handling failed")
        try:
            await send_message_text(
                access_token=token,
                chat_id=chat_id,
                text="Не удалось обработать сообщение. Попробуйте позже.",
                api_base=settings.max_api_base,
            )
        except Exception:
            logger.exception("max sendMessage after error failed")

    return {"ok": True}


@router.post("/api/v1/max/invoke", response_model=InvokeResponse)
async def max_invoke(req: InvokeRequest) -> InvokeResponse:
    """Ручной вызов в формате InvokeRequest (без объекта Update MAX)."""
    return await _engine.invoke(req)
