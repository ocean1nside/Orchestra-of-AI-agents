from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/orchestrator"
    qdrant_url: str = "http://qdrant:6333"
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""
    telegram_bot_token: str = ""
    max_bot_token: str = ""


def get_settings() -> Settings:
    return Settings()

