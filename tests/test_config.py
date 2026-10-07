from app.config import Settings


def test_demo_settings_need_no_azure_credentials():
    settings = Settings(_env_file=None, demo_mode=True)
    assert settings.demo_mode is True
    assert settings.azure_openai_api_key == ""
    assert settings.azure_search_api_key == ""


def test_search_admin_key_alias():
    settings = Settings(_env_file=None, AZURE_SEARCH_ADMIN_KEY="admin-test")
    assert settings.azure_search_api_key == "admin-test"
