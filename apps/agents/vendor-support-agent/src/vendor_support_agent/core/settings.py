from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = Field(default="knowledge_chunks", validation_alias="QDRANT_COLLECTION")

    embed_provider: Literal["hash", "openai"] = Field(default="hash", validation_alias="EMBED_PROVIDER")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")
    vector_dimensions: int = Field(default=384, validation_alias="VECTOR_DIMENSIONS")

    prompts_dir: Path = Field(default=Path("/app/prompts"), validation_alias="PROMPTS_DIR")

    llm_provider: str = Field(default="openai", validation_alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")

    telegram_bot_token: str = ""
    # Совпадает с secret_token при вызове setWebhook — заголовок X-Telegram-Bot-Api-Secret-Token.
    telegram_webhook_secret: str = Field(default="", validation_alias="TELEGRAM_WEBHOOK_SECRET")
    max_bot_token: str = ""
    # Секрет из POST /subscriptions (поле secret); заголовок X-Max-Bot-Api-Secret.
    max_webhook_secret: str = Field(default="", validation_alias="MAX_WEBHOOK_SECRET")
    max_api_base: str = Field(default="https://platform-api.max.ru", validation_alias="MAX_API_BASE")

    # Если не пусто: POST /api/v1/widget/invoke и /api/v1/invoke требуют Bearer или X-Widget-Api-Key.
    widget_api_key: str = Field(default="", validation_alias="WIDGET_API_KEY")


def get_settings() -> Settings:
    return Settings()
