#!/bin/sh
set -e

echo "Starting application..."

echo "Applying database migrations..."
alembic upgrade heads

echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
