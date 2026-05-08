from fastapi import FastAPI

from orchestrator_api.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="orchestrator-api",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    return app

