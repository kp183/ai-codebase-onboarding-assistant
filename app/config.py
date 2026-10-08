"""Application configuration; Azure settings are optional for local demos."""
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    app_name: str = "AI Codebase Onboarding Assistant"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    demo_mode: bool = False
    cors_allowed_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:8002,http://127.0.0.1:8002"
    )
    max_request_bytes: int = 65536
    max_chunks_per_repo: int = 5000
    ingest_requests_per_minute: int = 10
    chat_requests_per_minute: int = 30
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embedding_endpoint: str = ""
    azure_openai_embedding_api_key: str = ""
    azure_openai_embedding_api_version: str = "2023-05-15"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_search_endpoint: str = ""
    azure_search_api_key: str = Field(default="", validation_alias=AliasChoices("AZURE_SEARCH_ADMIN_KEY", "AZURE_SEARCH_API_KEY"))
    azure_search_index_name: str = "codebase-chunks"
    github_token: str | None = None


settings = Settings()
