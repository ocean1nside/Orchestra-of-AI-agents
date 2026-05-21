from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.escalation import (
    compute_escalation,
    format_user_facing_answer,
    send_escalation_notification,
)
from vendor_support_agent.core.llm_client import complete_chat, stream_chat
from vendor_support_agent.core.prompt_builder import build_system_prompt, build_user_prompt
from vendor_support_agent.core.conversation_control import get_control_holder
from vendor_support_agent.core.rag_service import retrieve
from vendor_support_agent.core.user_memory import (
    UserFactRow,
    prune_old_facts,
    refresh_user_memory_from_message,
)
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

        user_facts: list[UserFactRow] = []
        async with SessionLocal() as db:
            await self._persist_turn(db, conv_id=conv_id, req=req)
            if settings.user_memory_enabled:
                user_facts = await refresh_user_memory_from_message(
                    db, req=req, conversation_id=conv_id, settings=settings
                )
                await prune_old_facts(
                    db,
                    channel=req.channel,
                    user_id=str(req.user_id),
                    keep=settings.user_memory_max_facts,
                )
            holder = await get_control_holder(db, conversation_id=conv_id)
        if holder == "human":
            return InvokeResponse(
                answer="",
                sources=[],
                meta=InvokeResponseMeta(
                    conversation_holder="human",
                    ai_muted=True,
                ),
            )

        async with SessionLocal() as db:
            chunks = await retrieve(db, query=req.message, limit=8, settings=settings)
            system = await build_system_prompt(db)

        user_prompt = build_user_prompt(
            user_message=req.message, chunks=chunks, user_facts=user_facts
        )
        answer = await complete_chat(system=system, user=user_prompt, settings=settings)

        confidence = min(1.0, max(0.0, sum(c.score for c in chunks) / max(1, len(chunks))))
        needs_human = len(chunks) == 0 or confidence < 0.25

        decision = compute_escalation(
            settings=settings,
            message=req.message,
            answer=answer,
            confidence=confidence,
            needs_human=needs_human,
        )
        final_answer = format_user_facing_answer(llm_answer=answer, decision=decision)
        if decision.should_escalate:
            await send_escalation_notification(
                settings=settings,
                req=req,
                runtime_conversation_id=conv_id,
                user_message=req.message,
                answer=answer,
                confidence=confidence,
                decision=decision,
            )

        sources = [
            SourceItem(document_id=c.document_id, chunk_id=c.chunk_id, title=c.title) for c in chunks
        ]

        async with SessionLocal() as db:
            await self._persist_assistant(
                db,
                conv_id=conv_id,
                req=req,
                answer=final_answer,
                sources=sources,
                confidence=confidence,
                needs_human=needs_human,
                escalated=decision.should_escalate,
                escalation_reasons=decision.reasons,
            )
            holder_out = await get_control_holder(db, conversation_id=conv_id)

        return InvokeResponse(
            answer=final_answer,
            sources=sources,
            meta=InvokeResponseMeta(
                confidence=confidence,
                needs_human=needs_human,
                escalated=decision.should_escalate,
                escalation_reasons=list(decision.reasons),
                conversation_holder=holder_out,
                ai_muted=False,
            ),
        )

    async def invoke_stream(self, req: InvokeRequest) -> AsyncIterator[str]:
        """RAG + LLM с потоковым ответом: на каждом шаге — полный накопленный текст ответа."""
        settings = get_settings()
        conv_id = _conversation_pk(req.conversation_id)

        user_facts: list[UserFactRow] = []
        async with SessionLocal() as db:
            await self._persist_turn(db, conv_id=conv_id, req=req)
            if settings.user_memory_enabled:
                user_facts = await refresh_user_memory_from_message(
                    db, req=req, conversation_id=conv_id, settings=settings
                )
                await prune_old_facts(
                    db,
                    channel=req.channel,
                    user_id=str(req.user_id),
                    keep=settings.user_memory_max_facts,
                )
            holder = await get_control_holder(db, conversation_id=conv_id)
        if holder == "human":
            return

        async with SessionLocal() as db:
            chunks = await retrieve(db, query=req.message, limit=8, settings=settings)
            system = await build_system_prompt(db)

        user_prompt = build_user_prompt(
            user_message=req.message, chunks=chunks, user_facts=user_facts
        )
        answer = ""
        async for answer in stream_chat(system=system, user=user_prompt, settings=settings):
            yield answer

        confidence = min(1.0, max(0.0, sum(c.score for c in chunks) / max(1, len(chunks))))
        needs_human = len(chunks) == 0 or confidence < 0.25

        decision = compute_escalation(
            settings=settings,
            message=req.message,
            answer=answer,
            confidence=confidence,
            needs_human=needs_human,
        )
        final_answer = format_user_facing_answer(llm_answer=answer, decision=decision)
        if decision.should_escalate:
            await send_escalation_notification(
                settings=settings,
                req=req,
                runtime_conversation_id=conv_id,
                user_message=req.message,
                answer=answer,
                confidence=confidence,
                decision=decision,
            )

        if final_answer != answer:
            yield final_answer

        sources = [
            SourceItem(document_id=c.document_id, chunk_id=c.chunk_id, title=c.title) for c in chunks
        ]

        async with SessionLocal() as db:
            await self._persist_assistant(
                db,
                conv_id=conv_id,
                req=req,
                answer=final_answer,
                sources=sources,
                confidence=confidence,
                needs_human=needs_human,
                escalated=decision.should_escalate,
                escalation_reasons=decision.reasons,
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
                    conversation_holder="ai",
                    hidden=False,
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
        escalated: bool = False,
        escalation_reasons: list[str] | None = None,
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
                    "escalated": escalated,
                    "escalation_reasons": list(escalation_reasons or []),
                    "settings": {"embed_provider": get_settings().embed_provider, "llm_model": get_settings().llm_model},
                },
                created_at=datetime.utcnow(),
            )
        )
        await db.commit()
