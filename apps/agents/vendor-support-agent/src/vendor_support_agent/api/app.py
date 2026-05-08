from fastapi import FastAPI

from vendor_support_agent.api.routes.health import router as health_router
from vendor_support_agent.api.routes.invoke import router as invoke_router


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
    return app

