from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

from orchestrator_api.core.settings import get_settings


def _client() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url)


def ensure_collection(*, collection: str, vector_size: int) -> None:
    client = _client()
    names = {c.name for c in client.get_collections().collections}
    if collection in names:
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def delete_points_by_ids(*, collection: str, point_ids: list[str]) -> None:
    if not point_ids:
        return
    client = _client()
    client.delete(collection_name=collection, points_selector=PointIdsList(points=point_ids))


def upsert_points(*, collection: str, points: list[PointStruct]) -> None:
    if not points:
        return
    client = _client()
    client.upsert(collection_name=collection, points=points)
