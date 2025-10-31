# Disney Customer Feedback API 🏰

A FastAPI application that answers natural language questions about Disney parks using customer reviews. The system uses hybrid search combining keyword matching and semantic similarity for improved results, with comprehensive monitoring and observability through OpenTelemetry, Prometheus, Jaeger, and Grafana.

## Features

- 🔍 **Hybrid Search**: Combines keyword matching and semantic similarity using embeddings
- 🏰 **Disney Parks Support**: Supports multiple Disney locations (California, Hong Kong, Paris)
- 🗺️ **Location Filtering**: Filter reviews by visitor location
- 🤖 **LLM Integration**: Uses GPT-4o-mini for natural language responses
- 📊 **Vector Database**: ChromaDB for semantic search capabilities
- � **Redis Caching**: Semantic similarity-based caching for faster responses and reduced LLM costs
- �🚀 **FastAPI**: Modern, fast API with automatic documentation
- 📈 **Full Observability**: OpenTelemetry instrumentation with Prometheus metrics, Jaeger tracing, and Grafana dashboards
- 🎯 **Performance Monitoring**: Track request latency, search strategies, component performance, and business metrics

## Quick Start

### 1. Prerequisites

- Python 3.13+
- Docker & Docker Compose
- OpenAI API key

### 2. Setup Environment

```bash
# Clone and navigate to project
cd disney_customers_feedback_ex

# Create virtual environment and install dependencies
poetry install

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Start Services

```bash
# Start all services (Redis, ChromaDB, Prometheus, Jaeger, Grafana, OpenTelemetry Collector)
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check service health
curl http://localhost:6379  # Redis (should connect)
curl http://localhost:8001/api/v1/heartbeat  # ChromaDB
curl http://localhost:9090/-/ready           # Prometheus
curl http://localhost:3000/api/health        # Grafana
```

### 4. Prepare Data

Place your `DisneylandReviews.csv` file in:
```
src/disney_customers_feedback_ex/resources/DisneylandReviews.csv
```

### 5. Start the API Server

```bash
# Activate virtual environment
source env_disney_customers_feedback_ex/bin/activate

# Start the server
PYTHONPATH=src python src/disney_customers_feedback_ex/main.py
```

Or use VS Code debugger (F5) with the "FastAPI: Run Server" configuration.

## API Usage

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **FastAPI** | http://localhost:8000 | Main API server |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |
| **Cache Stats** | http://localhost:8000/cache/stats | Redis cache statistics |
| **Grafana** | http://localhost:3000 | Monitoring dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics database |
| **Jaeger** | http://localhost:16687 | Distributed tracing |
| **ChromaDB** | http://localhost:8001 | Vector database |
| **Redis** | localhost:6379 | Cache storage |

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```bash
GET /health
```

#### 2. Root Information
```bash
GET /
```

#### 3. Query Disney Reviews
```bash
POST /query
Content-Type: application/json

{
  "question": "What do visitors from Australia say about Disneyland in Hong Kong?"
}
```

#### 4. Cache Statistics
```bash
GET /cache/stats
```

Returns cache metrics including total entries, hit/miss rates, and Redis memory usage.

#### 5. Clear Cache
```bash
POST /cache/clear
```

Clears all cached queries (useful for testing or cache management).

### Example Queries

Try these natural language questions:

```bash
# Location-specific queries
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What do visitors from Australia say about Disneyland in Hong Kong?"}'

# Seasonal queries  
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is spring a good time to visit Disneyland?"}'

# Crowd queries
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is Disneyland California usually crowded in June?"}'

# Staff queries
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is the staff in Paris friendly?"}'
```

### Response Format

```json
{
  "question": "What do visitors from Australia say about Disneyland in Hong Kong?",
  "answer": "Visitors from Australia generally enjoyed Hong Kong Disneyland for its compact size and shorter wait times compared to other Disney parks. They appreciated the unique attractions and Chinese cultural elements. However, some noted it's smaller than other Disney parks and recommended visiting during weekdays to avoid crowds.",
  "num_reviews_used": 7,
  "cached": false
}
```

**Note**: The `cached` field indicates whether the response was served from Redis cache (true) or generated fresh (false). Cached responses are instant and cost-effective.

## API Documentation

Visit the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Monitoring & Observability

The application includes comprehensive monitoring and observability features. See detailed documentation:

- **[Quick Start Guide](QUICK_START.md)** - Fast setup and common commands
- **[Monitoring Implementation](MONITORING_IMPLEMENTATION.md)** - Technical details and architecture
- **[Grafana Dashboard Guide](GRAFANA_DASHBOARD_GUIDE.md)** - How to use dashboards and interpret metrics
- **[Metrics Reference](METRICS_REFERENCE.md)** - Complete list of available metrics

### Key Metrics Tracked

**Performance Metrics:**
- Request latency (P50, P95, P99)
- Component-level performance (ChromaDB, LLM, Embeddings, Keyword search)
- Error rates and availability

**Business Metrics:**
- Search type distribution (hybrid vs keyword)
- Hybrid search strategy selection (ID-filtered vs full search)
- Reviews returned per query
- Filter usage patterns (branch/location)
- Cache hit/miss rates
- Cache size and similarity scores

### Quick Monitoring Test

```bash
# Run comprehensive monitoring test
./test_e2e_monitoring.sh

