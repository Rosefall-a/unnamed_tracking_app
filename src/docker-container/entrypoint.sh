#!/bin/sh
set -eu

STATUS_DIR="/run/unnamed-tracking"
STATUS_FILE="$STATUS_DIR/status.json"
DETAILS_FILE="$STATUS_DIR/details.txt"
BACKEND_LOG="$STATUS_DIR/backend.log"
NGINX_PID="/run/nginx.pid"

mkdir -p "$STATUS_DIR"
: > "$DETAILS_FILE"
: > "$BACKEND_LOG"

write_status() {
  phase="$1"; overall="$2"; database="$3"; migrations="$4"; backend="$5"; frontend="$6"; message="$7"
  cat > "$STATUS_FILE" <<EOF
{"phase":"$phase","overall":"$overall","database":"$database","migrations":"$migrations","backend":"$backend","frontend":"$frontend","message":"$message"}
EOF
}

fail_startup() {
  phase="$1"; message="$2"
  printf '%s\n' "$message" > "$DETAILS_FILE"
  write_status "$phase" "failed" "unknown" "unknown" "failed" "waiting" "$message"
  # Keep Nginx alive so the diagnostic page remains available after failure.
  while :; do sleep 3600; done
}

cleanup() {
  set +e
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then kill "$BACKEND_PID" 2>/dev/null; fi
  if [ -f "$NGINX_PID" ]; then nginx -s quit 2>/dev/null; fi
}
trap cleanup INT TERM EXIT

write_status "INITIALIZING" "starting" "waiting" "waiting" "waiting" "ready" "Starting production services."
nginx -c /etc/nginx/startup.conf

if [ -z "${SECRET_KEY:-}" ]; then fail_startup "CONFIGURATION_FAILED" "SECRET_KEY is required."; fi
if [ -z "${DATABASE_URL:-}" ]; then fail_startup "CONFIGURATION_FAILED" "DATABASE_URL is required."; fi

write_status "WAITING_FOR_DATABASE" "starting" "starting" "waiting" "waiting" "ready" "Waiting for PostgreSQL."
DB_HEALTH_URL="$(printf "%s" "$DATABASE_URL" | sed "s#^postgresql+psycopg://#postgresql://#")"
attempt=1
while ! pg_isready -d "$DB_HEALTH_URL" >/dev/null 2>&1; do
  if [ "$attempt" -ge 60 ]; then fail_startup "DATABASE_FAILED" "PostgreSQL did not become ready within 120 seconds."; fi
  attempt=$((attempt + 1)); sleep 2
done

write_status "DATABASE_READY" "starting" "ready" "waiting" "waiting" "ready" "PostgreSQL is ready."
write_status "MIGRATING_DATABASE" "starting" "ready" "starting" "waiting" "ready" "Applying database migrations."

attempt=1
until alembic upgrade heads >>"$DETAILS_FILE" 2>&1; do
  if [ "$attempt" -ge 30 ]; then fail_startup "MIGRATION_FAILED" "Database migrations failed after 30 attempts."; fi
  attempt=$((attempt + 1)); sleep 2
done

write_status "DATABASE_READY" "starting" "ready" "ready" "waiting" "ready" "Database migrations completed."
write_status "STARTING_BACKEND" "starting" "ready" "ready" "starting" "ready" "Starting FastAPI."

uvicorn src.main:app --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1 &
BACKEND_PID="$!"

attempt=1
while ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    cat "$BACKEND_LOG" >> "$DETAILS_FILE" 2>/dev/null || true
    fail_startup "BACKEND_FAILED" "The backend process exited during startup."
  fi
  if [ "$attempt" -ge 60 ]; then
    cat "$BACKEND_LOG" >> "$DETAILS_FILE" 2>/dev/null || true
    fail_startup "BACKEND_TIMEOUT" "The backend did not become healthy within 120 seconds."
  fi
  attempt=$((attempt + 1)); sleep 2
done

write_status "STARTING_FRONTEND" "starting" "ready" "ready" "ready" "starting" "Activating the production frontend."
nginx -t -c /etc/nginx/ready.conf
cp /etc/nginx/ready.conf /etc/nginx/nginx.conf
nginx -s reload

attempt=1
while ! curl -fsS http://127.0.0.1/ >/dev/null 2>&1; do
  if [ "$attempt" -ge 15 ]; then fail_startup "FRONTEND_FAILED" "Nginx could not serve the production frontend."; fi
  attempt=$((attempt + 1)); sleep 1
done

write_status "READY" "ready" "ready" "ready" "ready" "ready" "Unnamed Tracking is ready."
printf '%s\n' "Production application is ready." > "$DETAILS_FILE"

while :; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    cat "$BACKEND_LOG" > "$DETAILS_FILE" 2>/dev/null || true
    write_status "BACKEND_CRASHED" "failed" "ready" "ready" "failed" "ready" "The backend stopped unexpectedly."
    while :; do sleep 3600; done
  fi
  sleep 2
done
