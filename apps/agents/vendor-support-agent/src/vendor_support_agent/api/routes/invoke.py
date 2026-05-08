from fastapi import APIRouter

from vendor_support_agent.core.agent_engine import AgentEngine
from vendor_support_agent.schemas.invoke import InvokeRequest, InvokeResponse

router = APIRouter()

_engine = AgentEngine()


@router.post("/api/v1/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)


@router.post("/api/v1/widget/invoke", response_model=InvokeResponse)
async def widget_invoke(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)


@router.post("/api/v1/telegram/webhook", response_model=InvokeResponse)
async def telegram_webhook(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)


@router.post("/api/v1/max/webhook", response_model=InvokeResponse)
async def max_webhook(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)

