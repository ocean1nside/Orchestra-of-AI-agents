from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from orchestrator_api.db.base import Base


class RuntimeConversation(Base):
    __tablename__ = "runtime_conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    conversation_holder: Mapped[str] = mapped_column(String(16), default="ai", server_default="ai")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class RuntimeMessage(Base):
    __tablename__ = "runtime_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeUserFact(Base):
    __tablename__ = "runtime_user_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str] = mapped_column(String(256))
    fact_key: Mapped[str] = mapped_column(String(64))
    fact_value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="extracted")
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeAgentLog(Base):
    __tablename__ = "runtime_agent_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
