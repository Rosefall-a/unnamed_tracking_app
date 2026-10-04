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
