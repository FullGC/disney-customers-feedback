#!/bin/bash

# Test script for monitoring setup

echo "=== Disney Customer Feedback API - Monitoring Test ==="
echo ""

# Test 1: Health endpoint
echo "1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
echo ""
echo ""

# Test 2: Metrics endpoint
echo "2. Testing metrics endpoint..."
curl -s http://localhost:8000/metrics | head -20
echo "..."
echo ""

# Test 3: Send test queries
echo "3. Sending test queries..."
echo ""

echo "Query 1: General feedback question"
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do people say about the rides?"}' | jq . 2>/dev/null || \
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do people say about the rides?"}'
echo ""
echo ""

echo "Query 2: Branch-specific question (Hong Kong)"
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How is the food at Hong Kong Disneyland?"}' | jq . 2>/dev/null || \
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How is the food at Hong Kong Disneyland?"}'
echo ""
echo ""

# Test 4: Check Prometheus
echo "4. Checking Prometheus metrics..."
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, state: .health}' 2>/dev/null || \
echo "Prometheus not available or jq not installed"
echo ""

# Test 5: Check OpenTelemetry Collector
echo "5. Checking OpenTelemetry Collector health..."
curl -s http://localhost:13133/ 2>/dev/null || echo "OTel Collector health endpoint not responding"
echo ""

echo "=== Monitoring Test Complete ==="
echo ""
echo "You can now view:"
echo "- Grafana dashboards: http://localhost:3000 (admin/admin)"
echo "- Jaeger traces: http://localhost:16687"
echo "- Prometheus: http://localhost:9090"
echo ""
