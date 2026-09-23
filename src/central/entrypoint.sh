#!/bin/sh
set -eu

APP_MODE="${APP_MODE:-both}"

start_backend() {
    echo "Starting backend..."
    echo "Applying database migrations..."
    alembic upgrade heads
    echo "Starting API server..."
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
}

start_frontend() {
    echo "Starting frontend..."
    cd /app/frontend
    exec npm run dev -- --host 0.0.0.0
}

cleanup() {
    status=$?
    trap - EXIT INT TERM
    if [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    exit "$status"
}

case "$APP_MODE" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    both)
        echo "Starting backend and frontend..."
        start_backend &
        BACKEND_PID=$!
        start_frontend &
        FRONTEND_PID=$!
        trap cleanup EXIT INT TERM

        while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
            sleep 1
        done

        if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo "Backend process exited; stopping frontend."
        else
            echo "Frontend process exited; stopping backend."
        fi
        exit 1
        ;;
    *)
        echo "Invalid APP_MODE: $APP_MODE" >&2
        echo "Expected one of: frontend, backend, both" >&2
        exit 2
        ;;
esac
