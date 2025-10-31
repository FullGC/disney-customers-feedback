# 🚀 Quick Start Guide - Disney Customer Feedback API Monitoring

## One-Time Setup

```bash
# 1. Start monitoring stack
docker-compose up -d

# 2. Start FastAPI app
source env_disney_customers_feedback_ex/bin/activate
python -m uvicorn disney_customers_feedback_ex.main:app --host 0.0.0.0 --port 8000
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Jaeger** | http://localhost:16687 | - |
| **FastAPI** | http://localhost:8000/docs | - |
| **Metrics** | http://localhost:8000/metrics | - |

## Quick Tests

```bash
# Test everything
./test_e2e_monitoring.sh

# Test API health
curl http://localhost:8000/health

# Test query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do people say about the rides?"}'

# View metrics
curl http://localhost:8000/metrics | grep disney_feedback
```

## Key Metrics to Monitor

### In Grafana Dashboard
1. **Total Requests** - Should increase with traffic
2. **Errors** - Should be 0 (green)
3. **P95 Latency** - Should be < 1s (green)
4. **Component Breakdown** - Shows where time is spent

### In Prometheus
```promql
# Request rate
rate(disney_feedback_requests_total[1m])

# P95 latency
histogram_quantile(0.95, rate(disney_feedback_request_duration_seconds_bucket[5m]))

# Search type distribution
sum by (search_type) (disney_feedback_search_type_total)

# Error count
sum(increase(disney_feedback_requests_total{status=~"5.."}[1h]))
```

## Troubleshooting

### No metrics in Prometheus?
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Check FastAPI metrics endpoint
curl http://localhost:8000/metrics | head -30
```

### Dashboard not loading in Grafana?
```bash
# Restart Grafana
docker-compose restart grafana

# Check Grafana logs
docker-compose logs grafana --tail=50
```

### Can't connect to services from Grafana?
- ✅ Use: `http://prometheus:9090` (Docker network)
- ❌ Don't use: `http://localhost:9090` (from inside container)

## File Structure

```
disney_customers_feedback_ex/
├── docker-compose.yml                    # All services
├── prometheus.yml                        # Prometheus config
├── otel-collector-config.yaml           # OpenTelemetry config
├── test_e2e_monitoring.sh               # Complete test
├── test_monitoring.sh                   # Basic test
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yaml        # Prometheus + Jaeger
│   │   └── dashboards/
│   │       └── dashboard.yaml          # Dashboard provisioning
│   └── dashboards/
│       └── disney-feedback-dashboard.json  # Main dashboard
├── src/disney_customers_feedback_ex/
│   ├── main.py                          # FastAPI app with instrumentation
│   ├── core/
│   │   ├── telemetry.py                # OpenTelemetry setup
│   │   └── metrics.py                  # Custom metrics
│   └── services/
│       └── review_service.py           # Instrumented search
└── GRAFANA_DASHBOARD_GUIDE.md          # Detailed documentation
```

## Common Commands

```bash
# Restart all services
docker-compose restart

# View service logs
docker-compose logs -f grafana
docker-compose logs -f prometheus
docker-compose logs -f otel-collector

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Check service status
docker-compose ps

# Send test query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do people say about Hong Kong Disneyland?"}'
```

## Performance Expectations

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| P95 Latency | < 1s | 1-3s | > 3s |
| P99 Latency | < 2s | 2-5s | > 5s |
| Error Rate | 0% | < 1% | > 1% |
| Availability | 100% | 99%+ | < 99% |

## Component Latency Breakdown (Typical)

- **LLM (OpenAI)**: 60-80% of total time
- **ChromaDB**: 10-20% of total time
- **Embeddings**: 5-10% of total time
- **Keyword Search**: 1-5% of total time

## Next Steps

1. ✅ Import dashboard in Grafana
2. ✅ Run `./test_e2e_monitoring.sh`
3. ✅ Send some test queries
4. ✅ View metrics in Grafana dashboard
5. 📊 Set up alerts in AlertManager (optional)
6. 📈 Create custom dashboards (optional)

## Support

- **Dashboard Guide**: See `GRAFANA_DASHBOARD_GUIDE.md`
- **Monitoring Details**: See `MONITORING_IMPLEMENTATION.md`
- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/

---

**Quick Tip**: Keep the dashboard open in a browser tab and watch metrics in real-time as you send queries! 🎯
