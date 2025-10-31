# Redis Caching Implementation Guide

## Overview

The Disney Customer Feedback API uses Redis for intelligent query caching based on semantic similarity. This reduces costs by avoiding redundant LLM API calls and improves response time for similar questions.

## How It Works

### Semantic Similarity Matching

Instead of exact string matching, the cache uses **cosine similarity** on question embeddings:

1. **Cache Check**: When a question arrives, generate its embedding
2. **Similarity Search**: Compare with all cached question embeddings
3. **Threshold Check**: If similarity ≥ 0.95, return cached answer
4. **Cache Miss**: If similarity < 0.95, proceed with full search and LLM generation
5. **Cache Store**: After generating new answer, store it with the question embedding

### Example

```
User 1: "What do people say about the rides?"
→ Cache MISS → Generate answer → Store in cache

User 2: "What are visitor opinions on the attractions?"
→ Similarity = 0.96 → Cache HIT → Return instant response
```

Even though the questions use different words, they're semantically similar enough to match!

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Redis connection (optional, defaults shown)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Cache Parameters

Configured in `main.py`:

```python
cache_service = QueryCacheService(
    embedding_service=embedding_service,
    redis_host=os.getenv("REDIS_HOST", "localhost"),
    redis_port=int(os.getenv("REDIS_PORT", "6379")),
    redis_db=0,
    similarity_threshold=0.95,  # 95% similarity required for cache hit
    ttl_hours=24                # Cache entries expire after 24 hours
)
```

### Redis Docker Configuration

In `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  container_name: disney_redis
  ports:
    - "6379:6379"
  volumes:
    - redis-data:/data
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
  restart: unless-stopped
  networks:
    - disney-network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
```

**Key Settings:**
- `appendonly yes`: Persistence enabled (survives container restarts)
- `maxmemory 256mb`: Memory limit
- `maxmemory-policy allkeys-lru`: Evict least recently used keys when full

## API Endpoints

### Get Cache Statistics

```bash
GET /cache/stats
```

**Response:**
```json
{
  "total_entries": 42,
  "similarity_threshold": 0.95,
  "ttl_hours": 24.0,
  "oldest_entry": "2024-01-15T10:30:00",
  "newest_entry": "2024-01-15T14:45:00",
  "redis_memory_used": "1.14M",
  "redis_host": "localhost",
  "redis_port": 6379
}
```

### Clear Cache

```bash
POST /cache/clear
```

**Response:**
```json
{
  "status": "success",
  "message": "Cache cleared"
}
```

## Data Structure

### Redis Keys

The cache uses three types of keys:

1. **Cache Entries**: `disney_cache:{hash}` - Stores question, answer, num_reviews_used, timestamp
2. **Embeddings**: `disney_embedding:{hash}` - Stores question embedding vector
3. **Key Set**: `disney_cache_keys` - Set of all cache entry identifiers

### Storage Format

```
disney_cache:a1b2c3d4e5f6g7h8
→ {"question": "...", "answer": "...", "num_reviews_used": 7, "timestamp": "2024-01-15T10:30:00"}

disney_embedding:a1b2c3d4e5f6g7h8
→ [0.123, -0.456, 0.789, ...]  # 384-dimensional embedding

disney_cache_keys
→ {a1b2c3d4e5f6g7h8, b2c3d4e5f6g7h8i9, ...}
```

## Metrics

The cache service exposes metrics for monitoring:

### Custom Metrics

```
# Cache hits (with similarity score)
disney_feedback_disney_api_cache_hit_count_total

# Cache misses
disney_feedback_disney_api_cache_miss_count_total

# Current cache size
disney_feedback_disney_api_cache_size

# Similarity scores for cache hits (histogram)
disney_feedback_disney_api_cache_similarity_score
```

### Example Queries

**Cache Hit Rate:**
```promql
rate(disney_feedback_disney_api_cache_hit_count_total[5m]) / 
(rate(disney_feedback_disney_api_cache_hit_count_total[5m]) + 
 rate(disney_feedback_disney_api_cache_miss_count_total[5m]))
```

**Average Similarity Score:**
```promql
histogram_quantile(0.5, 
  rate(disney_feedback_disney_api_cache_similarity_score_bucket[5m]))
```

## Testing

### Test Redis Connection

```bash
python test_redis_cache.py
```

