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


class PromptVersionItem(BaseModel):
    id: str
    version: int
    created_at: datetime | None = None


class PromptVersionsResponse(BaseModel):
    items: list[PromptVersionItem]
