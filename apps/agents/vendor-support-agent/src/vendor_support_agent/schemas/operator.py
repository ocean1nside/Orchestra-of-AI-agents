from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ControlHolder = Literal["ai", "human"]


class OperatorConversationItem(BaseModel):
    """Один диалог во всех каналах (id совпадает с conversation_id в invoke/webhook)."""

    id: str
    channel: Literal["widget", "telegram", "max"]
    user_id: str
    created_at: datetime
    last_message_at: datetime | None = None
    conversation_holder: ControlHolder = "ai"
    hidden: bool = False


class OperatorConversationListResponse(BaseModel):
    items: list[OperatorConversationItem]
    limit: int
    offset: int


class OperatorConversationDetail(OperatorConversationItem):
    pass


class OperatorMessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class OperatorMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[OperatorMessageItem]


class OperatorReplyBody(BaseModel):
    text: str = Field(min_length=1, max_length=12000)


class OperatorReplyResponse(BaseModel):
    ok: bool = True
    conversation_id: str
    channel: Literal["widget", "telegram", "max"]
    delivery: Literal["sent", "stored"]
    """sent — сообщение ушло в Telegram/MAX; stored — только БД (виджет: заберите через GET messages)."""


class OperatorControlBody(BaseModel):
    holder: ControlHolder = Field(description="ai — отвечает агент; human — только оператор (ИИ молчит).")


class OperatorControlResponse(BaseModel):
    ok: bool = True
    conversation_id: str
    conversation_holder: ControlHolder


class OperatorVisibilityBody(BaseModel):
    hidden: bool = Field(description="true — скрыть из списка оператора; false — снова показывать.")


class OperatorVisibilityResponse(BaseModel):
    ok: bool = True
    conversation_id: str
    hidden: bool
