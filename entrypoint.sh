#!/bin/sh
set -e

MAX_RETRIES=30
RETRY_DELAY=2

echo "Applying database migrations..."

attempt=1
until alembic -c app/alembic.ini upgrade head; do
  if [ "$attempt" -ge "$MAX_RETRIES" ]; then
    echo "Migrations failed after $MAX_RETRIES attempts. Exiting."
    exit 1
  fi
  echo "Migration attempt $attempt failed (DB may not be ready yet), retrying in ${RETRY_DELAY}s..."
  attempt=$((attempt + 1))
  sleep "$RETRY_DELAY"
done

echo "Migrations applied. Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000