# Metric Names Reference

## Corrected Metric Names for Grafana Dashboard

All metrics in the dashboard have been updated to match the actual metric names from OpenTelemetry.

### Metric Name Mapping

| Dashboard Display | Actual Prometheus Metric Name |
|------------------|------------------------------|
| Request Count | `disney_feedback_disney_api_request_count_total` |
| Request Duration | `disney_feedback_disney_api_request_duration_seconds_*` |
| Search Type | `disney_feedback_disney_api_search_type_count_total` |
| Hybrid Strategy | `disney_feedback_disney_api_hybrid_strategy_count_total` |
| Reviews Returned | `disney_feedback_disney_api_reviews_returned_*` |
| ChromaDB Search Duration | `disney_feedback_disney_api_chromadb_search_duration_seconds_*` |
| Embedding Duration | `disney_feedback_disney_api_embedding_generation_duration_seconds_*` |
| LLM Duration | `disney_feedback_disney_api_llm_inference_duration_seconds_*` |
| Keyword Search Duration | `disney_feedback_disney_api_keyword_search_duration_seconds_*` (if implemented) |
| Filter Usage | `disney_feedback_disney_api_filter_usage_count_total` |
| Candidate Count | `disney_feedback_disney_api_candidate_count_*` |

### Available Metrics

#### Request Metrics
- `disney_feedback_disney_api_request_count_total` - Counter for total requests
  - Labels: `endpoint`, `method`, `status_code`
- `disney_feedback_disney_api_request_duration_seconds_bucket` - Histogram buckets
- `disney_feedback_disney_api_request_duration_seconds_count` - Histogram count
- `disney_feedback_disney_api_request_duration_seconds_sum` - Histogram sum

#### Search Metrics
- `disney_feedback_disney_api_search_type_count_total` - Counter for search types
  - Labels: `search_type` (hybrid/keyword)
- `disney_feedback_disney_api_hybrid_strategy_count_total` - Counter for strategy
  - Labels: `strategy` (id_filtered/full_search)

#### Performance Metrics
- `disney_feedback_disney_api_chromadb_search_duration_seconds_*` - ChromaDB latency
  - Labels: `strategy`
- `disney_feedback_disney_api_embedding_generation_duration_seconds_*` - Embedding latency
  - Labels: `operation`
- `disney_feedback_disney_api_llm_inference_duration_seconds_*` - LLM latency
  - Labels: `model`

#### Business Metrics
- `disney_feedback_disney_api_reviews_returned_*` - Reviews per query
  - Labels: `search_type`
- `disney_feedback_disney_api_filter_usage_count_total` - Filter usage
  - Labels: `filter_type` (branch/location/both)
- `disney_feedback_disney_api_candidate_count_*` - Candidate counts
  - Labels: `strategy`

### Note on Histogram Metrics

Histogram metrics have three variants:
- `*_bucket{le="..."}` - Cumulative counts for each bucket
- `*_count` - Total number of observations
- `*_sum` - Sum of all observed values

To calculate percentiles (P50, P95, P99), use `histogram_quantile()`:
```promql
histogram_quantile(0.95, 
  rate(disney_feedback_disney_api_request_duration_seconds_bucket[5m])
)
```

To calculate average:
```promql
rate(disney_feedback_disney_api_request_duration_seconds_sum[5m]) 
/ 
rate(disney_feedback_disney_api_request_duration_seconds_count[5m])
```

### Additional OpenTelemetry Metrics

The following metrics are also available from the OpenTelemetry instrumentation:

- `disney_feedback_http_client_duration_milliseconds_*` - HTTP client latency
- `disney_feedback_otelcol_*` - OpenTelemetry Collector internal metrics
- `disney_feedback_up` - Scrape health status (1 = up, 0 = down)
- `disney_feedback_scrape_duration_seconds` - Time to scrape metrics

---

**Last Updated**: November 1, 2025  
**Dashboard File**: `grafana/provisioning/dashboards/disney-feedback-dashboard.json`
