# Production container developer documentation

## Architecture

The production image has two build stages. The package lives under src/docker-container/ so it remains isolated from the existing development container definitions. The Node stage installs the locked frontend dependencies and runs npm run build. The Python runtime stage contains the backend, runtime dependencies, Nginx, compiled frontend, and startup assets. Node and the Vite development server are not present in the runtime image.

## Process model

entrypoint.sh is PID 1 and owns the lifecycle.

Startup sequence:
1. Create /run/unnamed-tracking status files.
2. Start Nginx with the startup configuration.
3. Validate required configuration.
4. Wait for PostgreSQL with pg_isready.
5. Run alembic upgrade heads with retries.
6. Start Uvicorn on 127.0.0.1:8000.
7. Poll /health.
8. Validate ready.conf.
9. Replace the active nginx.conf with ready.conf.
10. Reload Nginx using the active configuration.
11. Verify that / serves the production frontend.
12. Keep PID 1 alive and detect an unexpected backend exit.

The startup page is available while every later step is running.

## Status contract

/_startup/status.json contains phase, overall, database, migrations, backend, frontend, and message fields.

/_startup/details.txt contains human-readable migration/startup details. /_startup/backend.log contains captured backend output.

These are file-backed rather than application-backed. This is intentional: the status path must remain usable when FastAPI cannot start.

## Nginx

The startup configuration serves the startup UI and status files. ready.conf adds the API reverse proxy and production frontend with SPA fallback.

The current hand-off copies ready.conf over the active nginx.conf and then performs a normal nginx -s reload. The process is therefore not restarted during the hand-off.

## Startup UI

The current branch contains both startup/index.html and startup/startup.html; the startup configuration serves the startup page through the Nginx startup routes.

It has an animated loading indicator, lifecycle phase, per-component state, expandable details, and responsive styling. Dark mode is the default presentation. A light presentation follows prefers-color-scheme: light.

The JavaScript polls quickly while startup is active and backs off substantially once the status becomes READY. Keep this polling asynchronous and lightweight.

Do not move the startup UI into the main Vue bundle. Its independence is a functional requirement.

## Performance

The startup page must remain a static Nginx response. It must not introduce Node startup, frontend compilation, database access, or FastAPI dependency into the first response. Keep the status document small and keep polling asynchronous.

The intended startup-page overhead is below 100 ms; the application startup itself is not artificially bounded by that number.

## CI

The dedicated production-container workflow currently builds and publishes the image but does not exercise the full runtime smoke-test sequence. Do not document the workflow as proving database, migration, backend, frontend, or startup-failure behaviour until those tests are present again.

## TLS

TLS is intentionally absent from this implementation. Future certificate handling should be implemented at the Nginx layer rather than adding certificate generation to entrypoint.sh.
