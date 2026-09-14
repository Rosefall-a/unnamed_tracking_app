# Unnamed Tracking App

## Quick start

The recommended self-hosted deployment uses PostgreSQL plus the separate backend and frontend images/services.

```bash
cp example.env .env
docker compose up --build
```

Then open `http://localhost:5173`. On a new database the first-run setup page creates the administrator and can configure OIDC and SMTP.

### Environment configuration

Normal `.env` configuration is intentionally small:

```dotenv
POSTGRES_USER=archive
POSTGRES_PASSWORD=change-this-database-password
POSTGRES_DB=archive
# POSTGRES_HOST=db
# POSTGRES_PORT=5432
```

You can instead provide a complete `DATABASE_URL`; it takes precedence over the `POSTGRES_*` values. The default PostgreSQL host is `db` and the default port is `5432`.
  
The application generates its Fernet encryption key automatically and persists it under `/data/config/fernet.key`. Existing deployments may temporarily provide `SECRET_KEY` as a migration/bootstrap value; new deployments do not need to generate one manually.

Normal application settings are managed from the web UI:

- **Settings → Application** — upload limits and secure authentication cookies.
- **Settings → Server Integrations** — provider credentials, including ScreenScraper and SteamGridDB.
- **Settings → OIDC / SSO** — OIDC configuration.
- **Settings → SMTP / Email** — SMTP and password-reset configuration.

`PRIMARY_USER_*` environment variables are no longer used for normal first-run setup.

## Docker image layouts

All three application images remain supported independently:

- `src/backend/dockerfile` — backend image.
- `src/frontend/Dockerfile` — frontend image.
- `src/central/Dockerfile` — optional combined application image containing both runtimes.

The central image does **not** embed PostgreSQL. PostgreSQL remains a separate persistent service, while `APP_MODE=both` runs the frontend and backend together. The same image can also run as `APP_MODE=backend` or `APP_MODE=frontend`.

See [`docs/SETUP.md`](docs/SETUP.md) for the complete deployment guide, database configuration, generated Fernet key behaviour, Settings configuration, and central-image Compose examples.

## Development checks

### Backend

```bash
cd src/backend
mypy --config-file pyproject.toml src
pylint --rcfile=pyproject.toml src
```

### Frontend

```bash
cd src/frontend
npm run lint
npm run format
npm run typecheck
```

## Database migrations

Generate a migration from the backend environment with:

```bash
docker compose exec backend alembic -c alembic.ini revision --autogenerate -m "describe the schema change"
```

Application startup applies all migration heads with `alembic upgrade heads`.

## Security

This project is not currently hardened for direct public-internet exposure. Keep the API behind an appropriate network boundary and do not expose it directly to the public internet. Keep PostgreSQL private, persist `/data`, and never delete the persisted Fernet key from an installation that contains encrypted secrets.

## Recommended VS Code extensions

- Ruff by charliermarsh
