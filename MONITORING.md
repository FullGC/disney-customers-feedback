# Disney Customer Feedback API - Monitoring Stack

## Overview

This project includes a complete observability stack for monitoring the Disney Customer Feedback API:

- **OpenTelemetry Collector** - Collects traces, metrics, and logs
- **Prometheus** - Time-series metrics storage
- **Jaeger** - Distributed tracing backend
- **Grafana** - Unified visualization dashboard
- **ChromaDB** - Vector database for semantic search

## Starting the Monitoring Stack

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Access Points

- **Grafana Dashboard**: http://localhost:3000 (username: `admin`, password: `admin`)
- **Prometheus UI**: http://localhost:9090
- **Jaeger Tracing UI**: http://localhost:16687 (changed from default 16686 due to port conflict)
- **ChromaDB**: http://localhost:8001
- **FastAPI App**: http://localhost:8000 (when running)

## Monitoring Architecture

```
FastAPI Application (:8000)
    │
    ├─→ /metrics (Prometheus scrape endpoint)
    │
    └─→ OTLP (traces & metrics)
         │
         ↓
OpenTelemetry Collector (:4317, :4318)
    │
    ├─→ Prometheus Exporter (:8889)
    │    │
    │    ↓
    │   Prometheus (:9090)
    │    │
    │    └─→ Grafana (:3000)
    │
    └─→ OTLP/Jaeger
         │
         ↓
        Jaeger (:16686)
         │
         └─→ Grafana (:3000)
```

## Key Metrics Tracked

### System Metrics
- Request latency (p50, p95, p99)
- Request throughput (requests/sec)
- Error rate
- Active connections

### Application Metrics
- Query processing time
- ChromaDB vector search latency
- Embedding generation time
- LLM inference latency
- Hybrid search strategy selection (ID-filtered vs full search)

### Business Metrics
- Query types (keyword vs hybrid)
- Reviews returned per query
- Branch filter usage
- Location filter usage

## Stopping the Stack

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes all monitoring data)
docker-compose down -v
```

## Troubleshooting

### Services won't start
```bash
# Check logs for specific service
docker-compose logs otel-collector
docker-compose logs prometheus
docker-compose logs grafana

# Restart specific service
docker-compose restart otel-collector
```

### Cannot access Grafana
- Ensure port 3000 is not in use
- Check Grafana logs: `docker-compose logs grafana`
- Try accessing: http://localhost:3000

### Metrics not showing up
- Verify OpenTelemetry Collector is running: `docker-compose ps otel-collector`
- Check collector health: http://localhost:13133
- Verify Prometheus targets: http://localhost:9090/targets

## Next Steps

1. **Add OpenTelemetry instrumentation to FastAPI app**
2. **Create custom Grafana dashboards**
3. **Set up alerting rules in Prometheus**
4. **Add logging to Grafana Loki (optional)**
