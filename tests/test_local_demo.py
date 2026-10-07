from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.service_manager import get_service_manager_sync


client = TestClient(app)
FIXTURE = str(Path(__file__).parent / "fixtures" / "sample_repo")


def test_fixture_ingest_is_idempotent_and_chat_is_grounded():
    first = client.post("/api/ingest", json={"repository_url": FIXTURE})
    assert first.status_code == 200, first.text
    assert first.json()["chunks_indexed"] > 0
    manager = get_service_manager_sync()
    count_after_first = manager.search_service.get_document_count()

    second = client.post("/api/ingest", json={"repository_url": FIXTURE})
    assert second.status_code == 200, second.text
    assert manager.search_service.get_document_count() == count_after_first

    answer = client.post("/api/chat", json={"question": "How does calculate_total add item prices?"})
    assert answer.status_code == 200, answer.text
    data = answer.json()
    assert "Retrieval-only answer" in data["answer"]
    assert any(source["file_path"] == "app/cart.py" for source in data["sources"])
    assert "app/cart.py:" in data["answer"]

    missing = client.post("/api/chat", json={"question": "Explain Kubernetes deployment secrets"})
    assert missing.status_code == 200, missing.text
    assert "Not found in repo" in missing.json()["answer"]
