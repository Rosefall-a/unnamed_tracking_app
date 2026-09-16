# Unnamed Tracking App

## Installable clients

The same self-hosted server can be used from several maintained clients:

- **Tracking Web APK** renders the hosted Vue application and therefore follows normal frontend UI updates automatically.
- **Tracking Native APK** is a Kotlin/Jetpack Compose client with native Android navigation and secure system-browser OIDC.
- **Progressive Web App** can be installed directly from a supported browser on desktop or mobile.
- **Tracking Windows Web** packages the hosted Vue application with Microsoft WebView2 as a portable ZIP and signed MSIX.

Tagged builds are published on the [latest GitHub Release](https://github.com/Rosefall-a/unnamed_tracking_app/releases/latest). Stable asset names are `tracking-web.apk`, `tracking-native.apk`, `tracking-windows-web.zip`, and `tracking-windows-web.msix`. Development builds remain available from the named artifacts on the Android and Windows Actions workflows.

See [`docs/CLIENTS.md`](docs/CLIENTS.md) for choosing, installing, releasing, and maintaining each client.

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

### Android

The two co-installable Android 10+ clients live in [`src/androidapp`](src/androidapp): a Vue/WebView edition and a native Compose edition. Both support explicit HTTP/HTTPS server configuration. See the [Android user and developer guide](src/androidapp/README.md).

### Windows

The Windows 10+ WebView2 client lives in [`src/windowsapp`](src/windowsapp). See its [build, packaging, and installation guide](src/windowsapp/README.md).

## Database migrations

Generate a migration from the backend environment with:

```bash
docker compose exec backend alembic -c alembic.ini revision --autogenerate -m "describe the schema change"
```

Application startup applies all migration heads with `alembic upgrade heads`.

## Security

This project is not currently hardened for direct public-internet exposure. Keep the API behind an appropriate network boundary and do not expose it directly to the public internet. Keep PostgreSQL private, persist `/data`, and never delete the persisted Fernet key from an installation that contains encrypted secrets.

Browser sessions use opaque random credentials; only SHA-256 token hashes are
stored in PostgreSQL. Logout is idempotent and revokes the matching database
session before clearing the browser cookie, so that cookie cannot be reused.

## Recommended VS Code extensions

- Ruff by charliermarsh
