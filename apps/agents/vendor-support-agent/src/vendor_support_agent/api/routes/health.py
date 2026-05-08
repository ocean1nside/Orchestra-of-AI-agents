from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/metadata")
def metadata() -> dict:
    return {"agent_id": "vendor-support-agent", "version": "0.1.0"}