# Or test individual components
curl http://localhost:8000/metrics | grep disney_feedback
curl http://localhost:9090/api/v1/targets
```

### Viewing Metrics

1. **Grafana Dashboard**: http://localhost:3000
   - Login: admin/admin
   - Look for "Disney Customer Feedback API - Performance Dashboard"
   - Auto-refreshes every 5 seconds

2. **Jaeger Traces**: http://localhost:16687
   - Search for service: "disney-customer-feedback-api"
   - View detailed request traces and performance breakdowns

3. **Prometheus**: http://localhost:9090
   - Query metrics directly
   - View targets and scraping status

## Architecture

### System Components

1. **FastAPI Server** - REST API endpoints with OpenTelemetry instrumentation
2. **Review Service** - Loads and searches CSV data using pandas with performance metrics
3. **Embedding Service** - Generates text embeddings using sentence-transformers
4. **Vector Store** - ChromaDB for semantic similarity search
5. **Cache Service** - Redis-based semantic caching for query results
6. **LLM Service** - OpenAI GPT-4o-mini integration with latency tracking
7. **Monitoring Stack**:
   - **OpenTelemetry Collector** - Aggregates telemetry data
   - **Prometheus** - Metrics storage and querying
   - **Jaeger** - Distributed tracing
   - **Grafana** - Visualization and dashboarding
8. **Data Storage**:
   - **Redis** - Query cache with automatic expiration (24h TTL)
   - **ChromaDB** - Vector embeddings for semantic search

### Search Flow

1. **Cache Check** - Check Redis for similar cached questions (cosine similarity ≥ 0.95)
2. **Cache Hit** - Return cached answer instantly (no LLM call needed)
3. **Cache Miss** - Proceed with full search and LLM generation:
   - **Query Processing** - Extract location/branch filters from natural language
   - **Pandas Filtering** - Fast metadata filtering (branch, location, dates)
   - **Hybrid Search**:
     - **Keyword Search** - Text matching with relevance scoring
     - **Semantic Search** - Vector similarity using embeddings
     - **Score Combination** - Weighted combination of both approaches
   - **Context Building** - Format top reviews with metadata
   - **LLM Generation** - Send context to GPT-4o-mini for answer generation
4. **Cache Store** - Save question-answer pair to Redis for future similar queries

## Testing

### Run Integration Tests

```bash
# Start the server first, then run tests
source env_disney_customers_feedback_ex/bin/activate
pytest tests/test_integration.py -v
```

### Test Individual Components

```bash
# Test specific functions
pytest tests/ -k "test_query_endpoint" -v
```

## Development

### Project Structure

```
disney_customers_feedback_ex/
├── src/disney_customers_feedback_ex/
│   ├── main.py                 # FastAPI application with telemetry
│   ├── core/
│   │   ├── logging.py          # Logging configuration
│   │   ├── telemetry.py        # OpenTelemetry setup
│   │   └── metrics.py          # Custom metrics definitions
│   ├── services/
│   │   ├── review_service.py   # CSV data loading & search (instrumented)
│   │   ├── embedding_service.py # Text embedding generation
│   │   ├── vector_store.py     # ChromaDB integration
│   │   ├── cache_service.py    # Redis caching with semantic similarity
│   │   └── llm_service.py      # OpenAI integration
│   └── resources/
│       └── DisneylandReviews.csv
├── tests/
│   └── test_integration.py     # API integration tests
├── grafana/
│   ├── provisioning/           # Grafana datasources & dashboard config
│   │   ├── datasources/
│   │   └── dashboards/
│   └── dashboards/             # Dashboard JSON files
├── docker-compose.yml          # All services (Redis, ChromaDB, monitoring stack)
├── prometheus.yml              # Prometheus configuration
├── otel-collector-config.yaml # OpenTelemetry Collector config
├── test_e2e_monitoring.sh     # End-to-end monitoring test
├── test_monitoring.sh          # Basic monitoring test
├── test_redis_cache.py         # Redis connectivity test
├── pyproject.toml             # Dependencies
├── README.md                  # This file
├── QUICK_START.md             # Quick reference guide
├── MONITORING_IMPLEMENTATION.md # Monitoring details
├── GRAFANA_DASHBOARD_GUIDE.md  # Dashboard usage guide
└── METRICS_REFERENCE.md        # Metrics documentation
```

### Adding New Features

1. **New Endpoints**: Add to `main.py`
2. **Search Logic**: Modify `review_service.py`
3. **LLM Prompts**: Update `llm_service.py`
4. **Tests**: Add to `tests/` directory

## Troubleshooting

### Common Issues

1. **ChromaDB Connection Failed**
   ```bash
   # Check if ChromaDB is running
   docker-compose ps
   
   # Restart if needed
   docker-compose restart chromadb
   ```

2. **Redis Connection Failed**
   ```bash
   # Check if Redis is running
   docker-compose ps
   
   # Test Redis connectivity
   python test_redis_cache.py
   
   # Restart if needed
   docker-compose restart redis
   
   # Check Redis logs
   docker-compose logs redis
   ```

3. **Metrics Not Showing in Grafana**
   ```bash
   # Verify all monitoring services are running
   docker-compose ps
   
   # Check Prometheus is scraping the app
   curl http://localhost:9090/api/v1/targets
   
   # Verify metrics endpoint
   curl http://localhost:8000/metrics | grep disney_feedback
   
   # Run comprehensive test
   ./test_e2e_monitoring.sh
   ```

4. **Dashboard Not Loading**
   ```bash
   # Restart Grafana with fresh state
   docker-compose stop grafana
   docker-compose rm -f grafana
   docker volume rm disney_customers_feedback_ex_grafana-data
   docker-compose up -d grafana
   ```

5. **Cache Not Working**
   ```bash
   # Check cache stats
   curl http://localhost:8000/cache/stats
   
   # Clear cache if needed
   curl -X POST http://localhost:8000/cache/clear
   
   # Check Redis memory usage
   docker exec disney_redis redis-cli INFO memory
   ```

6. **CSV Encoding Issues**
   - The system automatically tries multiple encodings (utf-8, latin-1, iso-8859-1, cp1252)
   - Check logs for which encoding was used

7. **OpenAI API Errors**
   - Verify your API key in `.env`
   - Check rate limits and billing status

8. **Memory Issues with Large Datasets**
   - Embeddings are generated in batches of 3000
   - Consider reducing batch size for very large datasets

### Logs

Check application logs for detailed information:
```bash
# The application logs to stdout with structured formatting
# Look for startup messages, search operations, and error details
```

## Performance Considerations

- **Embedding Generation**: Done once at startup, cached in ChromaDB
- **Search Performance**: Pandas filtering is very fast for metadata, ChromaDB handles vector similarity
- **Hybrid Search Strategies**: 
  - ID-filtered search when sufficient candidates (>= 5x max_results)
  - Full search with post-filtering for better coverage with fewer candidates
- **Caching**: 
  - Redis-based semantic similarity caching (cosine similarity ≥ 0.95)
  - 24-hour TTL for cache entries
  - Instant responses for cached queries (no LLM latency or cost)
  - Average cache hit rate: ~30-40% for similar questions
- **Memory Usage**: Full dataset loaded in memory for fast filtering
- **Scalability**: Current setup suitable for datasets up to ~100K reviews
- **Monitoring Overhead**: OpenTelemetry adds ~1-5ms per request
- **Metrics Export**: Batched every 5 seconds to minimize performance impact

## Documentation

- **[README.md](README.md)** - Main documentation (this file)
- **[QUICK_START.md](QUICK_START.md)** - Quick reference for daily use
- **[REDIS_CACHE_GUIDE.md](REDIS_CACHE_GUIDE.md)** - Redis caching implementation and tuning
- **[MONITORING_IMPLEMENTATION.md](MONITORING_IMPLEMENTATION.md)** - Technical monitoring details
- **[GRAFANA_DASHBOARD_GUIDE.md](GRAFANA_DASHBOARD_GUIDE.md)** - Dashboard usage and metrics interpretation
- **[METRICS_REFERENCE.md](METRICS_REFERENCE.md)** - Complete metrics catalog

## License

This project is for educational/interview purposes.
