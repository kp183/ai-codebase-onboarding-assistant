from datetime import datetime
from unittest.mock import Mock

import pytest

from app.services.repository_ingestion import RepositoryIngestionService


def test_public_github_url_is_allowed_in_demo_mode():
    service = RepositoryIngestionService()
    assert service._is_valid_github_url("https://github.com/githubtraining/hellogitworld")


def test_file_cap_rejects_oversized_repository(tmp_path):
    service = RepositoryIngestionService()
    service.MAX_FILES = 1
    (tmp_path / "one.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="file ingestion limit"):
        import asyncio

        asyncio.run(service.fetch_code_files(str(tmp_path)))


def test_repository_source_size_cap_rejects_oversized_repository(tmp_path):
    service = RepositoryIngestionService()
    service.MAX_REPOSITORY_SIZE = 8
    (tmp_path / "large.py").write_text("VALUE = 'long'\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source-size ingestion limit"):
        import asyncio

        asyncio.run(service.fetch_code_files(str(tmp_path)))


def test_demo_repo_size_is_checked_before_clone(monkeypatch):
    from app.config import settings
    from app.services import repository_ingestion as ingestion_module

    service = RepositoryIngestionService()
    response = Mock(status_code=200)
    response.json.return_value = {"size": service.MAX_CLONE_SIZE_KB + 1}
    monkeypatch.setattr(ingestion_module.requests, "get", Mock(return_value=response))
    monkeypatch.setattr(settings, "demo_mode", True)

    import asyncio

    accessible = asyncio.run(
        service._check_repository_accessibility("https://github.com/example/large-repo")
    )
    assert accessible is False
