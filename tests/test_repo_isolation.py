from contextlib import asynccontextmanager
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.models.data_models import CodeFile
from app.services.repository_ingestion import repository_service
from app.services.service_manager import get_service_manager_sync


client = TestClient(app)


def _code_file(path: str, content: str) -> CodeFile:
    return CodeFile(
        file_path=path,
        content=content,
        language="python",
        size_bytes=len(content.encode("utf-8")),
        last_modified=datetime.utcnow(),
    )


def test_repo_search_isolation_and_reingest_replacement(monkeypatch):
    repo_a = "https://github.com/example/repo-a"
    repo_b = "https://github.com/example/repo-b"
    indexed_files = {
        repo_a: [_code_file("app/alpha.py", 'def get_alpha_balance():\n    return "alpha-needle"\n')],
        repo_b: [_code_file("internal/beta.py", 'def get_beta_balance():\n    return "beta-secret"\n')],
    }

    @asynccontextmanager
    async def fake_repository_files(source):
        yield indexed_files[source]

    monkeypatch.setattr(repository_service, "repository_files", fake_repository_files)
    ingested_a = client.post("/api/ingest", json={"repository_url": repo_a})
    manager = get_service_manager_sync()
    count_after_a = manager.search_service.get_document_count()
    ingested_b = client.post("/api/ingest", json={"repository_url": repo_b})
    assert ingested_a.status_code == ingested_b.status_code == 200
    repo_a_id = ingested_a.json()["repo_id"]
    repo_b_id = ingested_b.json()["repo_id"]
    assert repo_a_id != repo_b_id
    count_after_b = manager.search_service.get_document_count()
    assert count_after_b == count_after_a + 1

    answer_a = client.post(
        "/api/chat",
        json={"question": "What does get_alpha_balance return?", "repo_id": repo_a_id},
    )
    assert answer_a.status_code == 200
    assert answer_a.json()["sources"]
    assert all(source["file_path"] == "app/alpha.py" for source in answer_a.json()["sources"])
    assert all(source["file_path"] != "internal/beta.py" for source in answer_a.json()["sources"])

    indexed_files[repo_a] = [
        _code_file("app/revised_alpha.py", 'def get_alpha_balance():\n    return "alpha-needle"\n')
    ]
    replaced_a = client.post("/api/ingest", json={"repository_url": repo_a})
    assert replaced_a.status_code == 200
    assert manager.search_service.get_document_count() == count_after_b
    answer_revised = client.post(
        "/api/chat",
        json={"question": "What does get_alpha_balance return?", "repo_id": repo_a_id},
    )
    assert all(source["file_path"] == "app/revised_alpha.py" for source in answer_revised.json()["sources"])

    unscoped = client.post("/api/chat", json={"question": "get alpha balance"})
    assert unscoped.status_code == 200
    assert "No repository selected" in unscoped.json()["answer"]
