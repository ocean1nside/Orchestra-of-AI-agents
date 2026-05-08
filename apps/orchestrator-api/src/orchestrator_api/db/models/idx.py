from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from orchestrator_api.db.base import Base


class IdxJob(Base):
    __tablename__ = "idx_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"job_{uuid4().hex}")
    mode: Mapped[str] = mapped_column(String(32))  # full|incremental|document
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    processed_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    indexed_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class IdxJobEvent(Base):
    __tablename__ = "idx_job_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"jobe_{uuid4().hex}")
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

