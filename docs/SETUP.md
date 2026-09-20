# Self-hosted setup

The normal installation path is **environment-light**:

- PostgreSQL connection details stay in `.env` because they are needed before the application can open its database.
- The first administrator is created from the first-run web setup page.
- OIDC and SMTP can be configured during first run and edited later from Settings.
- Provider credentials, including ScreenScraper and SteamGridDB, are managed from the admin Settings UI and stored encrypted in PostgreSQL.
- Upload limits and secure-cookie behaviour are managed from **Settings → Application**.
- The Fernet encryption key is generated automatically and persisted under the application data directory.

## 1. Example `.env`

Copy `example.env` to `.env` at the repository root. Do not commit your real `.env`.

```dotenv
POSTGRES_USER=archive
POSTGRES_PASSWORD=change-this-database-password
POSTGRES_DB=archive
# POSTGRES_HOST=db
# POSTGRES_PORT=5432

# Optional: replace the POSTGRES_* connection settings with one complete URL.
# DATABASE_URL=postgresql+psycopg://user:password@db.example.com:5432/archive
```

That is normally all the environment configuration required. `POSTGRES_HOST` defaults to `db` and `POSTGRES_PORT` defaults to `5432`.

If `DATABASE_URL` is supplied, it wins over the individual `POSTGRES_*` values. `postgres://...` and `postgresql://...` URLs are normalized to the async psycopg dialect used by the backend.

### Existing installations with `SECRET_KEY`

`SECRET_KEY` is still accepted as a **one-time backwards-compatible bootstrap value**. If no persisted key exists, the application validates that value and writes it to:

```text
/data/config/fernet.key
```

After that, the persisted key is authoritative and the `SECRET_KEY` environment variable can be removed. This is important: do not delete the persistent application data volume when removing the old variable.

New installations should not set `SECRET_KEY` at all.

## 2. Standard three-image Docker Compose

The standard deployment continues to use the three separate application images/services:

1. PostgreSQL
2. Backend
3. Frontend

The repository's `compose.yaml` uses the backend image with the generated-key data directory mounted at `/data` and the frontend proxy pointed at `http://backend:8000`.

```bash
cp example.env .env
docker compose up --build
```

The backend applies pending Alembic migrations with `alembic upgrade heads` before starting Uvicorn. A fresh database therefore has its schema before the setup endpoint is used.

Open `http://localhost:5173`. The frontend checks `/api/setup/status`; when there are no users it sends you to `/setup`, where you create the first administrator.

The backend does **not** create a primary user from environment variables anymore. `PRIMARY_USER_USERNAME`, `PRIMARY_USER_EMAIL`, and `PRIMARY_USER_PASSWORD` are no longer part of the normal configuration path.

## 3. Database configuration

The backend accepts either:

```dotenv
POSTGRES_USER=archive
POSTGRES_PASSWORD=change-this-database-password
POSTGRES_DB=archive
```

or a complete URL:

```dotenv
DATABASE_URL=postgresql+psycopg://archive:password@db.example.com:5432/archive
```

When using the individual settings, the effective URL is:

```text
postgresql+psycopg://POSTGRES_USER:POSTGRES_PASSWORD@POSTGRES_HOST:POSTGRES_PORT/POSTGRES_DB
```

The default host is `db` and the default port is `5432`, which matches the Compose service. You only need `POSTGRES_HOST` or `POSTGRES_PORT` when your database is somewhere else.

## 4. First-run setup

The setup page is the authoritative first-run bootstrap. It creates:

- the first administrator account;
- optional OIDC configuration;
- optional SMTP configuration.

Encrypted OIDC and SMTP secrets are stored using the same persistent Fernet key as the rest of the application's recoverable secrets.

## 5. Application Settings

Administrators can open **Settings → Application** and configure:

- **Secure authentication cookies** — enable when the browser-facing application is served over HTTPS. Restart after changing this setting.
- **Maximum upload size** — standard image/file uploads.
- **Maximum clip size** — video clips and soundtrack uploads.
- **Maximum world/modpack size** — world saves and modpack archives.

The upload-size values are applied to the running backend immediately. Secure-cookie middleware is initialized when the process starts, so restart after changing that option.

