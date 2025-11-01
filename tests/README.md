# Integration Tests

This directory contains comprehensive integration tests for the Disney Customer Feedback API.

## Test Coverage

### Basic Endpoints (6 tests)
- ✅ Root endpoint (`/`)
- ✅ Health check (`/health`)
- ✅ Metrics endpoint (`/metrics`)
- ✅ Cache statistics (`/cache/stats`)
- ✅ Cache clear (`/cache/clear`)
- ✅ Query endpoint

### Query Functionality (8 tests)
- ✅ Branch filtering (California, Hong Kong, Paris)
- ✅ Location filtering (Australia)
- ✅ Multiple filters combination
- ✅ Case-insensitive filters
- ✅ Comparative questions
- ✅ Specific attraction queries

### Caching (5 tests)
- ✅ Cache hit/miss functionality
- ✅ Semantic similarity caching
- ✅ Cache statistics
- ✅ Cache clearing
- ✅ Cache performance (speed comparison)

### Edge Cases (7 tests)
- ✅ Empty questions
- ✅ Very long questions
- ✅ Special characters
- ✅ Invalid requests
- ✅ Concurrent queries
- ✅ Numeric questions
- ✅ Questions with dates

### Content Variety (10 tests)
- ✅ Positive/negative sentiment questions
- ✅ Family-oriented questions
- ✅ Accessibility questions
- ✅ Specific attractions

### Parametrized Tests (3 test groups)
- ✅ All GET endpoints (4 variations)
- ✅ All branches (3 variations)
- ✅ Different topics (5 variations)

## Running Tests

### Prerequisites

1. **Start the infrastructure:**
   ```bash
   docker-compose up -d
   ```

2. **Start the FastAPI application:**
   ```bash
   source env_disney_customers_feedback_ex/bin/activate
   python -m uvicorn disney_customers_feedback_ex.main:app --host 0.0.0.0 --port 8000
   ```

### Run All Tests

```bash
# Run all integration tests
pytest tests/test_integration.py -v

# Run with coverage
pytest tests/test_integration.py -v --cov=disney_customers_feedback_ex

# Run specific test
pytest tests/test_integration.py::test_cache_functionality -v

# Run tests matching a pattern
pytest tests/test_integration.py -k "cache" -v

# Run parametrized tests
pytest tests/test_integration.py -k "test_all_branches" -v
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/test_integration.py -v -n auto
```

## Test Metrics

- **Total Tests**: 40+
- **Endpoints Covered**: 6
- **Query Variations**: 20+
- **Filter Combinations**: 5+
- **Edge Cases**: 7+

## Expected Results

All tests should pass when:
- ✅ FastAPI application is running on `http://localhost:8000`
- ✅ Redis is running and accessible
- ✅ ChromaDB is running and accessible
- ✅ OpenAI API key is configured (for LLM queries)

## Common Issues

### Tests Fail: "Connection refused"
**Solution**: Ensure the FastAPI app is running:
```bash
python -m uvicorn disney_customers_feedback_ex.main:app --host 0.0.0.0 --port 8000
```

### Tests Timeout
**Solution**: Increase timeout for slow queries:
```python
response = httpx.post(
    f"{BASE_URL}/query",
    json={"question": "..."},
    timeout=60.0  # Increase from 30.0
)
```

### Cache Tests Fail
**Solution**: Ensure Redis is running:
```bash
docker-compose up redis -d
```

## Performance Benchmarks

Expected performance (on local machine):

| Test Category | Expected Duration |
|--------------|-------------------|
| Basic Endpoints | < 1s |
| Cached Queries | < 200ms |
| Uncached Queries | 2-5s |
| Full Test Suite | 2-5 minutes |
