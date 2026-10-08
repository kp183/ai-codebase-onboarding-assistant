from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_cors_allows_local_ui_origin_and_rejects_unlisted_origin():
    allowed = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:8002",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:8002"

    rejected = client.options(
        "/api/chat",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_debug_routes_are_removed():
    assert client.get("/api/debug/service-status").status_code == 404
    assert client.get("/api/health/debug").status_code == 404
