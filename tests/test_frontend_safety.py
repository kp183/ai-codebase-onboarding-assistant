from pathlib import Path

from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.main import app
from app.models.data_models import QueryResponse, SourceReference


client = TestClient(app)
MALICIOUS_PATH = '"><img src=x onerror=alert(1)>.py'


def test_malicious_source_path_is_rendered_as_text(monkeypatch):
    class FakeServiceManager:
        async def process_chat_query(self, question, repo_id=None):
            return QueryResponse(
                answer="A safe answer.",
                sources=[
                    SourceReference(
                        file_path=MALICIOUS_PATH,
                        start_line=1,
                        end_line=1,
                        content_preview="safe",
                    )
                ],
                confidence_score=0.5,
                processing_time_ms=1,
            )

    async def fake_get_service_manager():
        return FakeServiceManager()

    monkeypatch.setattr(chat_api, "get_service_manager", fake_get_service_manager)
    response = client.post(
        "/api/chat", json={"question": "show the path", "repo_id": "test-repo"}
    )
    assert response.status_code == 200
    assert response.json()["sources"][0]["file_path"] == MALICIOUS_PATH

    script = (Path(__file__).parents[1] / "static" / "script.js").read_text(encoding="utf-8")
    markup = (Path(__file__).parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "onclick=" not in script
    assert "onclick=" not in markup
    assert "path.textContent = this.truncateFilePath(source.file_path)" in script
    assert "path.title = source.file_path" in script
