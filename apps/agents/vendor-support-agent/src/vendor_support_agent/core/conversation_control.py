"""Кто ведёт диалог: ai или human (менеджер)."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.db.models.runtime import RuntimeConversation

ControlHolder = Literal["ai", "human"]


def _normalize_holder(raw: str | None) -> ControlHolder:
    if not raw:
        return "ai"
    h = raw.strip().lower()
    return "human" if h == "human" else "ai"


async def get_control_holder(db: AsyncSession, *, conversation_id: str) -> ControlHolder:
    row = (
        await db.execute(select(RuntimeConversation).where(RuntimeConversation.id == conversation_id))
    ).scalar_one_or_none()
    if row is None:
        return "ai"
    return _normalize_holder(getattr(row, "conversation_holder", None))


async def set_control_holder(
    db: AsyncSession, *, conversation_id: str, holder: ControlHolder
) -> RuntimeConversation | None:
    row = (
        await db.execute(select(RuntimeConversation).where(RuntimeConversation.id == conversation_id))
    ).scalar_one_or_none()
    if row is None:
        return None
    row.conversation_holder = holder
    await db.commit()
    await db.refresh(row)
    return row
