"""
Tests for configuration management.
"""

import pytest
from unittest.mock import patch
from app.config import Settings


def test_settings_default_values():
    """Test that settings have appropriate default values."""
    with patch.dict('os.environ', {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key',
        'AZURE_SEARCH_ENDPOINT': 'https://test.search.windows.net',
        'AZURE_SEARCH_API_KEY': 'test-search-key'
    }):
        settings = Settings()
        
        assert settings.app_name == "AI Codebase Onboarding Assistant"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.azure_openai_api_version == "2023-12-01-preview"
        assert settings.azure_openai_embedding_model == "text-embedding-3-small"
        assert settings.azure_openai_chat_model == "gpt-4"
        assert settings.azure_search_index_name == "codebase-chunks"


def test_settings_required_fields():
    """Test that required Azure configuration fields are enforced."""
    from pydantic import ValidationError
    from pydantic import Field
    from pydantic_settings import BaseSettings
    
    class TestSettings(BaseSettings):
        """Test settings without .env file loading."""
        azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
        azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
        azure_search_endpoint: str = Field(..., env="AZURE_SEARCH_ENDPOINT")
        azure_search_api_key: str = Field(..., env="AZURE_SEARCH_API_KEY")
    
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValidationError):
            # Missing required Azure OpenAI endpoint
            TestSettings(
                azure_openai_api_key="test-key",
                azure_search_endpoint="https://test.search.windows.net",
                azure_search_api_key="test-search-key"
            )