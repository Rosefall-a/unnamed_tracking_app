# Operations

## Migrations

The backend applies migrations during startup.

The current production entrypoint uses:

```bash
alembic upgrade heads
```

The repository documentation says migration history should remain a single line and migrations should be safe to run repeatedly.

Do not edit a migration that has already shipped; create a new migration.

## Backups

The application contains deployment backup/restore functionality in the backend and Settings UI.

Deployment backups are separate from ordinary per-user data export. Operators should treat deployment backups as privileged application state and protect them accordingly.

Filesystem application data is mounted at `/data` in the supplied Compose deployments.

## Startup diagnostics

The production image writes runtime status under:

- `/run/unnamed-tracking/status.json`
- `/run/unnamed-tracking/details.txt`
- `/run/unnamed-tracking/backend.log`

The independent startup page can display status even when FastAPI has failed.

A backend crash after the application becomes ready changes the status to a failed state while keeping Nginx available.

## Logs

Development backend output is attached to the container. The production entrypoint captures Uvicorn output into its runtime status directory.

The repository currently has an open issue for broader production observability/hardening (#205).

## HTTPS

The current production image is HTTP-only. TLS is deliberately left to a follow-up issue (#204).

When HTTPS is added at the edge, `AUTH_COOKIE_SECURE=true` should be used.

## CI

The repository has separate backend, frontend, development Docker and production-container workflows.

Production image CI currently builds and publishes the assembled image, but the full PostgreSQL/runtime smoke test is not currently performed as a blocking build test. Issue #206 tracks a more robust optional runtime validation layer.

## Security boundary

The README explicitly warns that the project is not currently hardened for direct public-internet exposure. Operators should use a suitable network boundary/reverse proxy and protect PostgreSQL.
