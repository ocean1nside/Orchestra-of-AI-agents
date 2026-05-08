from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/status")
def status() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/infrastructure/status")
def infrastructure_status() -> dict:
    # MVP: later will include Postgres/Redis/Qdrant connectivity checks.
    return {
        "status": "ok",
        "services": {
            "orchestrator_api": {"status": "ok"},
            "postgres": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "qdrant": {"status": "unknown"},
            "storage": {"status": "unknown"},
            "indexing_worker": {"status": "unknown"},
            "vendor_support_agent": {"status": "unknown"},
        },
    }

