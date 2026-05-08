from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import select

from orchestrator_api.db.models.idx import IdxJob
from orchestrator_api.db.session import SessionLocal


async def _mark(job_id: str, *, status: str, error_message: str = "") -> None:
    async with SessionLocal() as db:
        job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one_or_none()
        if job is None:
            return
        job.status = status
        job.error_message = error_message
        job.updated_at = datetime.utcnow()
        await db.commit()


async def _run_index_job(job_id: str) -> None:
    # MVP stub worker: later will do extract -> chunk -> embed -> write Postgres/Qdrant.
    await _mark(job_id, status="processing")
    await asyncio.sleep(0.2)
    await _mark(job_id, status="completed")


def run_index_job(job_id: str) -> None:
    asyncio.run(_run_index_job(job_id))

