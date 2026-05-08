from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
IndexMode = Literal["full", "incremental", "document"]


class ReindexRequest(BaseModel):
    mode: IndexMode
    document_id: str | None = Field(default=None)


class JobProgress(BaseModel):
    total_documents: int = 0
    processed_documents: int = 0
    total_chunks: int = 0
    indexed_chunks: int = 0


class JobOut(BaseModel):
    job_id: str
    mode: IndexMode
    status: JobStatus
    document_id: str | None = None
    progress: JobProgress
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobOut]