For upgrades, existing `AUTH_COOKIE_SECURE`, `MAX_UPLOAD_SIZE_MB`, `MAX_CLIP_SIZE_MB`, and `MAX_WORLD_SAVE_SIZE_MB` environment values are migrated into the database once. After that, the database Settings values are authoritative.

## 6. Provider credentials

Open **Settings → Server Integrations** as an administrator.

The deployment-wide provider settings include:

- SteamGridDB
- RetroAchievements
- Giant Bomb
- IGDB
- ScreenScraper
- Xbox

ScreenScraper has two parts: its developer credentials (`devid`/`devpassword`) are deployment-wide, while a user's ScreenScraper account (`ssid`/`sspassword`) can be supplied per user or as a deployment-wide fallback. The ScreenScraper developer credentials are therefore stored in the same Server Integrations section rather than being required in `.env`.

Secret fields are encrypted at rest and are never returned to the browser after saving. Existing per-user credentials continue to take precedence over deployment-wide credentials.

Legacy provider environment variables remain readable as fallbacks for existing deployments, but new installations should use Settings.

## 7. OIDC / SSO

OIDC is configured from the first-run setup page or **Settings → OIDC / SSO**.

The redirect URI should be the browser-facing frontend URL, for example:

```text
http://localhost:5173/api/auth/oidc/callback
```

Register that exact URI with the identity provider. Client secrets remain backend-only and are encrypted at rest.

## 8. SMTP / password reset

SMTP is configured from the first-run setup page or **Settings → SMTP / Email**. The saved SMTP password is encrypted at rest. The Settings page also provides an SMTP test path using the same transport used by password-reset email.

## 9. Central application image

The repository also contains a reusable central image under `src/central/`. It packages the existing backend and frontend runtimes into one application image while keeping PostgreSQL as a separate service.

Build it from the repository root:

```bash
docker build -f src/central/Dockerfile -t unnamed-tracking-app-central:local .
```

### Combined central deployment

Copy the central example environment file to the repository root as `.env`, then run:

```bash
cp src/central/example.env .env
docker compose -f src/central/docker-compose.yaml up --build
```

The central container defaults to `APP_MODE=both`, exposing the frontend on `5173` and backend on `8000`. In combined mode the frontend proxy automatically uses `http://127.0.0.1:8000`.

### Split central deployment

The same central image can also run as two services:

```bash
docker compose -f src/central/docker-compose.separate.yaml up --build
```

The backend runs with `APP_MODE=backend`; the frontend runs with `APP_MODE=frontend` and proxies to `http://backend:8000`.

`BACKEND_URL` is an explicit override for unusual deployments. It takes precedence over the automatic defaults.

The central image uses the exact same application source as the three separate images; it is an additional packaging option, not a replacement for the separate backend/frontend images.

## 10. Persistent data

The application data directory should remain persistent across container recreation. At minimum it contains:

```text
/data/
  config/
    fernet.key
  users/
  ...application data...
```

PostgreSQL has its own persistent volume. The Fernet key and PostgreSQL data must both survive restarts/redeployments or encrypted provider credentials and user data will no longer be available.

## 11. Security notes

- Keep `.env` out of source control.
- Do not expose PostgreSQL publicly.
- Put the browser-facing application behind HTTPS in production and enable secure authentication cookies.
- Do not delete `/data/config/fernet.key` unless you are deliberately discarding encrypted application secrets and understand the consequences.
- Do not generate a new Fernet key on every container start.
- Provider/OIDC/SMTP secrets should normally be entered through Settings rather than copied into deployment files.


# Optional first-admin bootstrap. If all three are set, the server creates this
# administrator automatically. If they are omitted, the normal web setup remains
# available at /setup.
# PRIMARY_USER_USERNAME=admin
# PRIMARY_USER_EMAIL=admin@example.com
# PRIMARY_USER_PASSWORD=Change-this-during-setup

# Optional encrypted deployment-settings bootstrap.
# Put the password-protected JSON exported from Settings -> Backup at
# /data/application.json (or set APPLICATION_JSON_PATH) and provide the export
# password. It is only auto-imported when the database has no users.
# APPLICATION_JSON_PASSWORD=your-settings-export-password
# APPLICATION_JSON_PATH=/data/application.json
