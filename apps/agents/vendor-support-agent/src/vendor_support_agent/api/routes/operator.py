"""API консоли оператора: список чатов (все каналы), история, ответ пользователю."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from vendor_support_agent.api.dependencies import verify_operator_api_key
from vendor_support_agent.core.conversation_control import set_control_holder
from vendor_support_agent.core.operator_service import (
    deliver_operator_text,
    get_conversation,
    get_last_message_at,
    list_conversations_with_last_message,
    list_messages,
    persist_operator_message,
    set_conversation_hidden,
)
from vendor_support_agent.core.settings import get_settings
from vendor_support_agent.core.user_memory import load_user_facts
from vendor_support_agent.db.session import SessionLocal
from vendor_support_agent.schemas.invoke import Channel
from vendor_support_agent.schemas.operator import (
    ControlHolder,
    OperatorControlBody,
    OperatorControlResponse,
    OperatorConversationDetail,
    OperatorConversationItem,
    OperatorConversationListResponse,
    OperatorMessageItem,
    OperatorMessagesResponse,
    OperatorReplyBody,
    OperatorReplyResponse,
    OperatorUserFactItem,
    OperatorUserFactsResponse,
    OperatorVisibilityBody,
    OperatorVisibilityResponse,
)

logger = logging.getLogger(__name__)


def _holder_field(conv) -> ControlHolder:
    raw = (getattr(conv, "conversation_holder", None) or "ai").strip().lower()
    return "human" if raw == "human" else "ai"


router = APIRouter(
    prefix="/api/v1/operator",
    tags=["operator"],
    dependencies=[Depends(verify_operator_api_key)],
)


@router.get("/conversations", response_model=OperatorConversationListResponse)
async def operator_list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    channel: Channel | None = Query(default=None),
    include_hidden: bool = Query(default=False),
) -> OperatorConversationListResponse:
    async with SessionLocal() as db:
        rows = await list_conversations_with_last_message(
            db, limit=limit, offset=offset, channel=channel, include_hidden=include_hidden
        )
    items = [
        OperatorConversationItem(
            id=c.id,
            channel=c.channel,  # type: ignore[arg-type]
            user_id=c.user_id,
            created_at=c.created_at,
            last_message_at=lm,
            conversation_holder=_holder_field(c),
            hidden=bool(getattr(c, "hidden", False)),
        )
        for c, lm in rows
    ]
    return OperatorConversationListResponse(items=items, limit=limit, offset=offset)


@router.get("/conversations/{conversation_id}", response_model=OperatorConversationDetail)
async def operator_get_conversation(conversation_id: str) -> OperatorConversationDetail:
    async with SessionLocal() as db:
        c = await get_conversation(db, conversation_id=conversation_id)
        lm = await get_last_message_at(db, conversation_id=conversation_id) if c else None
    if c is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return OperatorConversationDetail(
        id=c.id,
        channel=c.channel,  # type: ignore[arg-type]
        user_id=c.user_id,
        created_at=c.created_at,
        last_message_at=lm,
        conversation_holder=_holder_field(c),
        hidden=bool(getattr(c, "hidden", False)),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=OperatorMessagesResponse)
async def operator_list_messages(
    conversation_id: str,
    limit: int = Query(default=500, ge=1, le=1000),
) -> OperatorMessagesResponse:
    async with SessionLocal() as db:
        c = await get_conversation(db, conversation_id=conversation_id)
        if c is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        msgs = await list_messages(db, conversation_id=conversation_id, limit=limit)
    return OperatorMessagesResponse(
        conversation_id=conversation_id,
        messages=[
            OperatorMessageItem(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in msgs
        ],
    )


@router.post("/conversations/{conversation_id}/reply", response_model=OperatorReplyResponse)
async def operator_reply(conversation_id: str, body: OperatorReplyBody) -> OperatorReplyResponse:
    settings = get_settings()
    text = body.text.strip()
    async with SessionLocal() as db:
        conv = await get_conversation(db, conversation_id=conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        channel = conv.channel

    try:
        delivery = await deliver_operator_text(
            settings=settings,
            channel=channel,
            conversation_id=conversation_id,
            text=text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("operator reply delivery failed conversation_id=%s", conversation_id)
        raise HTTPException(status_code=502, detail="Failed to send message to channel") from None

    async with SessionLocal() as db:
        await persist_operator_message(db, conversation_id=conversation_id, text=text)

    return OperatorReplyResponse(
        ok=True,
        conversation_id=conversation_id,
        channel=channel,  # type: ignore[arg-type]
        delivery=delivery,
    )


@router.post("/conversations/{conversation_id}/control", response_model=OperatorControlResponse)
async def operator_set_control(conversation_id: str, body: OperatorControlBody) -> OperatorControlResponse:
    async with SessionLocal() as db:
        updated = await set_control_holder(db, conversation_id=conversation_id, holder=body.holder)
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return OperatorControlResponse(
        ok=True,
        conversation_id=conversation_id,
        conversation_holder=_holder_field(updated),
    )


@router.get("/conversations/{conversation_id}/user-facts", response_model=OperatorUserFactsResponse)
async def operator_user_facts(conversation_id: str) -> OperatorUserFactsResponse:
    settings = get_settings()
    async with SessionLocal() as db:
        c = await get_conversation(db, conversation_id=conversation_id)
        if c is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if not settings.user_memory_enabled:
            facts = []
        else:
            facts = await load_user_facts(
                db,
                channel=c.channel,
                user_id=c.user_id,
                limit=settings.user_memory_max_facts,
            )
    return OperatorUserFactsResponse(
        conversation_id=conversation_id,
        channel=c.channel,
        user_id=c.user_id,
        items=[
            OperatorUserFactItem(
                fact_key=f.fact_key,
                label=f.label,
                value=f.fact_value,
                updated_at=f.updated_at,
            )
            for f in facts
        ],
    )


@router.post("/conversations/{conversation_id}/visibility", response_model=OperatorVisibilityResponse)
async def operator_set_visibility(
    conversation_id: str, body: OperatorVisibilityBody
) -> OperatorVisibilityResponse:
    async with SessionLocal() as db:
        updated = await set_conversation_hidden(db, conversation_id=conversation_id, hidden=body.hidden)
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return OperatorVisibilityResponse(
        ok=True,
        conversation_id=conversation_id,
        hidden=bool(updated.hidden),
    )
