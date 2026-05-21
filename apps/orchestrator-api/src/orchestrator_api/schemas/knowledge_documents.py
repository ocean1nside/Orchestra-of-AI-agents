from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal["uploaded", "pending_index", "indexing", "indexed", "failed", "deleted"]


class DocumentCreateJson(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None
    auto_index: bool = False


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    metadata: dict[str, Any] | None = None


class DocumentOut(BaseModel):
    document_id: str
    title: str
    status: DocumentStatus
    metadata: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentCreateResponse(BaseModel):
    status: DocumentStatus
    document_id: str
    indexing_status: DocumentStatus


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]


class ChunkOut(BaseModel):
    chunk_id: str
    chunk_index: int
    char_count: int
    content: str
    metadata: dict[str, Any]


class DocumentChunksResponse(BaseModel):
    document_id: str
    title: str
    status: DocumentStatus
    total_chunks: int
    items: list[ChunkOut]


class NormalizeRequest(BaseModel):
    content: str = Field(min_length=1, max_length=200_000)
    title: str | None = Field(default=None, max_length=512)


class NormalizeResponse(BaseModel):
    markdown: str
    model: str
    char_count: int


class PrepareAiResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    job_id: str | None = None
    model: str
    char_count: int
    message: str

