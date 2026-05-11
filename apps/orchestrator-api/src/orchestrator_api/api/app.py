from fastapi import FastAPI

from orchestrator_api.api.middleware import OrchestratorApiKeyMiddleware
from orchestrator_api.api.routes.agents import router as agents_router
from orchestrator_api.api.routes.health import router as health_router
from orchestrator_api.api.routes.jobs import router as jobs_router
from orchestrator_api.api.routes.knowledge_documents import router as knowledge_documents_router
from orchestrator_api.api.routes.logs import router as logs_router
from orchestrator_api.api.routes.prompts import router as prompts_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="orchestrator-api",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(OrchestratorApiKeyMiddleware)

    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(
        knowledge_documents_router, prefix="/api/v1/knowledge", tags=["knowledge-documents"]
    )
    app.include_router(jobs_router, prefix="/api/v1", tags=["jobs"])
    app.include_router(prompts_router, prefix="/api/v1", tags=["prompts"])
    app.include_router(logs_router, prefix="/api/v1", tags=["logs"])
    app.include_router(agents_router, prefix="/api/v1", tags=["agents"])
    return app

