# Production container developer documentation

## Architecture

The production image has two build stages. The package lives under `src/docker-container/` so it remains isolated from the existing development container definitions. The Node stage installs the locked frontend dependencies and runs npm run build. The Python runtime stage contains the backend, runtime dependencies, Nginx, compiled frontend, and startup assets. Node and the Vite development server are not present in the runtime image.

## Process model

entrypoint.sh is PID 1 and owns the lifecycle.

Startup sequence:
1. Create /run/unnamed-tracking status files.
2. Start Nginx with startup.conf.
3. Validate required configuration.
4. Wait for PostgreSQL with pg_isready.
5. Run alembic upgrade heads with retries.
6. Start Uvicorn on 127.0.0.1:8000.
7. Poll /health.
8. Switch Nginx to ready.conf and reload it.
9. Verify that / serves the production frontend.
10. Keep PID 1 alive and detect an unexpected backend exit.

The startup page is available while every later step is running.

## Status contract

/_startup/status.json contains phase, overall, database, migrations, backend, frontend, and message fields.

/_startup/details.txt contains human-readable migration/startup details. /_startup/backend.log contains captured backend output.

These are file-backed rather than application-backed. This is intentional: the status path must remain usable when FastAPI cannot start.

## Nginx

startup.conf serves only the startup UI and status files. ready.conf adds the API reverse proxy and production frontend with SPA fallback. Nginx is reloaded rather than restarted after readiness.

## Startup UI

The startup UI is plain HTML/CSS/JavaScript. It has an animated loading indicator, lifecycle phase, per-component state, expandable details, and responsive styling. Dark mode is the default presentation. A light presentation follows prefers-color-scheme: light.

Do not move the startup UI into the main Vue bundle. Its independence is a functional requirement.

## Performance

The startup page must remain a static Nginx response. It must not introduce Node startup, frontend compilation, database access, or FastAPI dependency into the first response. Keep the status document small and keep polling asynchronous.

The intended startup-page overhead is below 100 ms; the application startup itself is not artificially bounded by that number.

## TLS

TLS is intentionally absent from this implementation. Future certificate handling should be implemented at the Nginx layer rather than adding certificate generation to entrypoint.sh.
