#!/bin/bash
# Run tests inside Docker container

echo "========================================"
echo "GeoRoute Tactical Planning - Test Suite"
echo "========================================"

# Build backend image
echo "Building backend Docker image..."
docker compose build georoute-backend

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker build complete"
echo ""

# Run model tests
echo "Running tactical models tests..."
docker compose run --rm georoute-backend python -m georoute.tests.test_tactical_models

if [ $? -ne 0 ]; then
    echo "❌ Model tests failed"
    exit 1
fi

echo ""
echo "Running backlog storage tests..."
docker compose run --rm georoute-backend python -m georoute.tests.test_backlog_storage

if [ $? -ne 0 ]; then
    echo "❌ Storage tests failed"
    exit 1
fi

echo ""
echo "Running integration tests..."
docker compose run --rm georoute-backend python -m georoute.tests.test_integration

if [ $? -ne 0 ]; then
    echo "❌ Integration tests failed"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ ALL TESTS PASSED!"
echo "========================================"
