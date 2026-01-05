"""
Configuration management for AI Codebase Onboarding Assistant.
Uses Pydantic Settings for environment variable management.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Configuration
    app_name: str = Field(default="AI Codebase Onboarding Assistant", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Azure OpenAI Configuration - Chat
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-12-01-preview", env="AZURE_OPENAI_API_VERSION")
    azure_openai_chat_deployment: str = Field(default="gpt-4o-mini", env="AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    # Azure OpenAI Configuration - Embeddings (separate resource)
    azure_openai_embedding_endpoint: str = Field(..., env="AZURE_OPENAI_EMBEDDING_ENDPOINT")
    azure_openai_embedding_api_key: str = Field(..., env="AZURE_OPENAI_EMBEDDING_API_KEY")
    azure_openai_embedding_api_version: str = Field(default="2023-05-15", env="AZURE_OPENAI_EMBEDDING_API_VERSION")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-3-small", env="AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    # Azure AI Search Configuration
    azure_search_endpoint: str = Field(..., env="AZURE_SEARCH_ENDPOINT")
    azure_search_api_key: str = Field(..., env="AZURE_SEARCH_API_KEY")
    azure_search_index_name: str = Field(default="codebase-chunks", env="AZURE_SEARCH_INDEX_NAME")
    
    # GitHub Configuration
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()