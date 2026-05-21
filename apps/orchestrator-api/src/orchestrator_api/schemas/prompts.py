from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PromptListItem(BaseModel):
    prompt_key: str
    description: str
    latest_version: int


class PromptListResponse(BaseModel):
    items: list[PromptListItem]


class PromptOut(BaseModel):
    prompt_key: str
    version: int
    content: str
    updated_at: datetime | None = None


class PromptPutBody(BaseModel):
    content: str = Field(min_length=1)


class PromptCreateBody(BaseModel):
    """Новый блок инструкций (ключ латиницей: system, rules_escalation)."""

    prompt_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(default="", max_length=500)
    content: str = Field(min_length=1)


class PromptVersionItem(BaseModel):
    id: str
    version: int
    created_at: datetime | None = None


class PromptVersionsResponse(BaseModel):
    items: list[PromptVersionItem]
