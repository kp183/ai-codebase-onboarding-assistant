"""
Tests for chat API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_endpoint_structure():
    """Test chat endpoint accepts correct request format and returns correct response structure."""
    request_data = {
        "question": "What is this codebase about?",
        "session_id": "test-session-123"
    }
    
    response = client.post("/api/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure matches ChatResponse model
    assert "answer" in data
    assert "sources" in data
    assert "confidence_score" in data
    assert "processing_time_ms" in data
    assert "timestamp" in data
    
    # Verify data types
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["confidence_score"], (int, float))
    assert isinstance(data["processing_time_ms"], int)
    assert isinstance(data["timestamp"], str)


def test_chat_endpoint_without_session_id():
    """Test chat endpoint works without optional session_id."""
    request_data = {
        "question": "How does this system work?"
    }
    
    response = client.post("/api/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_chat_endpoint_missing_question():
    """Test chat endpoint returns error when question is missing."""
    request_data = {}
    
    response = client.post("/api/chat", json=request_data)
    
    assert response.status_code == 422  # Validation error


def test_predefined_where_to_start():
    """Test predefined 'where to start' endpoint returns correct response structure."""
    response = client.get("/api/predefined/where-to-start")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure matches ChatResponse model
    assert "answer" in data
    assert "sources" in data
    assert "confidence_score" in data
    assert "processing_time_ms" in data
    assert "timestamp" in data
    
    # Verify data types
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["confidence_score"], (int, float))
    assert isinstance(data["processing_time_ms"], int)
    assert isinstance(data["timestamp"], str)


def test_chat_endpoint_empty_question():
    """Test chat endpoint handles empty question string."""
    request_data = {
        "question": ""
    }
    
    response = client.post("/api/chat", json=request_data)
    
    # Should still return 200 with placeholder response for now
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data