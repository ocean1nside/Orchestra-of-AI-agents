"""HTTP middleware для оркестратора."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from orchestrator_api.core.settings import get_settings


def _exempt_path(path: str) -> bool:
    if path in {
        "/",
        "/favicon.ico",
        "/api/v1/health",
        "/api/v1/status",
        "/api/v1/infrastructure/status",
        "/docs",
        "/redoc",
        "/openapi.json",
    }:
        return True
    return path.startswith("/docs/") or path.startswith("/redoc/")


def _extract_api_key(request: Request) -> str | None:
    x = request.headers.get("x-api-key") or request.headers.get("X-Api-Key")
    if x:
        return x.strip()
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


class OrchestratorApiKeyMiddleware(BaseHTTPMiddleware):
    """
    Если ORCHESTRATOR_REQUIRE_API_KEY=true — для всех путей кроме health/status/openapi
    нужен заголовок X-Api-Key или Authorization: Bearer с тем же значением, что API_KEY_DEV.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if not settings.require_orchestrator_api_key:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        if _exempt_path(request.url.path):
            return await call_next(request)

        expected = (settings.api_key_dev or "").strip()
        if expected in ("", "change-me"):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "ORCHESTRATOR_REQUIRE_API_KEY is set but API_KEY_DEV is empty or default; "
                    "set a strong API_KEY_DEV in environment."
                },
            )

        key = _extract_api_key(request)
        if not key or key != expected:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid orchestrator API key (X-Api-Key or Authorization Bearer)."},
            )
        return await call_next(request)
