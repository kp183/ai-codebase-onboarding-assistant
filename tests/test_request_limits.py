from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.main import app
from app.middleware import RequestLimitsMiddleware


def _limited_app(body_limit=64, chat_limit=30):
    test_app = FastAPI()

    @test_app.post("/api/chat")
    async def chat(payload: dict):
        return {"ok": True}

    @test_app.post("/api/ingest")
    async def ingest(payload: dict):
        return {"ok": True}

    test_app.add_middleware(
        RequestLimitsMiddleware,
        max_body_bytes=body_limit,
        route_limits={"/api/chat": chat_limit, "/api/ingest": chat_limit},
        window_seconds=60,
    )
    return test_app


def test_request_body_size_limit():
    client = TestClient(_limited_app(body_limit=16))
    assert client.post("/api/chat", json={"x": "ok"}).status_code == 200
    too_large = client.post("/api/chat", content=b'{"x":"' + b"a" * 40 + b'"}')
    assert too_large.status_code == 413
    assert too_large.json()["detail"] == "Request body exceeds the allowed size."


def test_chat_rate_limit():
    client = TestClient(_limited_app(chat_limit=1))
    assert client.post("/api/chat", json={"question": "one"}).status_code == 200
    limited = client.post("/api/chat", json={"question": "two"})
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
    assert limited.json()["detail"] == "Rate limit exceeded. Try again shortly."


def test_ingest_rate_limit():
    client = TestClient(_limited_app(chat_limit=1))
    assert client.post("/api/ingest", json={"repository_url": "one"}).status_code == 200
    limited = client.post("/api/ingest", json={"repository_url": "two"})
    assert limited.status_code == 429


def test_chat_errors_do_not_expose_exception_text(monkeypatch):
    class BrokenServiceManager:
        async def process_chat_query(self, question, repo_id=None):
            raise RuntimeError("private credential value")

    async def fake_get_service_manager():
        return BrokenServiceManager()

    monkeypatch.setattr(chat_api, "get_service_manager", fake_get_service_manager)
    response = TestClient(app).post(
        "/api/chat", json={"question": "anything", "repo_id": "test"}
    )
    assert response.status_code == 500
    assert "private credential value" not in response.text
    assert response.json()["detail"] == "Chat request failed unexpectedly. Please try again."
