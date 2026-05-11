"""Фрагменты схемы MAX Update (message_created / message_edited). extra=ignore — поля платформы могут расширяться."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MaxUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: int
    is_bot: bool | None = False


class MaxRecipient(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chat_id: int | None = None


class MaxMessageBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str | None = None


class MaxMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: MaxUser | None = None
    recipient: MaxRecipient
    body: MaxMessageBody | None = None


class MaxUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_type: str
    message: MaxMessage | None = None
