from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.db.models.idx import IdxJob
from orchestrator_api.db.session import get_db
from orchestrator_api.modules.indexing.queue import get_queue
from orchestrator_api.modules.indexing.tasks import run_index_job
from orchestrator_api.schemas.jobs import JobListResponse, JobOut, JobProgress, ReindexRequest

router = APIRouter()


def _job_out(j: IdxJob) -> JobOut:
    return JobOut(
        job_id=j.id,
        mode=j.mode,  # type: ignore[arg-type]
        status=j.status,  # type: ignore[arg-type]
        document_id=j.document_id,
        progress=JobProgress(
            total_documents=j.total_documents,
            processed_documents=j.processed_documents,
            total_chunks=j.total_chunks,
            indexed_chunks=j.indexed_chunks,
        ),
        error_message=j.error_message or None,
        created_at=j.created_at,
        updated_at=j.updated_at,
    )


@router.post("/knowledge/reindex", response_model=JobOut)
async def reindex(req: ReindexRequest, db: AsyncSession = Depends(get_db)) -> JobOut:
    if req.mode == "document" and not req.document_id:
        raise HTTPException(status_code=400, detail="document_id is required for mode=document")

    job = IdxJob(
        mode=req.mode,
        status="pending",
        document_id=req.document_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    await db.flush()

    q = get_queue()
    q.enqueue(run_index_job, job.id)

    await db.commit()
    return _job_out(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(db: AsyncSession = Depends(get_db)) -> JobListResponse:
    rows = (await db.execute(select(IdxJob).order_by(IdxJob.created_at.desc()))).scalars().all()
    return JobListResponse(items=[_job_out(r) for r in rows])


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> JobOut:
    row = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _job_out(row)


@router.get("/knowledge/index/status")
async def index_status_summary(db: AsyncSession = Depends(get_db)) -> dict:
    counts = dict(
        (await db.execute(select(IdxJob.status, func.count()).group_by(IdxJob.status))).all()
    )

    latest = (
        await db.execute(select(IdxJob).order_by(IdxJob.created_at.desc()).limit(1))
    ).scalar_one_or_none()

    return {
        "job_counts_by_status": counts,
        "latest_job": (_job_out(latest).model_dump() if latest else None),
    }

