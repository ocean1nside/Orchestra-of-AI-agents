from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.db.models.runtime import RuntimeAgentLog
from orchestrator_api.db.session import get_db
from orchestrator_api.schemas.logs import RuntimeLogOut, RuntimeLogsResponse

router = APIRouter()


@router.get("/logs/runtime", response_model=RuntimeLogsResponse)
async def runtime_logs(
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> RuntimeLogsResponse:
    rows = (
        await db.execute(select(RuntimeAgentLog).order_by(RuntimeAgentLog.created_at.desc()).limit(limit))
    ).scalars().all()
    return RuntimeLogsResponse(
        items=[
            RuntimeLogOut(id=r.id, conversation_id=r.conversation_id, payload=r.payload or {}, created_at=r.created_at)
            for r in rows
        ]
    )


@router.get("/logs/indexing")
async def indexing_logs_stub() -> dict:
    return {"items": [], "note": "MVP: use idx_job_events / jobs API for indexing logs"}


@router.get("/audit/events")
async def audit_events_stub() -> dict:
    return {"items": [], "note": "MVP: audit_events table not implemented yet"}
