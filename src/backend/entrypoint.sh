#!/bin/sh
set -e

# Brings the database up to date (waits for it, adopts databases from an
# older migration history, then runs every newer migration). See
# src/database/migrate.py. A real failure stops the container with a clear
# message instead of retrying the same error.
echo "Preparing database..."
python -m src.database.migrate

echo "Starting application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
