# Architecture

Unnamed Tracking App is split into a Python/FastAPI backend and a Vue/Vite frontend, with PostgreSQL providing persistent application data.

## Plugin platform

The plugin platform adds a separate execution boundary. The frontend calls FastAPI /api/plugins; the backend authenticates the user and communicates with plugin-runtime over an authenticated internal transport; plugin-runtime performs package discovery, integrity validation and isolated process execution.

The backend owns the application-facing API, authentication, compatibility and permission policy. The runtime owns plugin process execution and private plugin storage. Plugin packages do not run inside the backend and do not receive the core environment, database connection, Docker socket or unrestricted network.

Compose connects the backend and runtime through an internal-only network. PostgreSQL and the frontend remain on the normal application network; the runtime is not attached to it and is not published to the host.

The frontend plugin manager calls /api/plugins for lifecycle state and /api/plugins/{id}/ui, /settings and /actions for the declarative plugin host. There is no browser-to-runtime connection.

## Repository structure

- src/backend/src/api/ — FastAPI routes and API schemas.
- src/backend/src/plugin_api/ — plugin contracts, lifecycle, gateway and runtime transport.
- src/frontend/src/components/ — reusable Vue components.
- src/frontend/src/views/ — application pages/views.
- src/frontend/src/services/ — frontend API/service clients.
- src/plugin-runtime/ — isolated runtime service and sandbox supervisor.

Plugin management routes are composed in `api/routes/plugins.py`; their implementations live in `api/routes/plugin_manager/`. Acquisition, catalogue access, lifecycle, updates, contributions and backend dispatch each have their own module. The shared runtime module owns the authenticated client and gateway helpers. Keep patches and dependency overrides at the module that owns the implementation.

`plugin_api/contracts.py` remains the public import surface. It composes the core manifest models in `base_contracts.py` and the declarative UI models in `frontend_contracts.py`. Splitting these modules does not change the v1.0 API: the manifest schema, UI schema and all 43 HTTP paths were compared with the original implementation, and the backend suite passed 855 tests with two existing skips.

Large frontend pages keep their state in composables and their styles in `styles/pages/`. Game detail panels share `gameDetailContext.ts`; their stylesheet selectors stay under `.game-detail-page` so panel extraction does not restyle other pages. The extraction passed the existing 106 frontend tests, type checks and production build.

## Configuration architecture

Deployment configuration is defined by the backend configuration registry. Environment values have higher precedence than persisted settings and environment-owned fields remain deployment-owned.

## Database

PostgreSQL is the normal production database. Schema changes are managed with Alembic migrations and must extend the single current head. The reconciliation revision `b8c7d6e5f403` joins the independently published main and plugin-manager histories without changing their revision IDs or dropping schema objects.

## API

The backend exposes the application's REST API under /api; interactive documentation is available at /api/docs.

## Authentication

Normal application authentication uses server-side sessions and host/port-scoped authentication cookies. Plugin management and plugin backend routes use the same request-scoped authentication boundary. Revoked sessions are rejected, and session metadata remains available for the session manager.

OIDC/SSO is integrated into the same application authentication flow. OIDC provider credentials are kept server-side; client secrets are not exposed to the frontend.

See [OIDC / SSO](../user-guide/oidc.md) for provider configuration.

## Production container

The production deployment is packaged separately under `src/docker-container/`.

```text
compiled Vue -> Nginx -> FastAPI -> PostgreSQL
                    |
                    +-> independent startup diagnostics
```

Nginx starts before FastAPI so the deployment always has a lightweight diagnostic path. PID 1 owns the lifecycle and switches Nginx from `startup.conf` to one of three complete production configurations only after the backend is healthy: `ready.conf` (HTTP), `readytls.conf` (HTTPS), or `readytlsredirect.conf` (HTTPS plus HTTP redirect). The selected TLS configuration is rendered with the certificate paths before being copied to `/etc/nginx/nginx.conf` and validated.

The readiness source of truth is the file-backed status JSON. The Docker healthcheck requires `overall=ready`; merely serving the startup page is not sufficient.

The production Nginx configuration may optionally add an HTTPS listener. TLS configuration is generated from deployment environment variables and externally mounted certificate/key files, not from the application configuration UI. FastAPI receives the forwarded protocol from the local Nginx hop so request-derived URLs can preserve HTTPS.

Nginx workers run as `www-data`. The master retains the privileges required for port binding and lifecycle control. Runtime status and diagnostics are ephemeral under `/run/unnamed-tracking`; persistent application state is mounted separately under `/data`.

For runtime integration behavior, including PostgreSQL, migrations, frontend/API handoff, and shutdown, see production issue #206.
