# Disney Customer Feedback API - Monitoring Implementation

## Overview

This document describes the comprehensive monitoring setup for the Disney Customer Feedback API using OpenTelemetry, Prometheus, Jaeger, and Grafana.

## Architecture

```
┌─────────────────┐
│   FastAPI App   │ (Port 8000)
│   /query        │
│   /metrics      │
└────────┬────────┘
         │
         │ OpenTelemetry SDK
         │ (Traces & Metrics)
         ▼
┌─────────────────────────┐
│  OpenTelemetry          │ (Ports 4317/4318)
│  Collector              │
│  - OTLP Receiver        │
│  - Batch Processor      │
│  - Resource Detection   │
└────┬───────────────┬────┘
     │               │
     │ Traces        │ Metrics
     │               │
     ▼               ▼
┌─────────┐    ┌────────────┐
│ Jaeger  │    │ Prometheus │ (Port 9090)
│  UI     │    │  + Scraper │
│         │    └─────┬──────┘
└─────────┘          │
(Port 16687)         │
                     ▼
              ┌──────────────┐
              │   Grafana    │ (Port 3000)
              │  Dashboards  │
              │   (Viz)      │
              └──────────────┘
```

## Components

### 1. FastAPI Application Instrumentation

#### Automatic Instrumentation
- **FastAPIInstrumentor**: Automatically traces all HTTP requests
  - Request/response spans
  - HTTP method, path, status code
  - Duration tracking

- **HTTPXClientInstrumentor**: Traces outbound HTTP calls
  - OpenAI API calls
  - ChromaDB requests

#### Custom Metrics (`core/metrics.py`)

**Request Metrics:**
- `disney_api_request_duration_seconds` (histogram): Request latency by endpoint/method/status
- `disney_api_request_count` (counter): Total requests by endpoint/method/status
- `disney_api_error_count` (counter): Error count by endpoint/method/status

**Search Metrics:**
- `disney_api_search_type_count` (counter): Search type distribution (keyword/hybrid)
- `disney_api_reviews_returned` (histogram): Number of reviews per query

**Component Latency Metrics:**
- `disney_api_chromadb_search_duration_seconds` (histogram): Vector search latency
- `disney_api_embedding_generation_duration_seconds` (histogram): Embedding generation time
- `disney_api_llm_inference_duration_seconds` (histogram): LLM API call duration
- `disney_api_keyword_search_duration_seconds` (histogram): Pandas keyword search time

**Filter Usage Metrics:**
- `disney_api_filter_usage_count` (counter): Filter usage by type (branch/location/both)

**Hybrid Search Metrics:**
- `disney_api_hybrid_strategy_count` (counter): Strategy selection (id_filtered/full_search)
- `disney_api_candidate_count` (histogram): Number of candidates from pandas filtering

#### Custom Traces

**Query Endpoint Span:**
- Question text
- Filter detection (branch/location)
- Number of reviews used

**Search Reviews Span:**
- Search type (keyword/hybrid)
- Number of results

**LLM Query Span:**
- Number of reviews in context
- Answer length
- Model name

**Embedding & Vector Search Spans:**
- Operation type
- Strategy used (id_filtered/full_search)
- Duration measurements

### 2. OpenTelemetry Collector

**Configuration** (`otel-collector-config.yaml`):

**Receivers:**
- OTLP gRPC: `:4317`
- OTLP HTTP: `:4318`

**Processors:**
- `batch`: Batches telemetry data for efficiency
- `memory_limiter`: Prevents OOM (80% soft, 90% hard limit)
- `resourcedetection`: Adds environment metadata (host, process, OS)

**Exporters:**
- `prometheus`: Exposes metrics on `:8889/metrics`
- `otlp/jaeger`: Sends traces to Jaeger (`:4317`)
- `debug`: Logs samples for debugging (detailed verbosity, sampling 0.1)

**Service Pipelines:**
```yaml
traces:
  receivers: [otlp]
  processors: [memory_limiter, resourcedetection, batch]
  exporters: [otlp/jaeger, debug]

metrics:
  receivers: [otlp]
  processors: [memory_limiter, resourcedetection, batch]
  exporters: [prometheus, debug]
```

### 3. Prometheus

**Configuration** (`prometheus.yml`):

**Scrape Targets:**
1. **otel-collector** (`:8889/metrics`): OTLP metrics from FastAPI app
2. **fastapi-app** (`:8000/metrics`): Direct Prometheus metrics endpoint
3. **prometheus** (`:9090/metrics`): Self-monitoring

**Retention:** Default 15 days

**Web UI:** http://localhost:9090

### 4. Jaeger

**Configuration:**
- OTLP gRPC endpoint: `:4317` (for traces from OTel Collector)
- Web UI: http://localhost:16687

**Note:** Port 16687 is used instead of default 16686 due to SSH tunnel conflict.

### 5. Grafana

**Configuration:**
- Web UI: http://localhost:3000 (admin/admin)

**Provisioned Datasources:**
1. **Prometheus** (default)
   - URL: http://prometheus:9090
   - Query metrics and build dashboards

2. **Jaeger**
   - URL: http://jaeger:16686
   - View distributed traces

**Dashboard Provisioning:**
- Located in `grafana/provisioning/dashboards/`
- Auto-loads dashboards on startup

