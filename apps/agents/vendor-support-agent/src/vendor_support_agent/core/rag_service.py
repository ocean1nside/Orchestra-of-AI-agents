from __future__ import annotations

import asyncio
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.embeddings import embed_query
from vendor_support_agent.core.settings import Settings, get_settings
from vendor_support_agent.db.models.kb import KbChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float


def _search_qdrant_sync(*, qdrant_url: str, collection: str, vector: list[float], limit: int):
    client = QdrantClient(url=qdrant_url)
    try:
        return client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
    except UnexpectedResponse as e:
        # До первой индексации коллекции может не быть — не падаем, просто без RAG.
        if getattr(e, "status_code", None) == 404 or "doesn't exist" in str(e).lower():
            return []
        raise


async def retrieve(
    db: AsyncSession,
    *,
    query: str,
    limit: int = 5,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    settings = settings or get_settings()
    vector = await embed_query(query, settings=settings)
    hits = await asyncio.to_thread(
        _search_qdrant_sync,
        qdrant_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        vector=vector,
        limit=limit,
    )

    chunk_ids: list[str] = []
    scores: dict[str, float] = {}
    for h in hits:
        cid = str(h.payload.get("chunk_id") if h.payload else "")  # type: ignore[union-attr]
        if not cid:
            continue
        chunk_ids.append(cid)
        scores[cid] = float(h.score or 0.0)

    if not chunk_ids:
        return []

    rows = (await db.execute(select(KbChunk).where(KbChunk.id.in_(chunk_ids)))).scalars().all()
    by_id = {r.id: r for r in rows}

    out: list[RetrievedChunk] = []
    for cid in chunk_ids:
        row = by_id.get(cid)
        if row is None:
            continue
        meta = row.metadata_json or {}
        title = str(meta.get("document_title") or meta.get("title") or "Document")
        out.append(
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                title=title,
                content=row.content,
                score=float(scores.get(row.id, 0.0)),
            )
        )
    return out
