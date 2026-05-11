from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from orchestrator_api.core.settings import get_settings
from orchestrator_api.db.session import engine

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/status")
def status() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/infrastructure/status")
async def infrastructure_status() -> dict:
    settings = get_settings()
    services: dict[str, dict[str, str]] = {
        "orchestrator_api": {"status": "ok"},
        "postgres": {"status": "unknown"},
        "redis": {"status": "unknown"},
        "qdrant": {"status": "unknown"},
        "storage": {"status": "unknown"},
        "indexing_worker": {"status": "unknown"},
        "vendor_support_agent": {"status": "unknown"},
    }

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"]["status"] = "ok"
    except Exception as e:
        services["postgres"]["status"] = "error"
        services["postgres"]["error"] = str(e)[:500]

    try:
        redis = Redis.from_url(settings.redis_url)
        try:
            pong = await redis.ping()
            services["redis"]["status"] = "ok" if pong else "error"
        finally:
            await redis.aclose()
    except Exception as e:
        services["redis"]["status"] = "error"
        services["redis"]["error"] = str(e)[:500]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.qdrant_url.rstrip('/')}/collections")
            services["qdrant"]["status"] = "ok" if r.status_code < 500 else "error"
    except Exception as e:
        services["qdrant"]["status"] = "error"
        services["qdrant"]["error"] = str(e)[:500]

    try:
        root = Path(settings.storage_path)
        services["storage"]["status"] = "ok" if root.exists() else "error"
    except Exception as e:
        services["storage"]["status"] = "error"
        services["storage"]["error"] = str(e)[:500]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.vendor_support_agent_base_url.rstrip('/')}/health")
            services["vendor_support_agent"]["status"] = "ok" if r.status_code == 200 else "error"
    except Exception as e:
        services["vendor_support_agent"]["status"] = "error"
        services["vendor_support_agent"]["error"] = str(e)[:500]

    # indexing_worker: best-effort via Redis queue presence (worker itself doesn't expose HTTP)
    try:
        redis = Redis.from_url(settings.redis_url)
        try:
            await redis.ping()
            services["indexing_worker"]["status"] = "unknown"
            services["indexing_worker"]["note"] = "No HTTP endpoint; verify docker logs for indexing-worker"
        finally:
            await redis.aclose()
    except Exception:
        services["indexing_worker"]["status"] = "error"

    overall = "ok"
    for s in services.values():
        if s.get("status") == "error":
            overall = "degraded"
            break

    return {"status": overall, "services": services}