### Test Cache Functionality

```bash
# Send first query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do people say about the rides?"}'
# Response: {"cached": false, ...}

# Send similar query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are visitor opinions on attractions?"}'
# Response: {"cached": true, ...}

# Check cache stats
curl http://localhost:8000/cache/stats
```

## Performance Impact

### Benefits

1. **Cost Savings**: Avoid OpenAI API calls for similar questions (~$0.002 per query saved)
2. **Response Time**: Instant responses for cache hits (< 50ms vs 1-3 seconds for LLM)
3. **Reduced Load**: Less load on ChromaDB and embedding service
4. **Better UX**: Faster responses improve user experience

### Overhead

- **Cache Check**: ~10-20ms to compute similarity with all cached entries
- **Storage**: ~2KB per cached entry (embedding + metadata)
- **Memory**: 256MB Redis instance can hold ~100K cached queries

### Expected Cache Hit Rate

Based on typical usage patterns:

- **Single user session**: 30-40% (users often rephrase questions)
- **Multiple users**: 20-30% (common questions overlap)
- **FAQ-style queries**: 50-60% (same questions repeated)

## Troubleshooting

### Cache Not Working

1. **Check Redis Connection**
   ```bash
   docker-compose ps redis
   docker-compose logs redis
   ```

2. **Test Redis Connectivity**
   ```bash
   python test_redis_cache.py
   ```

3. **Check Cache Stats**
   ```bash
   curl http://localhost:8000/cache/stats
   ```

### Low Cache Hit Rate

1. **Lower Similarity Threshold** (in `main.py`):
   ```python
   similarity_threshold=0.90  # Instead of 0.95
   ```

2. **Check Similarity Scores**:
   - Look at `cache_similarity_score` metric in Grafana
   - If most scores are 0.85-0.94, threshold is too high

### Redis Memory Full

1. **Check Memory Usage**
   ```bash
   docker exec disney_redis redis-cli INFO memory
   ```

2. **Increase Memory Limit** (in `docker-compose.yml`):
   ```yaml
   command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
   ```

3. **Clear Old Entries**
   ```bash
   curl -X POST http://localhost:8000/cache/clear
   ```

### Cache Persistence Issues

If cache is lost after container restart:

1. **Check Volume**
   ```bash
   docker volume ls | grep redis
   ```

2. **Verify AOF**
   ```bash
   docker exec disney_redis redis-cli CONFIG GET appendonly
   # Should return: appendonly yes
   ```

## Advanced Configuration

### Tuning Similarity Threshold

The `similarity_threshold` parameter controls how similar questions must be:

- **0.99**: Very strict - only near-identical questions match
- **0.95**: Recommended - semantically similar questions match
- **0.90**: Relaxed - broader matching, higher hit rate
- **0.85**: Very relaxed - may match unrelated questions

### Custom TTL

Adjust `ttl_hours` based on your needs:

```python
ttl_hours=24   # Default: 24 hours
ttl_hours=72   # 3 days for longer-lived cache
ttl_hours=1    # 1 hour for frequently changing data
```

### Redis Configuration

For production, consider:

```yaml
command: >
  redis-server
  --appendonly yes
  --maxmemory 1gb
  --maxmemory-policy allkeys-lru
  --save 900 1
  --save 300 10
  --save 60 10000
```

## Best Practices

1. **Monitor Cache Hit Rate**: Track in Grafana to ensure cache is effective
2. **Adjust Threshold**: Fine-tune based on your question patterns
3. **Set Appropriate TTL**: Balance freshness vs cache hit rate
4. **Regular Cleanup**: Clear cache when data changes significantly
5. **Memory Monitoring**: Watch Redis memory usage and adjust limits

## Security Considerations

1. **Network Isolation**: Redis runs in Docker network, not exposed publicly
2. **No Authentication**: For local development only
3. **Production**: Add Redis password and TLS for production deployments

```yaml
# Production example
environment:
  - REDIS_PASSWORD=your_secure_password
command: redis-server --requirepass ${REDIS_PASSWORD} --tls-cert-file /certs/cert.pem
```

## Migration from File-based Cache

The old file-based cache has been completely replaced with Redis. No migration is needed - the system will start with an empty cache and populate it as queries are made.

Old cache files (if any) can be safely deleted:
```bash
rm -rf cache/query_cache.json
```
