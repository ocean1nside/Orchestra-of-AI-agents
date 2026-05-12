from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from vendor_support_agent.db.base import Base


class RuntimeConversation(Base):
    __tablename__ = "runtime_conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    # Кто ведёт диалог: ai — отвечает агент; human — только оператор (ИИ не отвечает).
    conversation_holder: Mapped[str] = mapped_column(String(16), default="ai", server_default="ai")
    # Скрыт из списка operator API (мягкое скрытие; строки и сообщения остаются в БД).
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class RuntimeMessage(Base):
    __tablename__ = "runtime_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeAgentLog(Base):
    __tablename__ = "runtime_agent_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
