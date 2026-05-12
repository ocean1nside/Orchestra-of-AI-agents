from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.embeddings import embed_query
from vendor_support_agent.core.settings import Settings, get_settings
from vendor_support_agent.db.models.kb import KbChunk

# Для лексического поиска: слишком частые короткие слова дают шум в OR.
_LEX_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "you",
        "are",
        "not",
        "how",
        "what",
        "when",
        "where",
        "как",
        "что",
        "где",
        "когда",
        "это",
        "для",
        "или",
        "можно",
        "нужно",
        "есть",
        "будет",
        "было",
        "если",
        "они",
        "она",
        "его",
        "них",
        "мне",
        "вас",
        "нас",
        "про",
        "при",
        "все",
        "уже",
        "ещё",
        "еще",
        "так",
        "вот",
        "лишь",
        "хочу",
        "надо",
        "могу",
        "поможете",
        "расскажи",
        "скажите",
    }
)


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
        if getattr(e, "status_code", None) == 404 or "doesn't exist" in str(e).lower():
            return []
        raise


def _tokenize_lexical(query: str) -> list[str]:
    """Слова/токены для ILIKE; без семантики, только совпадение подстрок."""
    raw = re.findall(r"[\w\-]{3,}", (query or "").lower(), flags=re.UNICODE)
    seen: set[str] = set()
    unique: list[str] = []
    for w in raw:
        if w in seen:
            continue
        seen.add(w)
        unique.append(w)
    significant = [t for t in unique if t not in _LEX_STOP and len(t) >= 4]
    if significant:
        return significant[:12]
    return unique[:10]


async def _retrieve_lexical(
    db: AsyncSession,
    *,
    query: str,
    limit: int,
) -> list[RetrievedChunk]:
    """
    Лексический RAG: для каждого токена отдельный LIMIT — иначе один редкий токен
    (например «баннер») может потеряться при OR+LIMIT на большой базе.
    Ранжирование: IDF по частоте токена среди кандидатов (редкие совпадения важнее).
    """
    tokens = _tokenize_lexical(query)
    if not tokens:
        return []

    per_token_limit = 55
    merged: dict[str, KbChunk] = {}
    for t in tokens:
        stmt = select(KbChunk).where(KbChunk.content.ilike(f"%{t}%")).limit(per_token_limit)
        for row in (await db.execute(stmt)).scalars().all():
            merged[row.id] = row

    rows = list(merged.values())
    if not rows:
        return []

    freq = Counter()
    for row in rows:
        cl = (row.content or "").lower()
        for t in tokens:
            if t in cl:
                freq[t] += 1

    qlow = (query or "").lower()
    scored: list[tuple[float, KbChunk]] = []
    for row in rows:
        cl = (row.content or "").lower()
        s = 0.0
        for t in tokens:
            if t in cl:
                # чем реже токен среди кандидатов, тем выше вес
                s += 6.0 / (1.0 + max(0, freq[t] - 1) * 0.4)
        if s == 0:
            continue
        if len(qlow) >= 8 and qlow[:120] in cl:
            s += 4.0
        scored.append((s, row))

    scored.sort(key=lambda x: -x[0])
    max_s = scored[0][0] if scored else 1.0
    out: list[RetrievedChunk] = []
    for h, row in scored[:limit]:
        meta = row.metadata_json or {}
        title = str(meta.get("document_title") or meta.get("title") or "Document")
        norm = min(1.0, h / max(max_s, 1e-6))
        out.append(
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                title=title,
                content=row.content,
                score=norm,
            )
        )
    return out


async def _retrieve_vector(
    db: AsyncSession,
    *,
    query: str,
    limit: int,
    settings: Settings,
) -> list[RetrievedChunk]:
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


async def retrieve(
    db: AsyncSession,
    *,
    query: str,
    limit: int = 8,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    """
    RAG: при EMBED_PROVIDER=hash векторный поиск в Qdrant не семантический (хэш текста),
    поэтому используем лексический поиск по kb_chunks. При openai — Qdrant, при пустом
    или слабом результате — запасной лексический поиск.
    """
    settings = settings or get_settings()

    if settings.embed_provider == "hash":
        return await _retrieve_lexical(db, query=query, limit=limit)

    vec_chunks = await _retrieve_vector(db, query=query, limit=limit, settings=settings)
    if vec_chunks:
        best = max((c.score for c in vec_chunks), default=0.0)
        if best >= 0.15:
            return vec_chunks

    lex = await _retrieve_lexical(db, query=query, limit=limit)
    if lex:
        return lex
    return vec_chunks
