from fastapi import FastAPI

from vendor_support_agent.api.routes.health import router as health_router
from vendor_support_agent.api.routes.invoke import router as invoke_router
from vendor_support_agent.api.routes.max_channel import router as max_channel_router
from vendor_support_agent.api.routes.operator import router as operator_router
from vendor_support_agent.api.routes.telegram import router as telegram_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="vendor-support-agent",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.include_router(health_router, tags=["health"])
    app.include_router(invoke_router, tags=["invoke"])
    app.include_router(telegram_router, tags=["telegram"])
    app.include_router(max_channel_router, tags=["max"])
    app.include_router(operator_router)
    return app

