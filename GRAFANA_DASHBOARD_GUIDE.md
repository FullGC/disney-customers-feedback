# 📊 Grafana Dashboard Guide

## Dashboard Overview

The **Disney Customer Feedback API - Performance Dashboard** provides comprehensive monitoring and visualization of your FastAPI application's performance, search behavior, and system health.

## 🚀 Quick Start

### 1. Import the Dashboard

**Option A: Auto-provisioning (Recommended)**
The dashboard should auto-load when you restart Grafana:
```bash
docker-compose restart grafana
```

**Option B: Manual Import**
1. Open Grafana: http://localhost:3000
2. Login: `admin` / `admin`
3. Click **+** → **Import**
4. Click **Upload JSON file**
5. Select `grafana/dashboards/disney-feedback-dashboard.json`
6. Select **Prometheus** as the datasource
7. Click **Import**

### 2. Verify Data Flow

Run the end-to-end test:
```bash
./test_e2e_monitoring.sh
```

This will:
- ✅ Check all services are running
- ✅ Send test queries to generate metrics
- ✅ Verify metrics appear in Prometheus
- ✅ Verify traces appear in Jaeger
- ✅ Verify Grafana datasources are configured

## 📈 Dashboard Panels

### Row 1: Key Performance Indicators (KPIs)

#### 1. Total Requests (1h)
- **Metric**: `disney_feedback_requests_total`
- **Description**: Total number of API requests in the last hour
- **Good Value**: Depends on traffic, but should be > 0 if app is active
- **Action Items**: 
  - If 0: Check if FastAPI app is running and receiving requests
  - Spike: Investigate traffic source

#### 2. Errors (1h)
- **Metric**: `disney_feedback_requests_total{status=~"5.."}`
- **Description**: Total 5xx errors in the last hour
- **Good Value**: 0 (green)
- **Threshold**: 
  - Green: 0 errors
  - Red: ≥ 1 error
- **Action Items**: 
  - Check application logs
  - Review Jaeger traces for failed requests
  - Investigate error patterns

#### 3. P95 Latency
- **Metric**: `disney_feedback_request_duration_seconds_bucket`
- **Description**: 95th percentile response time
- **Good Value**: < 1s (green)
- **Thresholds**:
  - Green: < 1s
  - Yellow: 1-3s
  - Red: > 3s
- **Action Items**:
  - Check Component Performance Breakdown
  - Identify slow components (LLM, ChromaDB, embeddings)

#### 4. P99 Latency
- **Metric**: `disney_feedback_request_duration_seconds_bucket`
- **Description**: 99th percentile response time (worst-case performance)
- **Good Value**: < 2s (green)
- **Thresholds**:
  - Green: < 2s
  - Yellow: 2-5s
  - Red: > 5s
- **Action Items**: Similar to P95, focus on tail latency optimization

### Row 2: Traffic and Latency Analysis

#### 5. Request Rate by Endpoint
- **Metric**: `rate(disney_feedback_requests_total[1m])`
- **Description**: Requests per second for each endpoint
- **Chart Type**: Time series
- **Use Cases**:
  - Identify traffic patterns
  - Spot unusual spikes or drops
  - Capacity planning

#### 6. Request Latency Percentiles
- **Metrics**: P50, P95, P99 latency by endpoint
- **Description**: Multi-percentile latency view
- **Chart Type**: Time series with table legend
- **Use Cases**:
  - Compare latency across endpoints
  - Identify degradation over time
  - SLA monitoring

### Row 3: Search Behavior Analytics

#### 7. Search Type Distribution
- **Metric**: `disney_feedback_search_type_total`
- **Description**: Pie chart showing hybrid vs keyword search usage
- **Chart Type**: Pie chart
- **Use Cases**:
  - Understand search method adoption
  - Validate vector search availability
  - Track feature usage

#### 8. Hybrid Search Strategy Distribution
- **Metric**: `disney_feedback_hybrid_search_strategy_total`
- **Description**: ID-filtered vs full search strategy usage
- **Chart Type**: Pie chart
- **Use Cases**:
  - Understand how often filters reduce the search space
  - Optimize hybrid search thresholds
  - Performance tuning

