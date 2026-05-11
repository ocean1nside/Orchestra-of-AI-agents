from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from uuid import uuid4

from qdrant_client.models import PointStruct
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.core.settings import Settings, get_settings
from orchestrator_api.db.models.idx import IdxJob, IdxJobEvent
from orchestrator_api.db.models.kb import KbChunk, KbDocument, KbDocumentVersion
from orchestrator_api.db.session import SessionLocal
from orchestrator_api.modules.indexing import qdrant_index
from orchestrator_api.modules.indexing.chunk_text import chunk_text
from orchestrator_api.modules.indexing.embeddings import embed_batch
from orchestrator_api.modules.indexing.extract import read_original_text


async def _add_event(db: AsyncSession, job_id: str, message: str, *, level: str = "info") -> None:
    db.add(
        IdxJobEvent(
            job_id=job_id,
            level=level,
            message=message,
            created_at=datetime.utcnow(),
        )
    )


async def _collect_documents(db: AsyncSession, job: IdxJob) -> list[KbDocument]:
    if job.mode == "document":
        if not job.document_id:
            return []
        row = (await db.execute(select(KbDocument).where(KbDocument.id == job.document_id))).scalar_one_or_none()
        if row is None or row.status == "deleted":
            return []
        return [row]

    if job.mode == "incremental":
        stmt = select(KbDocument).where(KbDocument.status == "pending_index")
        return list((await db.execute(stmt)).scalars().all())

    if job.mode == "full":
        stmt = select(KbDocument).where(KbDocument.status != "deleted")
        return list((await db.execute(stmt)).scalars().all())

    return []


async def _index_one_document(db: AsyncSession, job_id: str, doc: KbDocument, settings: Settings) -> int:
    await _add_event(db, job_id, f"Indexing document_id={doc.id}")
    doc.status = "indexing"
    doc.updated_at = datetime.utcnow()
    await db.flush()

    stmt = (
        select(KbDocumentVersion)
        .where(KbDocumentVersion.document_id == doc.id)
        .order_by(KbDocumentVersion.version.desc(), KbDocumentVersion.created_at.desc())
        .limit(1)
    )
    ver = (await db.execute(stmt)).scalar_one_or_none()
    if ver is None or not ver.original_path:
        raise RuntimeError(f"No original file for document {doc.id}")

    text, _suffix = read_original_text(relative_path=ver.original_path)
    parts = chunk_text(text)
    if not parts:
        raise RuntimeError(f"Empty document after extraction: {doc.id}")

    old_ids = list((await db.execute(select(KbChunk.id).where(KbChunk.document_id == doc.id))).scalars().all())
    if old_ids:
        await asyncio.to_thread(
            qdrant_index.delete_points_by_ids,
            collection=settings.qdrant_collection,
            point_ids=old_ids,
        )
    await db.execute(delete(KbChunk).where(KbChunk.document_id == doc.id))
    await db.flush()

    meta = doc.metadata_json or {}
    category = str(meta.get("category", "general"))
    title = doc.title

    batch_size = 32
    points: list[PointStruct] = []
    for i in range(0, len(parts), batch_size):
        batch = parts[i : i + batch_size]
        vectors = await embed_batch(batch, settings=settings)
        for offset, (piece, vec) in enumerate(zip(batch, vectors, strict=True)):
            idx = i + offset
            cid = f"chunk_{uuid4().hex}"
            chunk = KbChunk(
                id=cid,
                document_id=doc.id,
                content=piece,
                metadata_json={
                    "document_title": title,
                    "category": category,
                    "chunk_index": idx,
                },
                created_at=datetime.utcnow(),
            )
            db.add(chunk)
            points.append(
                PointStruct(
                    id=cid,
                    vector=vec,
                    payload={
                        "chunk_id": cid,
                        "document_id": doc.id,
                        "title": title,
                        "category": category,
                        "source_type": ver.source_type or "knowledge_document",
                    },
                )
            )

    await db.flush()
    await asyncio.to_thread(qdrant_index.upsert_points, collection=settings.qdrant_collection, points=points)

    doc.status = "indexed"
    doc.updated_at = datetime.utcnow()
    return len(parts)


async def execute_index_job(job_id: str) -> None:
    settings = get_settings()

    async with SessionLocal() as db:
        job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one_or_none()
        if job is None:
            return

        job.status = "processing"
        job.updated_at = datetime.utcnow()
        await _add_event(db, job_id, f"Job started mode={job.mode}")
        await db.commit()

        try:
            await asyncio.to_thread(
                qdrant_index.ensure_collection,
                collection=settings.qdrant_collection,
                vector_size=settings.vector_dimensions,
            )
        except Exception as e:
            job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:2000]
            job.updated_at = datetime.utcnow()
            await _add_event(db, job_id, f"Qdrant init failed: {e}", level="error")
            await db.commit()
            return

        docs = await _collect_documents(db, job)
        job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one()
        job.total_documents = len(docs)
        job.processed_documents = 0
        job.total_chunks = 0
        job.indexed_chunks = 0
        job.updated_at = datetime.utcnow()
        await _add_event(db, job_id, f"Documents to process: {len(docs)}")
        await db.commit()

        if not docs:
            job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one()
            job.status = "completed"
            job.updated_at = datetime.utcnow()
            await _add_event(db, job_id, "No documents to index; completed")
            await db.commit()
            return

        processed = 0
        total_chunks = 0
        indexed_chunks = 0

        for doc in docs:
            try:
                n = await _index_one_document(db, job_id, doc, settings)
                processed += 1
                total_chunks += n
                indexed_chunks += n

                job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one()
                job.processed_documents = processed
                job.total_chunks = total_chunks
                job.indexed_chunks = indexed_chunks
                job.updated_at = datetime.utcnow()
                await db.commit()
            except Exception:
                tb = traceback.format_exc()[:4000]
                job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one()
                job.status = "failed"
                job.error_message = tb
                job.updated_at = datetime.utcnow()

                doc_row = (await db.execute(select(KbDocument).where(KbDocument.id == doc.id))).scalar_one_or_none()
                if doc_row is not None:
                    doc_row.status = "failed"
                    doc_row.updated_at = datetime.utcnow()

                await _add_event(db, job_id, tb, level="error")
                await db.commit()
                return

        job = (await db.execute(select(IdxJob).where(IdxJob.id == job_id))).scalar_one()
        job.status = "completed"
        job.updated_at = datetime.utcnow()
        await _add_event(db, job_id, "Job completed")
        await db.commit()
