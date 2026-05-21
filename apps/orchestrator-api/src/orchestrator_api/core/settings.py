from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = Field(default="knowledge_chunks", validation_alias="QDRANT_COLLECTION")
    storage_path: str = "/storage/knowledge"
    api_key_dev: str = Field(default="change-me", validation_alias="API_KEY_DEV")
    # Если true — все маршруты /api/v1/* кроме health/status/infrastructure требуют X-Api-Key / Bearer = API_KEY_DEV.
    require_orchestrator_api_key: bool = Field(
        default=False,
        validation_alias="ORCHESTRATOR_REQUIRE_API_KEY",
    )

    # Embeddings: `hash` = deterministic local vectors (dev); `openai` = OpenAI API (set OPENAI_API_KEY).
    embed_provider: Literal["hash", "openai"] = Field(default="hash", validation_alias="EMBED_PROVIDER")
    openai_api_key: str = ""
    embedding_model: str = Field(default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")
    vector_dimensions: int = Field(default=384, validation_alias="VECTOR_DIMENSIONS")
    knowledge_normalize_model: str = Field(
        default="gpt-4o-mini",
        validation_alias="KNOWLEDGE_NORMALIZE_MODEL",
    )
    prompt_tune_model: str = Field(
        default="gpt-4o-mini",
        validation_alias="PROMPT_TUNE_MODEL",
    )

    vendor_support_agent_base_url: str = Field(
        default="http://vendor-support-agent:8010",
        validation_alias="VENDOR_SUPPORT_AGENT_BASE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

