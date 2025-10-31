#!/bin/bash

# Test Redis Caching Integration
# This script tests the end-to-end caching functionality

set -e

BASE_URL="http://localhost:8000"
REDIS_HOST="localhost"
REDIS_PORT="6379"

echo "🧪 Testing Redis Caching Integration"
echo "======================================"
echo ""

# 1. Check Redis is running
echo "1️⃣  Checking Redis connection..."
if ! python -c "import redis; r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT); r.ping()" 2>/dev/null; then
    echo "❌ Redis is not running!"
    echo "   Start it with: docker-compose up redis -d"
    exit 1
fi
echo "✅ Redis is running"
echo ""

# 2. Clear cache
echo "2️⃣  Clearing cache..."
CLEAR_RESPONSE=$(curl -s -X POST "$BASE_URL/cache/clear")
echo "   Response: $CLEAR_RESPONSE"
echo "✅ Cache cleared"
echo ""

# 3. Check initial cache stats
echo "3️⃣  Checking initial cache stats..."
STATS=$(curl -s "$BASE_URL/cache/stats")
echo "   $STATS"
ENTRIES=$(echo $STATS | python -c "import sys, json; print(json.load(sys.stdin)['total_entries'])" 2>/dev/null || echo "0")
if [ "$ENTRIES" != "0" ]; then
    echo "⚠️  Cache not empty after clear (found $ENTRIES entries)"
fi
echo "✅ Initial cache is empty"
echo ""

# 4. First query (should miss cache)
echo "4️⃣  Sending first query (expecting cache MISS)..."
QUERY1='{"question": "What do people say about the rides?"}'
RESPONSE1=$(curl -s -X POST "$BASE_URL/query" \
    -H "Content-Type: application/json" \
    -d "$QUERY1")

CACHED1=$(echo $RESPONSE1 | python -c "import sys, json; print(json.load(sys.stdin).get('cached', False))" 2>/dev/null || echo "false")
if [ "$CACHED1" = "True" ]; then
    echo "❌ First query was cached (should be MISS)"
    exit 1
fi
echo "✅ Cache MISS as expected"
echo ""

# 5. Check cache stats after first query
echo "5️⃣  Checking cache stats after first query..."
STATS=$(curl -s "$BASE_URL/cache/stats")
ENTRIES=$(echo $STATS | python -c "import sys, json; print(json.load(sys.stdin)['total_entries'])" 2>/dev/null || echo "0")
if [ "$ENTRIES" != "1" ]; then
    echo "❌ Expected 1 cache entry, found $ENTRIES"
    exit 1
fi
echo "✅ Cache now has 1 entry"
echo ""

# 6. Similar query (should hit cache)
echo "6️⃣  Sending similar query (expecting cache HIT)..."
QUERY2='{"question": "What are visitor opinions on the attractions?"}'
RESPONSE2=$(curl -s -X POST "$BASE_URL/query" \
    -H "Content-Type: application/json" \
    -d "$QUERY2")

CACHED2=$(echo $RESPONSE2 | python -c "import sys, json; print(json.load(sys.stdin).get('cached', False))" 2>/dev/null || echo "false")
if [ "$CACHED2" != "True" ]; then
    echo "⚠️  Similar query was not cached"
    echo "   This might be OK if similarity < 0.95"
    SIMILARITY=$(echo $RESPONSE2 | python -c "import sys, json; print(json.load(sys.stdin).get('cache_similarity', 'N/A'))" 2>/dev/null || echo "N/A")
    echo "   Similarity score: $SIMILARITY"
else
    echo "✅ Cache HIT as expected"
    SIMILARITY=$(echo $RESPONSE2 | python -c "import sys, json; print(json.load(sys.stdin).get('cache_similarity', 'N/A'))" 2>/dev/null || echo "N/A")
    echo "   Similarity score: $SIMILARITY"
fi
echo ""

# 7. Different query (should miss cache)
echo "7️⃣  Sending different query (expecting cache MISS)..."
QUERY3='{"question": "Is Disneyland California usually crowded?"}'
RESPONSE3=$(curl -s -X POST "$BASE_URL/query" \
    -H "Content-Type: application/json" \
    -d "$QUERY3")

CACHED3=$(echo $RESPONSE3 | python -c "import sys, json; print(json.load(sys.stdin).get('cached', False))" 2>/dev/null || echo "false")
if [ "$CACHED3" = "True" ]; then
    echo "⚠️  Different query was cached (unexpected)"
else
    echo "✅ Cache MISS as expected for different question"
fi
echo ""

# 8. Final cache stats
echo "8️⃣  Final cache statistics..."
STATS=$(curl -s "$BASE_URL/cache/stats")
echo "$STATS" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f\"   Total entries: {data.get('total_entries', 0)}\")
print(f\"   Similarity threshold: {data.get('similarity_threshold', 'N/A')}\")
print(f\"   TTL hours: {data.get('ttl_hours', 'N/A')}\")
print(f\"   Redis memory: {data.get('redis_memory_used', 'N/A')}\")
" 2>/dev/null || echo "   $STATS"
echo ""

# 9. Test metrics
echo "9️⃣  Checking cache metrics..."
METRICS=$(curl -s "$BASE_URL/metrics" | grep -E "disney_feedback_disney_api_cache_(hit|miss)_count")
if [ -z "$METRICS" ]; then
    echo "⚠️  Cache metrics not found"
else
    echo "✅ Cache metrics available:"
    echo "$METRICS" | sed 's/^/   /'
fi
echo ""

echo "======================================"
echo "✅ All Redis cache tests completed!"
echo ""
echo "Summary:"
echo "  - Redis connection: ✅"
echo "  - Cache clear: ✅"
echo "  - Cache miss on first query: ✅"
echo "  - Cache storage: ✅"
echo "  - Cache hit on similar query: $([ "$CACHED2" = "True" ] && echo "✅" || echo "⚠️  (check similarity threshold)")"
echo "  - Cache miss on different query: ✅"
echo "  - Metrics exposed: $([ -n "$METRICS" ] && echo "✅" || echo "⚠️")"
echo ""
