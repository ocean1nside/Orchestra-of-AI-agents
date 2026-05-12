from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Channel = Literal["widget", "telegram", "max"]


class InvokeRequest(BaseModel):
    channel: Channel
    conversation_id: str
    user_id: str
    message: str = Field(min_length=1)
    context: dict[str, Any] | None = None


class SourceItem(BaseModel):
    document_id: str
    chunk_id: str
    title: str


class InvokeResponseMeta(BaseModel):
    confidence: float | None = None
    needs_human: bool = False
    escalated: bool = False
    escalation_reasons: list[str] = Field(default_factory=list)
    # Кто ведёт диалог в БД; ai_muted=True — ответ ИИ не генерировался (контроль у human).
    conversation_holder: Literal["ai", "human"] = "ai"
    ai_muted: bool = False


class InvokeResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    answer: str
    sources: list[SourceItem] = []
    meta: InvokeResponseMeta = InvokeResponseMeta()

