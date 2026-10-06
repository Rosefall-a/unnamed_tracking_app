# Startup and Troubleshooting

The production container keeps startup diagnostics available without turning the startup page into a raw log viewer. The page is intentionally concise: it reports lifecycle state and a short failure explanation, while detailed logs remain operator-facing diagnostics.

## Startup sequence

1. Initialise status and diagnostic files.
2. Start Nginx with the startup configuration.
3. Validate database configuration.
4. Wait for PostgreSQL.
5. Run Alembic migrations.
6. Start Uvicorn on `127.0.0.1:8000`.
7. Wait for `/health`.
8. Select the HTTP, HTTPS, or HTTPS-redirect production Nginx configuration and render TLS certificate paths when required.
9. Validate the selected configuration, copy it to `nginx.conf`, and reload Nginx.
10. Verify the compiled frontend.
11. Monitor the backend process.

## Health semantics

The Docker healthcheck reads the file-backed startup status rather than treating the diagnostic Nginx page as readiness.

`overall=starting` means the container is alive but the application is not ready. `overall=failed` means the operator should inspect the diagnostics. Only `overall=ready` is healthy.

A backend crash after readiness changes the status to `BACKEND_CRASHED` and makes the healthcheck fail while keeping diagnostics available.

## Failure states

## Startup page

The static startup page reports application starting, database state, migration state, backend state, frontend state, application ready, and application failed. Normal startup does not render backend, migration, Nginx, or Docker log output. On failure the spinner is replaced by a failure indicator and a concise diagnostic message.

Raw logs are intentionally not rendered by default: they are useful for operators but noisy for normal startup. The startup page does not add a reload button or other log-management controls.

## Detailed diagnostics

Use the container logging facilities first:

```text
docker logs <container>
docker logs -f <container>
```

Docker exposes container stdout/stderr through docker logs. The production entrypoint writes lifecycle messages there and Nginx errors are directed to stderr. Detailed backend output is retained at /run/unnamed-tracking/backend.log; migration output is retained at /run/unnamed-tracking/migration.log.

If detailed file contents are needed, use the retained files inside the running container:

```text
docker exec <container> cat /run/unnamed-tracking/backend.log
docker exec <container> cat /run/unnamed-tracking/migration.log
```

They can also be copied out:

```text
docker cp <container>:/run/unnamed-tracking/backend.log ./backend.log
docker cp <container>:/run/unnamed-tracking/migration.log ./migration.log
```

Do not inspect Docker's internal logging-driver files directly.

## Diagnostic endpoints

- `CONFIGURATION_FAILED`
- `DATABASE_FAILED`
- `MIGRATION_FAILED`
- `BACKEND_FAILED`
- `BACKEND_TIMEOUT`
- `FRONTEND_FAILED`
- `BACKEND_CRASHED`

Inspect:

```text
/_startup/status.json
/_startup/details.txt
/_startup/backend.log
```

These are operational diagnostics, not durable log storage.

## TLS failures

TLS is disabled by default and is enabled only when `NGINX_TLS_ENABLED=true`. When enabled, the container uses `readytls.conf` unless `NGINX_TLS_REDIRECT_HTTP=true`, in which case it uses `readytlsredirect.conf`. With both certificate variables empty, an existing `/etc/nginx/tls/tls.crt` + `/etc/nginx/tls/tls.key` pair is used when present; otherwise a self-signed localhost certificate/key pair is generated automatically under `/run/unnamed-tracking/tls`.

Check that:

1. the certificate and private key are mounted at the configured paths;
2. both files are readable by the Nginx master;
3. the certificate chain is in the expected PEM order;
4. the certificate and key match;
5. port 443 is published by the deployment;
6. `AUTH_COOKIE_SECURE=true` is set for an HTTPS public URL.

The renderer reports missing/unreadable files without printing private-key contents. Nginx validation catches malformed or mismatched certificate/key material.

If TLS configuration fails during startup, the diagnostic HTTP listener remains available because the HTTPS configuration is activated only during the ready handoff.

## OIDC and proxy URLs

Nginx forwards `X-Forwarded-Proto` and Uvicorn trusts that header only from the local Nginx hop. This allows request-derived OIDC callback URLs to use `https` when clients connect through embedded TLS.

If another reverse proxy is placed in front of the container, ensure it preserves the external HTTPS scheme and that the deployment’s proxy trust boundary remains limited to the expected internal hop.

## Shutdown

Docker stop sends SIGTERM to PID 1. PID 1 forwards shutdown to FastAPI, waits for it, and then asks Nginx to quit. If shutdown behavior is incorrect in a deployment, inspect the container logs for the entrypoint’s shutdown messages.


## Secrets

The production entrypoint does not print passwords, tokens, API keys, SMTP credentials, private keys, webhook secrets, or session secrets. Detailed logs remain operator-only diagnostics because application components may produce their own log output.
