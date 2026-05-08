from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.db.models.kb import KbDocument, KbDocumentVersion
from orchestrator_api.db.session import get_db
from orchestrator_api.modules.knowledge.storage import save_original_bytes
from orchestrator_api.schemas.knowledge_documents import (
    DocumentCreateJson,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentOut,
    DocumentUpdate,
)

router = APIRouter()


def _doc_out(d: KbDocument) -> DocumentOut:
    return DocumentOut(
        document_id=d.id,
        title=d.title,
        status=d.status,  # type: ignore[arg-type]
        metadata=d.metadata_json or {},
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)) -> DocumentListResponse:
    rows = (await db.execute(select(KbDocument).order_by(KbDocument.created_at.desc()))).scalars().all()
    return DocumentListResponse(items=[_doc_out(r) for r in rows])


@router.post("/documents", response_model=DocumentCreateResponse)
async def create_document(
    payload: DocumentCreateJson | None = None,
    file: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> DocumentCreateResponse:
    if payload is None and file is None:
        raise HTTPException(status_code=400, detail="Provide either JSON payload or multipart file.")
    if payload is not None and file is not None:
        raise HTTPException(status_code=400, detail="Provide only one: JSON payload or multipart file.")

    metadata: dict[str, Any] = {}
    title: str
    raw: bytes
    filename: str

    if payload is not None:
        title = payload.title
        metadata = payload.metadata or {}
        raw = payload.content.encode("utf-8")
        filename = "content.md"
    else:
        assert file is not None
        title = file.filename or "document"
        filename = file.filename or "document"
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty file.")

    doc = KbDocument(title=title, status="uploaded", metadata_json=metadata)
    db.add(doc)
    await db.flush()  # get doc.id

    version = KbDocumentVersion(document_id=doc.id, version=1)
    db.add(version)
    await db.flush()

    rel_path, sha = save_original_bytes(
        document_id=doc.id, version_id=version.id, filename=filename, data=raw
    )
    version.original_path = rel_path
    version.content_hash = sha

    if payload is not None and payload.auto_index:
        doc.status = "pending_index"

    doc.updated_at = datetime.utcnow()
    await db.commit()

    return DocumentCreateResponse(
        status=doc.status,  # type: ignore[arg-type]
        document_id=doc.id,
        indexing_status=doc.status,  # type: ignore[arg-type]
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)) -> DocumentOut:
    row = (await db.execute(select(KbDocument).where(KbDocument.id == document_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _doc_out(row)


@router.patch("/documents/{document_id}", response_model=DocumentOut)
async def patch_document(
    document_id: str, patch: DocumentUpdate, db: AsyncSession = Depends(get_db)
) -> DocumentOut:
    values: dict[str, Any] = {"updated_at": datetime.utcnow()}
    if patch.title is not None:
        values["title"] = patch.title
    if patch.metadata is not None:
        values["metadata"] = patch.metadata

    res = await db.execute(update(KbDocument).where(KbDocument.id == document_id).values(**values))
    if res.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Document not found.")
    await db.commit()
    row = (await db.execute(select(KbDocument).where(KbDocument.id == document_id))).scalar_one()
    return _doc_out(row)


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(select(KbDocument).where(KbDocument.id == document_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    row.status = "deleted"
    row.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "deleted", "document_id": document_id}

