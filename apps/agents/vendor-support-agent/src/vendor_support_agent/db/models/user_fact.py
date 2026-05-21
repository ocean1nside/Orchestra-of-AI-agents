from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vendor_support_agent.db.base import Base


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