#### 9. Average Reviews Returned
- **Metric**: `disney_feedback_reviews_returned`
- **Description**: Average number of reviews returned per query
- **Chart Type**: Time series
- **Use Cases**:
  - Quality of search results
  - Validate max_results parameter
  - LLM context size monitoring

### Row 4: Component Performance

#### 10. Component Performance Breakdown
- **Metrics**: 
  - `disney_feedback_chromadb_search_duration_seconds`
  - `disney_feedback_embedding_duration_seconds`
  - `disney_feedback_llm_duration_seconds`
  - `disney_feedback_keyword_search_duration_seconds`
- **Description**: Stacked area chart showing time spent in each component
- **Chart Type**: Stacked time series
- **Use Cases**:
  - Identify bottlenecks
  - Optimization prioritization
  - Performance regression detection
- **Typical Breakdown**:
  - LLM: 60-80% (OpenAI API call)
  - ChromaDB: 10-20% (vector search)
  - Embedding: 5-10% (local computation)
  - Keyword: 1-5% (pandas operations)

### Row 5: Advanced Metrics

#### 11. ChromaDB Search P95 Latency by Strategy
- **Metric**: `disney_feedback_chromadb_search_duration_seconds_bucket`
- **Description**: Compare vector search performance between strategies
- **Chart Type**: Time series
- **Use Cases**:
  - Validate ID-filtered search optimization
  - Tune hybrid search threshold (5x max_results)
  - Performance comparison

#### 12. Average Candidate Count (Hybrid Search)
- **Metric**: `disney_feedback_hybrid_candidates_count`
- **Description**: Number of candidates after pandas filtering
- **Chart Type**: Time series grouped by has_filters
- **Use Cases**:
  - Understand filter effectiveness
  - Optimize filtering logic
  - Predict strategy selection

### Row 6: Filter Usage

#### 13. Filter Usage (Branch/Location)
- **Metric**: `disney_feedback_filter_usage_total`
- **Description**: Track which filters are being used
- **Chart Type**: Bar chart
- **Use Cases**:
  - Feature usage analytics
  - Query pattern analysis
  - Business insights

## 🎯 How to Use the Dashboard

### Monitor Real-Time Performance

1. **Set refresh interval**: Top-right corner → 5s (default)
2. **Adjust time range**: Top-right corner → Last 1h (default)
3. **Watch for anomalies**: Look for spikes in errors or latency

### Investigate Performance Issues

1. **Check P95/P99 latency panels** → Identify if there's a problem
2. **Review Component Performance Breakdown** → Find the bottleneck
3. **Check Search Strategy Distribution** → See if strategy selection is optimal
4. **Click on Jaeger datasource** → View detailed traces for slow requests

### Analyze Search Behavior

1. **Search Type Distribution** → Understand hybrid vs keyword usage
2. **Hybrid Strategy Distribution** → See how often ID filtering is used
3. **Average Reviews Returned** → Validate search quality
4. **Filter Usage** → Understand query patterns

### Capacity Planning

1. **Request Rate by Endpoint** → Identify peak traffic times
2. **Component Performance Breakdown** → Plan resource allocation
3. **Average Candidate Count** → Estimate database load

## 📊 Example Queries in Prometheus

You can create custom panels using these PromQL queries:

### Request Metrics
```promql
# Total requests per minute
sum(rate(disney_feedback_requests_total[1m]))

# Success rate
sum(rate(disney_feedback_requests_total{status!~"5.."}[5m])) 
/ 
sum(rate(disney_feedback_requests_total[5m]))

# Error rate
sum(rate(disney_feedback_requests_total{status=~"5.."}[5m]))
```

### Latency Metrics
```promql
# Average request latency
rate(disney_feedback_request_duration_seconds_sum[5m]) 
/ 
rate(disney_feedback_request_duration_seconds_count[5m])

# P50 latency
histogram_quantile(0.50, 
  rate(disney_feedback_request_duration_seconds_bucket[5m])
)

# P95 latency
histogram_quantile(0.95, 
  rate(disney_feedback_request_duration_seconds_bucket[5m])
)

# P99 latency
histogram_quantile(0.99, 
  rate(disney_feedback_request_duration_seconds_bucket[5m])
)
```

