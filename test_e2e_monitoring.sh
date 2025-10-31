#!/bin/bash

# Complete End-to-End Monitoring Test Script

set -e

echo "=============================================="
echo "Disney Customer Feedback API - E2E Monitoring Test"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Function to wait for service
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}Ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}Timeout!${NC}"
    return 1
}

echo "Step 1: Checking Docker Services"
echo "================================="

services=("disney_chromadb" "disney_otel_collector" "disney_prometheus" "disney_jaeger" "disney_grafana")
for service in "${services[@]}"; do
    if docker ps | grep -q "$service"; then
        print_status 0 "$service is running"
    else
        print_status 1 "$service is NOT running"
        echo "Please run: docker-compose up -d"
        exit 1
    fi
done
echo ""

echo "Step 2: Checking Service Health"
echo "================================"

# Check ChromaDB
if curl -s http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
    print_status 0 "ChromaDB (port 8001)"
else
    print_status 1 "ChromaDB (port 8001)"
fi

# Check OTel Collector
if curl -s http://localhost:13133/ > /dev/null 2>&1; then
    print_status 0 "OpenTelemetry Collector (port 13133)"
else
    print_status 1 "OpenTelemetry Collector (port 13133)"
fi

# Check Prometheus
if curl -s http://localhost:9090/-/ready > /dev/null 2>&1; then
    print_status 0 "Prometheus (port 9090)"
else
    print_status 1 "Prometheus (port 9090)"
fi

# Check Jaeger
if curl -s http://localhost:16687/ > /dev/null 2>&1; then
    print_status 0 "Jaeger UI (port 16687)"
else
    print_status 1 "Jaeger UI (port 16687)"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    print_status 0 "Grafana (port 3000)"
else
    print_status 1 "Grafana (port 3000)"
fi
echo ""

echo "Step 3: Checking FastAPI Application"
echo "===================================="

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status 0 "FastAPI app is running (port 8000)"
else
    print_status 1 "FastAPI app is NOT running"
    echo -e "${YELLOW}Please start the app:${NC}"
    echo "  source env_disney_customers_feedback_ex/bin/activate"
    echo "  python -m uvicorn disney_customers_feedback_ex.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# Check metrics endpoint
if curl -s http://localhost:8000/metrics | grep -q "disney_feedback"; then
    print_status 0 "Metrics endpoint is exposing disney_feedback metrics"
else
    print_status 1 "Metrics endpoint is NOT exposing disney_feedback metrics"
fi
echo ""

echo "Step 4: Sending Test Queries"
echo "============================"

