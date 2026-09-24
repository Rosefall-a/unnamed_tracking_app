# Environment Variables

This page records environment variables found in the current repository and explains what they actually do. There are three different sources to keep separate:

1. **Backend application settings** — loaded by Pydantic Settings in `src/backend/src/core/config.py`.
2. **Compose variables** — used to construct container/database configuration.
3. **Frontend variables** — Vite variables available at build/dev time.

## Backend application settings

| Variable | Default / required | Actual purpose |
|---|---|---|
| `DATABASE_URL` | **Required** | PostgreSQL connection string used by SQLAlchemy/Alembic. |
| `SECRET_KEY` | **Required** | Fernet encryption key and Starlette session signing secret. Must remain stable. |
| `AUTH_COOKIE_SECURE` | `false` | Marks the application session cookie Secure when enabled. Use with HTTPS. |
| `DEBUG` | `false` | Passed to SQLAlchemy as its `echo` flag; enables SQL logging. |
| `MAX_UPLOAD_SIZE_MB` | `15` | General image/upload size limit. |
| `MAX_SAVE_ARCHIVE_SIZE_MB` | `4096` | Save archive upload limit except world-save archives. |
| `MAX_CLIP_SIZE_MB` | `500` | Clip/soundtrack media limit. |
| `MAX_WORLD_SAVE_SIZE_MB` | `2000` | World-save/modpack archive limit where applicable. |
| `PRIMARY_USER_USERNAME` | empty | Legacy automatic first-user bootstrap. |
| `PRIMARY_USER_EMAIL` | empty | Legacy automatic first-user bootstrap. |
| `PRIMARY_USER_PASSWORD` | empty | Legacy automatic first-user bootstrap. |
| `STEAMGRIDDB_API_KEY` | optional | Environment fallback for SteamGridDB. |
| `RETROACHIEVEMENTS_API_KEY` | optional | Environment fallback for RetroAchievements. |
| `GIANTBOMB_API_KEY` | optional | Environment fallback for GiantBomb. |
| `IGDB_CLIENT_ID` | optional | Environment fallback for IGDB client ID. |
| `IGDB_CLIENT_SECRET` | optional | Environment fallback for IGDB client secret. |
| `TMDB_API_KEY` | optional | Environment fallback for TMDB. |
| `OMDB_API_KEY` | optional | Environment fallback for OMDb. |
| `TVDB_API_KEY` | optional | Environment fallback for TheTVDB. |
| `SCREENSCRAPER_DEVID` | optional | ScreenScraper developer ID fallback. |
| `SCREENSCRAPER_DEVPASSWORD` | optional | ScreenScraper developer password fallback. |
| `SCREENSCRAPER_SSID` | optional | ScreenScraper session/user identifier fallback. |
| `SCREENSCRAPER_SSPASSWORD` | optional | ScreenScraper user password fallback. |
| `OIDC_ISSUER_URL` | optional | Backwards-compatible/default OIDC issuer fallback. |
| `OIDC_CLIENT_ID` | optional | Backwards-compatible/default OIDC client ID fallback. |
| `OIDC_CLIENT_SECRET` | optional | Backwards-compatible/default OIDC client secret fallback. |
| `OIDC_REDIRECT_URI` | optional | OIDC callback override for the environment fallback. |
| `OIDC_SCOPES` | `openid profile email` | Requested OIDC scopes for the environment fallback. |
| `OIDC_GROUPS_CLAIM` | `groups` | Claim name used for group-based admin mapping. |
| `OIDC_ADMIN_GROUP` | empty | Optional group whose membership grants admin status. |
| `OIDC_USER_MATCH_FIELD` | `email` | Matches an OIDC identity to a local account by email or username. |

### Credential precedence

For deployment-wide metadata credentials, database-backed Settings generally take precedence over environment values. User-specific credentials are more specific and can take precedence over deployment defaults for providers that support them.

The startup code also applies deployment credentials into the in-process provider settings so older provider clients see the effective deployment fallback.

## Compose/deployment variables

| Variable | Where | Purpose |
|---|---|---|
| `POSTGRES_USER` | Compose | PostgreSQL username and part of generated `DATABASE_URL`. |
| `POSTGRES_PASSWORD` | Compose | PostgreSQL password and part of generated `DATABASE_URL`. |
| `POSTGRES_DB` | Compose | PostgreSQL database name and part of generated `DATABASE_URL`. |
| `UNNAMED_TRACKING_APP_VERSION` | production Compose | GHCR image tag; defaults to `latest`. |
| `UNNAMED_TRACKING_APP_PORT` | production Compose | Host port mapped to container port 80; defaults to `8080`. |
| `PYTHONUNBUFFERED` | development/production container | Python runtime output buffering behaviour; production image sets it internally. |
| `PYTHONDONTWRITEBYTECODE` | production image | Python runtime image setting; set internally by the Dockerfile. |
| `JAVA_HOME` / `PATH` | backend image | Internal BlueMap/Java runtime configuration; not normal application configuration. |

The production Compose file explicitly passes `DATABASE_URL`, `SECRET_KEY`, `PRIMARY_USER_*` and `AUTH_COOKIE_SECURE` to the application. The development Compose file uses `.env` plus an explicitly constructed `DATABASE_URL`.

## Frontend variables

### `VITE_USE_MOCK_DATA`

This is actively consumed throughout frontend services/components. When exactly `true`, many API operations return local mock data or skip real API calls.

It is a development/testing switch and should not be enabled for a real deployment.

### `VITE_API_BASE_URL`

This is declared in the frontend TypeScript environment type and appears in `example.env`, but the current frontend code predominantly uses relative `/api` URLs and the Vite proxy. No current consumer was found for the value itself.

It should therefore be treated as **stale/unused configuration** until the frontend is changed to consume it.

## Documentation inconsistencies found

The environment examples are not currently a single authoritative schema:

- `example.env` contains `SECRET_KEY` twice.
- `example.env` does not list every backend setting.
- The root example and production example intentionally serve different deployment models.
- `VITE_API_BASE_URL` is documented but currently unused.
- Some provider credentials have moved from environment-first configuration to encrypted database-backed Settings while environment fallbacks remain supported.

The planned .env handler should establish one authoritative configuration model and should be accompanied by tests proving precedence, defaults, typing and secret handling.
