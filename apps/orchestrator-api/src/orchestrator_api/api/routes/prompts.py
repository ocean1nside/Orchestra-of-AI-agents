from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.db.models.prompt import PromptTemplate, PromptVersion
from orchestrator_api.db.session import get_db
from orchestrator_api.modules.prompts.prompt_tune import apply_prompt_tune, propose_prompt_tune
from orchestrator_api.schemas.prompts import (
    PromptCreateBody,
    PromptListItem,
    PromptListResponse,
    PromptOut,
    PromptPutBody,
    PromptTuneApplyBody,
    PromptTuneApplyResponse,
    PromptTunePreviewResponse,
    PromptTuneRequest,
    PromptVersionItem,
    PromptVersionsResponse,
)

router = APIRouter()


@router.post("/prompts/tune", response_model=PromptTunePreviewResponse)
async def preview_prompt_tune(body: PromptTuneRequest, db: AsyncSession = Depends(get_db)) -> PromptTunePreviewResponse:
    """ИИ предлагает правки промптов по жалобе оператора (без сохранения)."""
    try:
        summary, log_entry, changes, model = await propose_prompt_tune(db, feedback=body.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Prompt tune failed: {e}") from e
    return PromptTunePreviewResponse(
        summary=summary,
        log_entry=log_entry,
        changes=changes,
        model=model,
    )


@router.post("/prompts/tune/apply", response_model=PromptTuneApplyResponse)
async def apply_prompt_tune_route(
    body: PromptTuneApplyBody, db: AsyncSession = Depends(get_db)
) -> PromptTuneApplyResponse:
    """Применить предпросмотренные правки и дописать журнал tuning_log."""
    if not body.changes and not (body.log_entry or "").strip():
        raise HTTPException(status_code=400, detail="No changes to apply")
    try:
        applied = await apply_prompt_tune(db, changes=body.changes, log_entry=body.log_entry)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Apply failed: {e}") from e
    keys = ", ".join(f"{a.prompt_key} (v{a.version})" for a in applied if a.prompt_key != "tuning_log")
    summary = f"Сохранено: {keys}" if keys else "Обновлён журнал тюнинга"
    return PromptTuneApplyResponse(summary=summary, applied=applied)


@router.post("/prompts", response_model=PromptOut, status_code=201)
async def create_prompt(body: PromptCreateBody, db: AsyncSession = Depends(get_db)) -> PromptOut:
    exists = (
        await db.execute(select(PromptTemplate).where(PromptTemplate.prompt_key == body.prompt_key))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail=f"prompt_key already exists: {body.prompt_key}")

    now = datetime.utcnow()
    db.add(
        PromptTemplate(
            prompt_key=body.prompt_key,
            description=(body.description or "").strip(),
            created_at=now,
        )
    )
    pv = PromptVersion(
        id=f"pv_{uuid4().hex}",
        prompt_key=body.prompt_key,
        version=1,
        content=body.content.strip(),
        created_at=now,
    )
    db.add(pv)
    await db.commit()
    return PromptOut(
        prompt_key=body.prompt_key,
        version=1,
        content=pv.content,
        updated_at=pv.created_at,
    )


@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(db: AsyncSession = Depends(get_db)) -> PromptListResponse:
    templates = (await db.execute(select(PromptTemplate))).scalars().all()
    items: list[PromptListItem] = []
    for t in templates:
        latest = (
            await db.execute(
                select(func.max(PromptVersion.version)).where(PromptVersion.prompt_key == t.prompt_key)
            )
        ).scalar_one()
        ver = int(latest or 0)
        items.append(
            PromptListItem(prompt_key=t.prompt_key, description=t.description or "", latest_version=ver)
        )
    items.sort(key=lambda x: x.prompt_key)
    return PromptListResponse(items=items)


@router.get("/prompts/{prompt_key}", response_model=PromptOut)
async def get_prompt(prompt_key: str, db: AsyncSession = Depends(get_db)) -> PromptOut:
    exists = (await db.execute(select(PromptTemplate).where(PromptTemplate.prompt_key == prompt_key))).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="Unknown prompt_key")

    row = (
        await db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_key == prompt_key)
            .order_by(PromptVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No versions for prompt_key")
    return PromptOut(
        prompt_key=prompt_key,
        version=row.version,
        content=row.content,
        updated_at=row.created_at,
    )


@router.put("/prompts/{prompt_key}", response_model=PromptOut)
async def put_prompt(prompt_key: str, body: PromptPutBody, db: AsyncSession = Depends(get_db)) -> PromptOut:
    exists = (await db.execute(select(PromptTemplate).where(PromptTemplate.prompt_key == prompt_key))).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="Unknown prompt_key")

    latest = (
        await db.execute(
            select(func.max(PromptVersion.version)).where(PromptVersion.prompt_key == prompt_key)
        )
    ).scalar_one()
    next_ver = int(latest or 0) + 1
    pv = PromptVersion(
        id=f"pv_{uuid4().hex}",
        prompt_key=prompt_key,
        version=next_ver,
        content=body.content,
        created_at=datetime.utcnow(),
    )
    db.add(pv)
    await db.commit()
    return PromptOut(prompt_key=prompt_key, version=next_ver, content=body.content, updated_at=pv.created_at)


@router.get("/prompts/{prompt_key}/versions", response_model=PromptVersionsResponse)
async def list_versions(prompt_key: str, db: AsyncSession = Depends(get_db)) -> PromptVersionsResponse:
    exists = (await db.execute(select(PromptTemplate).where(PromptTemplate.prompt_key == prompt_key))).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="Unknown prompt_key")

    rows = (
        await db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_key == prompt_key)
            .order_by(PromptVersion.version.desc())
        )
    ).scalars().all()
    return PromptVersionsResponse(
        items=[PromptVersionItem(id=r.id, version=r.version, created_at=r.created_at) for r in rows]
    )
