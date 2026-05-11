from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/agents")
async def list_agents() -> dict:
    return {
        "items": [
            {
                "agent_id": "vendor-support-agent",
                "title": "Vendor support",
                "status": "unknown",
            }
        ]
    }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    if agent_id != "vendor-support-agent":
        raise HTTPException(status_code=404, detail="Unknown agent")
    return {"agent_id": agent_id, "title": "Vendor support", "metadata": {}}


@router.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str) -> dict:
    if agent_id != "vendor-support-agent":
        raise HTTPException(status_code=404, detail="Unknown agent")
    return {"agent_id": agent_id, "status": "unknown", "detail": "MVP: status polling not wired yet"}
