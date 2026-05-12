from __future__ import annotations

from fastapi import Header, HTTPException

from vendor_support_agent.core.settings import get_settings


async def verify_widget_api_key(
    authorization: str | None = Header(None),
    x_widget_api_key: str | None = Header(None, alias="X-Widget-Api-Key"),
) -> None:
    """Если в окружении задан WIDGET_API_KEY — требуем Bearer или X-Widget-Api-Key."""
    expected = (get_settings().widget_api_key or "").strip()
    if not expected:
        return
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_widget_api_key:
        token = x_widget_api_key.strip()
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing widget API key")


async def verify_operator_api_key(
    authorization: str | None = Header(None),
    x_operator_api_key: str | None = Header(None, alias="X-Operator-Api-Key"),
) -> None:
    """OPERATOR_API_KEY; если не задан — используется WIDGET_API_KEY (как для внутренней консоли)."""
    settings = get_settings()
    expected = (settings.operator_api_key or "").strip()
    if not expected:
        expected = (settings.widget_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Set OPERATOR_API_KEY or WIDGET_API_KEY for operator API access",
        )
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_operator_api_key:
        token = x_operator_api_key.strip()
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing operator API key")
