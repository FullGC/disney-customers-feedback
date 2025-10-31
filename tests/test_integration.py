from __future__ import annotations

import httpx


BASE_URL = "http://localhost:8000"


def test_root_endpoint() -> None:
    """Test the root endpoint returns welcome message."""
    response = httpx.get(f"{BASE_URL}/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "message" in data
    assert "Welcome to Disney Customer Feedback API" in data["message"]
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_health_check_endpoint() -> None:
    """Test the health check endpoint."""
    response = httpx.get(f"{BASE_URL}/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "disney-customer-feedback-api"


def test_query_endpoint() -> None:
    """Test the LLM query endpoint."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What is Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "question" in data
    assert "answer" in data
    assert "num_reviews_used" in data
    assert data["question"] == "What is Disneyland?"
    assert len(data["answer"]) > 0
    assert isinstance(data["answer"], str)
    assert isinstance(data["num_reviews_used"], int)
    assert data["num_reviews_used"] >= 0


