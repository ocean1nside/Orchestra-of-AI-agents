"""Список диалогов и доставка ответа оператора в Telegram / MAX / запись для виджета."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.max_outbound import send_message_text
from vendor_support_agent.core.settings import Settings
from vendor_support_agent.core.telegram_outbound import send_message
from vendor_support_agent.db.models.runtime import RuntimeConversation, RuntimeMessage


async def list_conversations_with_last_message(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
    channel: str | None,
    include_hidden: bool = False,
) -> list[tuple[RuntimeConversation, datetime | None]]:
    lm = func.max(RuntimeMessage.created_at).label("last_msg_at")
    subq = select(RuntimeMessage.conversation_id, lm).group_by(RuntimeMessage.conversation_id).subquery()
    stmt = (
        select(RuntimeConversation, subq.c.last_msg_at)
        .outerjoin(subq, RuntimeConversation.id == subq.c.conversation_id)
        .order_by(desc(subq.c.last_msg_at).nulls_last(), desc(RuntimeConversation.created_at))
        .limit(limit)
        .offset(offset)
    )
    if channel:
        stmt = stmt.where(RuntimeConversation.channel == channel)
    if not include_hidden:
        stmt = stmt.where(RuntimeConversation.hidden.is_(False))
    rows = (await db.execute(stmt)).all()
    return [(c, ts) for c, ts in rows]


async def get_conversation(db: AsyncSession, *, conversation_id: str) -> RuntimeConversation | None:
    return (
        await db.execute(select(RuntimeConversation).where(RuntimeConversation.id == conversation_id))
    ).scalar_one_or_none()


async def set_conversation_hidden(
    db: AsyncSession, *, conversation_id: str, hidden: bool
) -> RuntimeConversation | None:
    row = (
        await db.execute(select(RuntimeConversation).where(RuntimeConversation.id == conversation_id))
    ).scalar_one_or_none()
    if row is None:
        return None
    row.hidden = hidden
    await db.commit()
    await db.refresh(row)
    return row


async def get_last_message_at(db: AsyncSession, *, conversation_id: str) -> datetime | None:
    stmt = select(func.max(RuntimeMessage.created_at)).where(RuntimeMessage.conversation_id == conversation_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_messages(
    db: AsyncSession, *, conversation_id: str, limit: int = 500
) -> list[RuntimeMessage]:
    stmt = (
        select(RuntimeMessage)
        .where(RuntimeMessage.conversation_id == conversation_id)
        .order_by(RuntimeMessage.created_at.asc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def persist_operator_message(db: AsyncSession, *, conversation_id: str, text: str) -> RuntimeMessage:
    msg = RuntimeMessage(
        id=f"msg_{uuid4().hex}",
        conversation_id=conversation_id,
        role="operator",
        content=text.strip(),
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


def _numeric_chat_id(conversation_id: str) -> int:
    return int(str(conversation_id).strip())


async def deliver_operator_text(
    *,
    settings: Settings,
    channel: str,
    conversation_id: str,
    text: str,
) -> Literal["sent", "stored"]:
    if channel == "widget":
        return "stored"

    if channel == "telegram":
        token = (settings.telegram_bot_token or "").strip()
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        try:
            chat_id = _numeric_chat_id(conversation_id)
        except ValueError as e:
            raise ValueError("Telegram delivery requires numeric conversation_id (chat id)") from e
        await send_message(bot_token=token, chat_id=chat_id, text=text)
        return "sent"

    if channel == "max":
        token = (settings.max_bot_token or "").strip()
        if not token:
            raise ValueError("MAX_BOT_TOKEN is not configured")
        try:
            chat_id = _numeric_chat_id(conversation_id)
        except ValueError as e:
            raise ValueError("MAX delivery requires numeric conversation_id (chat id)") from e
        await send_message_text(
            access_token=token,
            chat_id=chat_id,
            text=text,
            api_base=settings.max_api_base,
        )
        return "sent"

    raise ValueError(f"Unknown channel: {channel}")