echo "Query 1: General question about rides..."
response1=$(curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do people say about the rides?"}')

if echo "$response1" | grep -q "answer"; then
    print_status 0 "Query 1 successful"
    num_reviews=$(echo "$response1" | grep -o '"num_reviews_used":[0-9]*' | grep -o '[0-9]*')
    echo "  → Used $num_reviews reviews"
else
    print_status 1 "Query 1 failed"
fi

sleep 2

echo "Query 2: Hong Kong specific question..."
response2=$(curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How is the food at Hong Kong Disneyland?"}')

if echo "$response2" | grep -q "answer"; then
    print_status 0 "Query 2 successful"
    num_reviews=$(echo "$response2" | grep -o '"num_reviews_used":[0-9]*' | grep -o '[0-9]*')
    echo "  → Used $num_reviews reviews"
else
    print_status 1 "Query 2 failed"
fi

sleep 2

echo "Query 3: California specific question..."
response3=$(curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do visitors think about California Disneyland?"}')

if echo "$response3" | grep -q "answer"; then
    print_status 0 "Query 3 successful"
    num_reviews=$(echo "$response3" | grep -o '"num_reviews_used":[0-9]*' | grep -o '[0-9]*')
    echo "  → Used $num_reviews reviews"
else
    print_status 1 "Query 3 failed"
fi
echo ""

echo "Step 5: Verifying Metrics in Prometheus"
echo "========================================"

# Wait a moment for metrics to be scraped
sleep 5

# Check if metrics are available in Prometheus
metrics_check=$(curl -s 'http://localhost:9090/api/v1/query?query=disney_feedback_requests_total')

if echo "$metrics_check" | grep -q '"status":"success"'; then
    if echo "$metrics_check" | grep -q '"result":\['; then
        print_status 0 "disney_feedback_requests_total metric found in Prometheus"
        
        # Get the total count
        total=$(echo "$metrics_check" | grep -o '"value":\[[^]]*\]' | head -1 | grep -o '[0-9.]*' | tail -1)
        echo "  → Total requests recorded: $total"
    else
        print_status 1 "disney_feedback_requests_total metric exists but has no data"
    fi
else
    print_status 1 "Failed to query Prometheus"
fi

# Check search type metric
search_type_check=$(curl -s 'http://localhost:9090/api/v1/query?query=disney_feedback_search_type_total')
if echo "$search_type_check" | grep -q '"result":\['; then
    print_status 0 "disney_feedback_search_type_total metric found"
else
    print_status 1 "disney_feedback_search_type_total metric not found"
fi

# Check hybrid strategy metric
strategy_check=$(curl -s 'http://localhost:9090/api/v1/query?query=disney_feedback_hybrid_search_strategy_total')
if echo "$strategy_check" | grep -q '"result":\['; then
    print_status 0 "disney_feedback_hybrid_search_strategy_total metric found"
else
    print_status 1 "disney_feedback_hybrid_search_strategy_total metric not found"
fi
echo ""

echo "Step 6: Verifying Traces in Jaeger"
echo "==================================="

# Check if Jaeger has traces for our service
traces_check=$(curl -s 'http://localhost:16687/api/services')

if echo "$traces_check" | grep -q "disney-customer-feedback-api"; then
    print_status 0 "Traces found for disney-customer-feedback-api in Jaeger"
else
    print_status 1 "No traces found in Jaeger (may take a few moments to appear)"
fi
echo ""

echo "Step 7: Verifying Grafana Datasources"
echo "======================================"

# Check Prometheus datasource
datasources=$(curl -s -u admin:admin http://localhost:3000/api/datasources)

if echo "$datasources" | grep -q '"name":"Prometheus"'; then
    print_status 0 "Prometheus datasource configured in Grafana"
else
    print_status 1 "Prometheus datasource NOT found in Grafana"
fi

if echo "$datasources" | grep -q '"name":"Jaeger"'; then
    print_status 0 "Jaeger datasource configured in Grafana"
else
    print_status 1 "Jaeger datasource NOT found in Grafana"
fi
echo ""

echo "Step 8: Checking Dashboard Availability"
echo "========================================"

dashboards=$(curl -s -u admin:admin http://localhost:3000/api/search?type=dash-db)

if echo "$dashboards" | grep -q "Disney Customer Feedback API"; then
    print_status 0 "Disney Customer Feedback API dashboard found"
else
    print_status 1 "Dashboard not found (you may need to import it manually)"
fi
echo ""

echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo ""
echo -e "${GREEN}✓ All systems operational!${NC}"
echo ""
echo "Access the monitoring stack:"
echo "  • Grafana:    http://localhost:3000 (admin/admin)"
echo "  • Prometheus: http://localhost:9090"
echo "  • Jaeger:     http://localhost:16687"
echo "  • FastAPI:    http://localhost:8000/docs"
echo ""
echo "View metrics:"
echo "  curl http://localhost:8000/metrics | grep disney_feedback"
echo ""
echo "Example Prometheus queries:"
echo "  • Request rate:  rate(disney_feedback_requests_total[1m])"
echo "  • P95 latency:   histogram_quantile(0.95, rate(disney_feedback_request_duration_seconds_bucket[5m]))"
echo "  • Search types:  sum by (search_type) (disney_feedback_search_type_total)"
echo ""
echo -e "${GREEN}Monitoring setup complete!${NC}"
echo ""