### Component Performance
```promql
# ChromaDB average latency
rate(disney_feedback_chromadb_search_duration_seconds_sum[5m]) 
/ 
rate(disney_feedback_chromadb_search_duration_seconds_count[5m])

# LLM average latency
rate(disney_feedback_llm_duration_seconds_sum[5m]) 
/ 
rate(disney_feedback_llm_duration_seconds_count[5m])

# Embedding generation average latency
rate(disney_feedback_embedding_duration_seconds_sum[5m]) 
/ 
rate(disney_feedback_embedding_duration_seconds_count[5m])
```

### Business Metrics
```promql
# Search type breakdown (last hour)
sum by (search_type) (
  increase(disney_feedback_search_type_total[1h])
)

# Hybrid search strategy usage
sum by (strategy) (
  increase(disney_feedback_hybrid_search_strategy_total[1h])
)

# Filter usage statistics
sum by (filter_type) (
  increase(disney_feedback_filter_usage_total[1h])
)

# Average reviews per query
avg(disney_feedback_reviews_returned)
```

## 🚨 Alerts Configuration

### Recommended Alerts

Create these alerts in Prometheus AlertManager:

```yaml
groups:
  - name: disney_feedback_api
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(disney_feedback_requests_total{status=~"5.."}[5m])) 
          / 
          sum(rate(disney_feedback_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High P95 latency
      - alert: HighLatencyP95
        expr: |
          histogram_quantile(0.95, 
            rate(disney_feedback_request_duration_seconds_bucket[5m])
          ) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency is high"
          description: "P95 latency is {{ $value }}s"

      # Service down
      - alert: ServiceDown
        expr: up{job="fastapi-app"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "FastAPI service is down"
          description: "The FastAPI application is not responding"
```

## 🔍 Troubleshooting

### Dashboard Shows "No Data"

1. **Check Prometheus datasource**:
   - Configuration → Data Sources → Prometheus
   - Click "Save & Test"
   - Should see "Data source is working"

2. **Verify metrics are being scraped**:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```
   - Look for `fastapi-app` job
   - Check `health` status is "up"

3. **Send test queries**:
   ```bash
   ./test_e2e_monitoring.sh
   ```

### Metrics Not Updating

1. **Check FastAPI app is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check metrics endpoint**:
   ```bash
   curl http://localhost:8000/metrics | grep disney_feedback
   ```

3. **Verify Prometheus scraping**:
   - Open Prometheus: http://localhost:9090
   - Go to Status → Targets
   - Check `fastapi-app` last scrape time

### Dashboard Shows Old Data

1. **Check refresh interval**: Top-right corner, should be 5s
2. **Check time range**: Top-right corner, try "Last 5 minutes"
3. **Force refresh**: Click refresh button in top-right corner

## 📚 Additional Resources

- **Prometheus Querying**: https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Grafana Dashboards**: https://grafana.com/docs/grafana/latest/dashboards/
- **OpenTelemetry**: https://opentelemetry.io/docs/
- **Jaeger Tracing**: https://www.jaegertracing.io/docs/

## 🎓 Best Practices

1. **Set up alerts**: Don't rely on manual dashboard monitoring
2. **Use annotations**: Mark deployments, incidents in Grafana
3. **Create team dashboards**: Customize for different audiences (ops, dev, business)
4. **Regular reviews**: Weekly performance review using historical data
5. **SLO tracking**: Define and track Service Level Objectives
6. **Continuous optimization**: Use metrics to drive performance improvements

## 📈 Next Steps

1. **Create custom panels**: Add business-specific metrics
2. **Set up AlertManager**: Configure notifications (Slack, email, PagerDuty)
3. **Add more dashboards**: Separate dashboards for different concerns
4. **Implement SLOs**: Define and track service level objectives
5. **Cost monitoring**: Track OpenAI API costs and ChromaDB resource usage
6. **User segmentation**: Add labels for different user types or regions

---

**Dashboard UID**: `disney-feedback-api`  
**Last Updated**: November 1, 2025  
**Auto-refresh**: 5 seconds  
**Default Time Range**: Last 1 hour
