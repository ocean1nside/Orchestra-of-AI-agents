from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.db.models.idx import IdxJob
from orchestrator_api.db.models.kb import KbDocument, KbDocumentVersion
from orchestrator_api.modules.indexing.extract import read_original_text
from orchestrator_api.modules.indexing.queue import get_queue
from orchestrator_api.modules.indexing.tasks import run_index_job
from orchestrator_api.modules.knowledge.normalize import normalize_to_markdown
from orchestrator_api.modules.knowledge.storage import save_original_bytes


async def prepare_document_with_ai(
    db: AsyncSession,
    document_id: str,
    *,
    auto_reindex: bool = True,
) -> tuple[KbDocument, str | None, str, str]:
    """
    Читает текущий оригинал, переписывает через ИИ в Markdown, сохраняет новую версию,
    опционально ставит job reindex. Возвращает (doc, job_id, markdown, model).
    """
    doc = (
        await db.execute(select(KbDocument).where(KbDocument.id == document_id))
    ).scalar_one_or_none()
    if doc is None or doc.status == "deleted":
        raise ValueError("Document not found.")

    ver = (
        await db.execute(
            select(KbDocumentVersion)
            .where(KbDocumentVersion.document_id == document_id)
            .order_by(KbDocumentVersion.version.desc(), KbDocumentVersion.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if ver is None or not ver.original_path:
        raise ValueError("No original file for document.")

    raw_text, _suffix = read_original_text(relative_path=ver.original_path)
    markdown, model = await normalize_to_markdown(raw_text=raw_text, title=doc.title)

    max_ver = (
        await db.execute(
            select(func.max(KbDocumentVersion.version)).where(
                KbDocumentVersion.document_id == document_id
            )
        )
    ).scalar_one_or_none()
    next_ver = int(max_ver or 0) + 1

    new_version = KbDocumentVersion(
        document_id=document_id,
        version=next_ver,
        source_type="ai_prepared_markdown",
    )
    db.add(new_version)
    await db.flush()

    rel_path, sha = save_original_bytes(
        document_id=document_id,
        version_id=new_version.id,
        filename="content.md",
        data=markdown.encode("utf-8"),
    )
    new_version.original_path = rel_path
    new_version.content_hash = sha

    meta = dict(doc.metadata_json or {})
    meta.update(
        {
            "ai_normalized": True,
            "ai_prepared_at": datetime.utcnow().isoformat() + "Z",
            "ai_prepare_model": model,
            "ai_prepare_source_version": ver.version,
            "upload_method": meta.get("upload_method", "file"),
            "file_format": "md",
            "source_filename": meta.get("source_filename") or "content.md",
        }
    )
    doc.metadata_json = meta
    doc.status = "pending_index"
    doc.updated_at = datetime.utcnow()

    job_id: str | None = None
    if auto_reindex:
        job = IdxJob(
            mode="document",
            status="pending",
            document_id=document_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(job)
        await db.flush()
        job_id = job.id
        get_queue().enqueue(run_index_job, job_id)

    await db.commit()
    await db.refresh(doc)
    return doc, job_id, markdown, model
