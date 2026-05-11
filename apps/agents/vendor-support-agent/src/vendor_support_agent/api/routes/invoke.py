from fastapi import APIRouter, Depends

from vendor_support_agent.api.dependencies import verify_widget_api_key
from vendor_support_agent.core.agent_engine import AgentEngine
from vendor_support_agent.schemas.invoke import InvokeRequest, InvokeResponse

router = APIRouter()

_engine = AgentEngine()


@router.post(
    "/api/v1/invoke",
    response_model=InvokeResponse,
    dependencies=[Depends(verify_widget_api_key)],
)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)


@router.post(
    "/api/v1/widget/invoke",
    response_model=InvokeResponse,
    dependencies=[Depends(verify_widget_api_key)],
)
async def widget_invoke(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)


@router.post("/api/v1/telegram/invoke", response_model=InvokeResponse)
async def telegram_invoke(req: InvokeRequest) -> InvokeResponse:
    """Ручная проверка в формате InvokeRequest (curl / Postman), без Telegram Update."""
    return await _engine.invoke(req)


@router.post("/api/v1/max/webhook", response_model=InvokeResponse)
async def max_webhook(req: InvokeRequest) -> InvokeResponse:
    return await _engine.invoke(req)

