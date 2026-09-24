# Architecture

## Repository layout

The application is split into:

- `src/backend` — FastAPI/Python application, SQLAlchemy models, Alembic migrations and provider integrations.
- `src/frontend` — Vue 3/Vite web client.
- `src/docker-container` — assembled production image with Nginx and the compiled frontend.
- `docs` — operator/developer documentation.
- `devdocs` — implementation-oriented production-container notes.
- `Notes` — historical/design/build notes.
- `.github/workflows` — CI for backend, frontend, Docker and formatting.

## Development architecture

The development frontend is a Vite dev server on port 80 inside its container. It proxies `/api` to `http://backend:8000`.

The backend runs FastAPI/Uvicorn on port 8000.

PostgreSQL is the persistent database.

The browser normally sees the frontend origin and therefore does not need a direct backend hostname.

## Production architecture

The production image combines:

- Python backend
- compiled Vue frontend
- Nginx
- PostgreSQL client utilities
- BlueMap Java runtime/CLI

Nginx is the public process. FastAPI listens on `127.0.0.1:8000`.

The production startup UI is intentionally independent of Vue and FastAPI so it can still display diagnostics when the backend cannot start.

## Configuration layers

There are currently several configuration layers:

1. Environment variables loaded by Pydantic Settings.
2. Compose interpolation variables.
3. Deployment-wide settings stored in PostgreSQL.
4. Per-user credentials stored with user data.
5. Frontend Vite build/dev environment variables.
6. Playnite extension settings stored by Playnite.

This is the main reason a future unified .env/config handler needs careful boundaries: not every setting belongs in the environment, and some secrets intentionally belong in the database.

## Database

SQLAlchemy uses asynchronous PostgreSQL connections through `DATABASE_URL`.

Alembic migrations are part of application startup. The repository's migration documentation describes automatic adoption/upgrade behaviour for older schemas; the production entrypoint currently invokes `alembic upgrade heads`.

## API

FastAPI exposes:

- OpenAPI at `/api/openapi.json`
- Swagger UI at `/api/docs`
- ReDoc at `/api/redoc`
- health at `/health`

Routes cover games, media, authentication, setup, settings, integrations, library sync, archives, notifications, calendar, cards, sets, statistics and import/export.

## Data and secret handling

Recoverable secrets such as provider credentials and OIDC client secrets can be encrypted with Fernet using `SECRET_KEY`. The deployment settings API deliberately returns configuration status rather than secret values.

OIDC client secrets remain backend-side. The browser receives the application's normal HTTP-only session cookie, not an OIDC access token.
