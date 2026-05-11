from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.llm_client import complete_chat
from vendor_support_agent.core.prompt_builder import build_system_prompt, build_user_prompt
from vendor_support_agent.core.rag_service import retrieve
from vendor_support_agent.core.settings import get_settings
from vendor_support_agent.db.models.runtime import RuntimeAgentLog, RuntimeConversation, RuntimeMessage
from vendor_support_agent.db.session import SessionLocal
from vendor_support_agent.schemas.invoke import InvokeRequest, InvokeResponse, InvokeResponseMeta, SourceItem


def _conversation_pk(external_id: str) -> str:
    ext = external_id.strip()
    if len(ext) <= 64:
        return ext
    return "cc_" + hashlib.sha256(ext.encode("utf-8")).hexdigest()[:61]


class AgentEngine:
    async def invoke(self, req: InvokeRequest) -> InvokeResponse:
        settings = get_settings()
        conv_id = _conversation_pk(req.conversation_id)

        async with SessionLocal() as db:
            await self._persist_turn(db, conv_id=conv_id, req=req)

        async with SessionLocal() as db:
            chunks = await retrieve(db, query=req.message, limit=5, settings=settings)

        system = build_system_prompt()
        user_prompt = build_user_prompt(user_message=req.message, chunks=chunks)
        answer = await complete_chat(system=system, user=user_prompt, settings=settings)

        confidence = min(1.0, max(0.0, sum(c.score for c in chunks) / max(1, len(chunks))))
        needs_human = len(chunks) == 0 or confidence < 0.25

        sources = [
            SourceItem(document_id=c.document_id, chunk_id=c.chunk_id, title=c.title) for c in chunks
        ]

        async with SessionLocal() as db:
            await self._persist_assistant(
                db,
                conv_id=conv_id,
                req=req,
                answer=answer,
                sources=sources,
                confidence=confidence,
                needs_human=needs_human,
            )

        return InvokeResponse(
            answer=answer,
            sources=sources,
            meta=InvokeResponseMeta(confidence=confidence, needs_human=needs_human),
        )

    async def _persist_turn(self, db: AsyncSession, *, conv_id: str, req: InvokeRequest) -> None:
        existing = (await db.execute(select(RuntimeConversation).where(RuntimeConversation.id == conv_id))).scalar_one_or_none()
        if existing is None:
            db.add(
                RuntimeConversation(
                    id=conv_id,
                    channel=req.channel,
                    user_id=req.user_id,
                    created_at=datetime.utcnow(),
                )
            )

        db.add(
            RuntimeMessage(
                id=f"msg_{uuid4().hex}",
                conversation_id=conv_id,
                role="user",
                content=req.message,
                created_at=datetime.utcnow(),
            )
        )
        await db.commit()

    async def _persist_assistant(
        self,
        db: AsyncSession,
        *,
        conv_id: str,
        req: InvokeRequest,
        answer: str,
        sources: list[SourceItem],
        confidence: float,
        needs_human: bool,
    ) -> None:
        db.add(
            RuntimeMessage(
                id=f"msg_{uuid4().hex}",
                conversation_id=conv_id,
                role="assistant",
                content=answer,
                created_at=datetime.utcnow(),
            )
        )
        db.add(
            RuntimeAgentLog(
                id=f"log_{uuid4().hex}",
                conversation_id=conv_id,
                payload={
                    "channel": req.channel,
                    "user_id": req.user_id,
                    "sources": [s.model_dump() for s in sources],
                    "confidence": confidence,
                    "needs_human": needs_human,
                    "settings": {"embed_provider": get_settings().embed_provider, "llm_model": get_settings().llm_model},
                },
                created_at=datetime.utcnow(),
            )
        )
        await db.commit()
