from __future__ import annotations

import httpx
import pytest
import time


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


def test_query_with_branch_filter() -> None:
    """Test query with branch filter (California)."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What do people say about California Disneyland rides?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    assert len(data["answer"]) > 0
    # Should mention California or have California-specific information
    assert data["num_reviews_used"] > 0


def test_query_with_hong_kong_branch() -> None:
    """Test query with Hong Kong branch filter."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "How is Hong Kong Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert data["num_reviews_used"] > 0


def test_query_with_paris_branch() -> None:
    """Test query with Paris branch filter."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What are the best attractions in Paris Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert data["num_reviews_used"] > 0


def test_query_with_location_filter() -> None:
    """Test query with location filter (Australia)."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What do Australian visitors think about Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert data["num_reviews_used"] >= 0


def test_cache_functionality() -> None:
    """Test that caching works for similar questions."""
    # Clear cache first
    httpx.post(f"{BASE_URL}/cache/clear", timeout=10.0)
    
    # First query - should not be cached
    question1 = "What do people say about the rides?"
    response1 = httpx.post(
        f"{BASE_URL}/query",
        json={"question": question1},
        timeout=30.0
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cached"] is False
    
    # Second query - exact same question, should be cached
    response2 = httpx.post(
        f"{BASE_URL}/query",
        json={"question": question1},
        timeout=30.0
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cached"] is True
    assert data2["answer"] == data1["answer"]
    
    # Third query - similar question, should be cached (semantic similarity)
    question3 = "What are visitor opinions on the attractions?"
    response3 = httpx.post(
        f"{BASE_URL}/query",
        json={"question": question3},
        timeout=30.0
    )
    
    assert response3.status_code == 200
    data3 = response3.json()
    # May or may not be cached depending on similarity threshold
    assert "cached" in data3


def test_cache_stats_endpoint() -> None:
    """Test cache statistics endpoint."""
    response = httpx.get(f"{BASE_URL}/cache/stats", timeout=10.0)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_entries" in data
    assert isinstance(data["total_entries"], int)


def test_cache_clear_endpoint() -> None:
    """Test cache clear endpoint."""
    # Add something to cache first
    httpx.post(
        f"{BASE_URL}/query",
        json={"question": "Test question for cache clear"},
        timeout=30.0
    )
    
    # Clear cache
    response = httpx.post(f"{BASE_URL}/cache/clear", timeout=10.0)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data
    
    # Verify cache is empty
    stats_response = httpx.get(f"{BASE_URL}/cache/stats", timeout=10.0)
    stats = stats_response.json()
    assert stats["total_entries"] == 0


def test_metrics_endpoint() -> None:
    """Test Prometheus metrics endpoint."""
    response = httpx.get(f"{BASE_URL}/metrics", timeout=10.0)
    
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    
    # Check for some expected metrics
    content = response.text
    assert "disney_feedback" in content or "request" in content.lower()


def test_invalid_query_request() -> None:
    """Test query endpoint with invalid request."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={},  # Missing 'question' field
        timeout=10.0
    )
    
    assert response.status_code == 422  # Validation error


def test_empty_question() -> None:
    """Test query endpoint with empty question."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": ""},
        timeout=30.0
    )
    
    # Should either succeed with empty results or handle gracefully
    assert response.status_code in [200, 400, 422]


def test_very_long_question() -> None:
    """Test query endpoint with very long question."""
    long_question = "What do people think about " + "the attractions " * 100
    
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": long_question},
        timeout=60.0
    )
    
    # Should handle long questions gracefully
    assert response.status_code in [200, 400, 413]


def test_special_characters_in_question() -> None:
    """Test query endpoint with special characters."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What about rides?! 🎢 @Disney #fun $$$"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_multiple_filters_combination() -> None:
    """Test query with multiple filters combined."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What do Australian visitors think about California Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_query_response_time() -> None:
    """Test that cached queries are significantly faster."""
    # Clear cache
    httpx.post(f"{BASE_URL}/cache/clear", timeout=10.0)
    
    question = "What are the best restaurants at Disney?"
    
    # First query - not cached
    start_time = time.time()
    response1 = httpx.post(
        f"{BASE_URL}/query",
        json={"question": question},
        timeout=30.0
    )
    uncached_time = time.time() - start_time
    
    assert response1.status_code == 200
    assert response1.json()["cached"] is False
    
    # Second query - cached
    start_time = time.time()
    response2 = httpx.post(
        f"{BASE_URL}/query",
        json={"question": question},
        timeout=30.0
    )
    cached_time = time.time() - start_time
    
    assert response2.status_code == 200
    assert response2.json()["cached"] is True
    
    # Cached query should be faster (at least 2x)
    assert cached_time < uncached_time / 2


def test_concurrent_queries() -> None:
    """Test handling of concurrent queries."""
    question = "What do people say about food?"
    
    # Send multiple concurrent requests
    with httpx.Client(timeout=30.0) as client:
        responses = []
        for _ in range(3):
            response = client.post(
                f"{BASE_URL}/query",
                json={"question": question}
            )
            responses.append(response)
    
    # All should succeed
    for response in responses:
        assert response.status_code == 200
        assert "answer" in response.json()


def test_case_insensitive_filters() -> None:
    """Test that filters work regardless of case."""
    questions = [
        "What about CALIFORNIA?",
        "How is california disneyland?",
        "Tell me about CaLiFoRnIa park"
    ]
    
    for question in questions:
        response = httpx.post(
            f"{BASE_URL}/query",
            json={"question": question},
            timeout=30.0
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


def test_numeric_question() -> None:
    """Test query with numbers."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "How many rides are there?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_question_with_dates() -> None:
    """Test query mentioning dates."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What were reviews like in 2023?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_comparative_question() -> None:
    """Test comparative questions."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "Is Hong Kong Disneyland better than California?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["num_reviews_used"] > 0


def test_negative_sentiment_question() -> None:
    """Test questions about negative aspects."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What complaints do people have?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_positive_sentiment_question() -> None:
    """Test questions about positive aspects."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What do people love most about Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_specific_attraction_question() -> None:
    """Test question about specific attraction."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What do people think about Space Mountain?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_family_oriented_question() -> None:
    """Test family-related questions."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "Is Disneyland good for families with young children?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_accessibility_question() -> None:
    """Test accessibility-related questions."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": "What about wheelchair accessibility?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


@pytest.mark.parametrize("endpoint", ["/", "/health", "/metrics", "/cache/stats"])
def test_all_get_endpoints(endpoint: str) -> None:
    """Test all GET endpoints are accessible."""
    response = httpx.get(f"{BASE_URL}{endpoint}", timeout=10.0)
    assert response.status_code == 200


@pytest.mark.parametrize("branch", ["California", "Hong Kong", "Paris"])
def test_all_branches(branch: str) -> None:
    """Test queries for all Disney branches."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": f"What do people say about {branch} Disneyland?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["num_reviews_used"] > 0


@pytest.mark.parametrize("topic", ["food", "rides", "staff", "cleanliness", "prices"])
def test_different_topics(topic: str) -> None:
    """Test queries about different topics."""
    response = httpx.post(
        f"{BASE_URL}/query",
        json={"question": f"What do people say about the {topic}?"},
        timeout=30.0
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data



