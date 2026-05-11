from __future__ import annotations

import hashlib
import struct
import httpx

from orchestrator_api.core.settings import Settings, get_settings


def _hash_embedding(text: str, dim: int) -> list[float]:
    out: list[float] = []
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    counter = 0
    while len(out) < dim:
        block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
        for i in range(0, len(block) - 3, 4):
            u = struct.unpack_from("!I", block, i)[0]
            out.append((u / 4294967295.0) * 2.0 - 1.0)
            if len(out) >= dim:
                break
    return out[:dim]


async def embed_batch(texts: list[str], settings: Settings | None = None) -> list[list[float]]:
    settings = settings or get_settings()
    if not texts:
        return []

    if settings.embed_provider == "hash":
        return [_hash_embedding(t, settings.vector_dimensions) for t in texts]

    if settings.embed_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBED_PROVIDER=openai")

        payload = {
            "model": settings.embedding_model,
            "input": texts,
            "dimensions": settings.vector_dimensions,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        return [it["embedding"] for it in items]

    raise RuntimeError(f"Unknown embed provider: {settings.embed_provider}")