## Running the Stack

### Start All Services

```bash
docker-compose up -d
```

This starts:
- ChromaDB (port 8001)
- OpenTelemetry Collector (ports 4317, 4318, 8889)
- Prometheus (port 9090)
- Jaeger (ports 16687, 4317)
- Grafana (port 3000)

### Start FastAPI Application

```bash
# Activate virtual environment
source env_disney_customers_feedback_ex/bin/activate

# Start with uvicorn
python -m uvicorn disney_customers_feedback_ex.main:app --host 0.0.0.0 --port 8000
```

### Test Monitoring

```bash
# Run test script
./test_monitoring.sh
```

This will:
1. Test health endpoint
2. Check metrics endpoint
3. Send test queries
4. Verify Prometheus targets
5. Check OpenTelemetry Collector health

## Viewing Telemetry Data

### Metrics in Prometheus

1. Open http://localhost:9090
2. Go to "Graph" tab
3. Example queries:
   ```promql
   # Request rate by endpoint
   rate(disney_api_request_count[5m])
   
   # P95 latency
   histogram_quantile(0.95, rate(disney_api_request_duration_seconds_bucket[5m]))
   
   # Error rate
   rate(disney_api_error_count[5m])
   
   # Hybrid search strategy distribution
   disney_api_hybrid_strategy_count
   
   # ChromaDB search latency
   histogram_quantile(0.99, rate(disney_api_chromadb_search_duration_seconds_bucket[5m]))
   ```

### Traces in Jaeger

1. Open http://localhost:16687
2. Select service: `disney-customer-feedback-api`
3. Click "Find Traces"
4. Explore:
   - Request flow
   - Component latencies
   - Error traces
   - Dependency graph

### Dashboards in Grafana

1. Open http://localhost:3000 (admin/admin)
2. Go to "Dashboards"
3. Create new dashboard or import existing
4. Add panels with Prometheus queries:
   - Request rate and latency
   - Error rates
   - Search performance
   - LLM inference time
   - ChromaDB operations
   - Hybrid search strategy distribution

## Key Metrics to Monitor

### Performance Metrics
- **Request Latency**: P50, P95, P99 for `/query` endpoint
- **Component Latency Breakdown**:
  - Embedding generation: ~100-500ms
  - ChromaDB search: ~10-100ms
  - LLM inference: ~500-2000ms
  - Keyword search: ~1-10ms

### Business Metrics
- **Search Type Distribution**: Hybrid vs keyword usage
- **Hybrid Strategy Selection**: ID-filtered vs full search
- **Reviews Returned**: Distribution of result counts
- **Filter Usage**: Branch/location filter popularity

### Reliability Metrics
- **Error Rate**: 4xx and 5xx responses
- **Availability**: Uptime percentage
- **Service Dependencies**: ChromaDB, OpenAI API availability

## Troubleshooting

### No Metrics in Prometheus

1. Check FastAPI app is running: `curl http://localhost:8000/metrics`
2. Check OTel Collector: `curl http://localhost:8889/metrics`
3. Check Prometheus targets: http://localhost:9090/targets

### No Traces in Jaeger

1. Check OTel Collector logs: `docker-compose logs otel-collector`
2. Verify FastAPI app startup logs show: "OpenTelemetry instrumentation enabled"
3. Send test query: `curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"question": "test"}'`

### Grafana Datasource Issues

1. Check datasource config: `cat grafana/provisioning/datasources/datasources.yaml`
2. Test connectivity from Grafana container:
   ```bash
   docker-compose exec grafana curl http://prometheus:9090/-/healthy
   docker-compose exec grafana curl http://jaeger:16686
   ```

## Performance Impact

**Instrumentation Overhead:**
- Traces: ~1-5ms per request
- Metrics: <1ms per request
- Total: ~2-10ms (negligible for LLM-based queries)

**Resource Usage:**
- FastAPI app: +~50MB memory for OpenTelemetry SDK
- OTel Collector: ~100-200MB memory
- Prometheus: ~500MB-1GB (depends on retention)
- Jaeger: ~500MB-1GB
- Grafana: ~200-300MB

## Future Improvements

1. **Alerting**: Set up Prometheus AlertManager for critical metrics
2. **Custom Dashboards**: Create comprehensive Grafana dashboards
3. **Log Aggregation**: Add Loki for log centralization
4. **Distributed Tracing**: Add trace sampling for high-volume scenarios
5. **Service Level Objectives (SLOs)**: Define and track SLIs/SLOs
6. **Cost Tracking**: Monitor OpenAI API costs via custom metrics

## References

- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- Prometheus: https://prometheus.io/docs/
- Jaeger: https://www.jaegertracing.io/docs/
- Grafana: https://grafana.com/docs/

## Monitoring Checklist

- [x] OpenTelemetry SDK installed and configured
- [x] Automatic instrumentation (FastAPI, HTTPX)
- [x] Custom metrics implemented
- [x] Custom traces implemented
- [x] Prometheus metrics endpoint exposed
- [x] OpenTelemetry Collector configured
- [x] Prometheus scraping configured
- [x] Jaeger tracing enabled
- [x] Grafana datasources provisioned
- [ ] Grafana dashboards created
- [ ] Test queries validated
- [ ] Performance baseline established
- [ ] Alerting rules defined
