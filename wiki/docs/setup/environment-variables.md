# Environment Variables

Environment variables are optional deployment configuration unless explicitly marked otherwise.

For the Arcane deployment guide, the only environment values needed for a basic deployment are `POSTGRES_PASSWORD` and `AUTH_COOKIE_SECURE`. The Compose file supplies defaults for the remaining PostgreSQL connection settings.

## Database

| Variable | Description |
|---|---|
| `POSTGRES_USER` | PostgreSQL username. The Compose deployment defaults to `unnamed_tracking`. |
| `POSTGRES_PASSWORD` | PostgreSQL password. **Required for the standard Compose deployment.** Use a strong, unique value. |
| `POSTGRES_DB` | PostgreSQL database name. The Compose deployment defaults to `unnamed_tracking`. |
| `POSTGRES_HOST` | PostgreSQL host. Defaults to `db`. |
| `POSTGRES_PORT` | PostgreSQL port. Defaults to `5432`. |
| `DATABASE_URL` | Legacy database connection URL. Prefer the individual `POSTGRES_*` variables. |

## Application

| Variable | Description |
|---|---|
| `SECRET_KEY` | Stable key used for encryption and session/authentication signing. If omitted, the application generates and persists one. |
| `AUTH_COOKIE_SECURE` | Controls whether authentication cookies require HTTPS. Use `false` for direct HTTP access and `true` when users access the app through HTTPS, including HTTPS terminated by a reverse proxy. |
| `DEBUG` | Enables debug mode. Defaults to `false`. |
| `STARTUP_MODE` | Selects the startup profile. `dev`/`development` skips setup after installation; `testing` shows setup with testing/development defaults; empty or other values use normal setup behavior. |
| `MAX_UPLOAD_SIZE_MB` | Maximum general upload size in MB. Defaults to `15`. |
| `MAX_SAVE_ARCHIVE_SIZE_MB` | Maximum game save archive size in MB. Defaults to `4096`. |
| `MAX_CLIP_SIZE_MB` | Maximum clip size in MB. Defaults to `500`. |
| `MAX_WORLD_SAVE_SIZE_MB` | Maximum game world save size in MB. Defaults to `2000`. |

## First-user bootstrap

These are legacy bootstrap options. The normal setup UI is preferred.

| Variable | Description |
|---|---|
| `PRIMARY_USER_USERNAME` | Username for the initial administrator when using environment-based bootstrap. |
| `PRIMARY_USER_EMAIL` | Email address for the initial administrator when using environment-based bootstrap. |
| `PRIMARY_USER_PASSWORD` | Password for the initial administrator when using environment-based bootstrap. |

## Metadata providers

| Variable | Description |
|---|---|
| `STEAMGRIDDB_API_KEY` | API key used to access SteamGridDB metadata/art assets. |
| `IGDB_CLIENT_ID` | IGDB client ID used for game metadata access. |
| `IGDB_CLIENT_SECRET` | IGDB client secret used for game metadata access. |
| `TMDB_API_KEY` | TMDB API key used for movie and TV metadata. |
| `OMDB_API_KEY` | OMDb API key used for movie/TV metadata. |
| `TVDB_API_KEY` | TVDB API key used for TV metadata. |
| `SCREENSCRAPER_DEVID` | ScreenScraper developer ID. |
| `SCREENSCRAPER_DEVPASSWORD` | ScreenScraper developer password. |
| `SCREENSCRAPER_SSID` | ScreenScraper session ID. |
| `SCREENSCRAPER_SSPASSWORD` | ScreenScraper session password. |

## Account & data integrations

These integrations are used for external account connections, user-specific data, libraries, achievements, or importing data rather than general media metadata.

| Variable | Description |
|---|---|
| `XBOX_CLIENT_ID` | Xbox integration client ID. |
| `XBOX_CLIENT_SECRET` | Xbox integration client secret. |
| `GIANTBOMB_API_KEY` | API key used for GiantBomb integration and related game data. |
| `RETROACHIEVEMENTS_API_KEY` | API key used to access RetroAchievements data. |

## OpenID Connect / SSO

| Variable | Description |
|---|---|
| `OIDC_ISSUER_URL` | OpenID Connect issuer/discovery URL. |
| `OIDC_CLIENT_ID` | OpenID Connect client ID. |
| `OIDC_CLIENT_SECRET` | OpenID Connect client secret. |
| `OIDC_SCOPES` | Space-separated OpenID Connect scopes. Defaults to `openid profile email`. |
| `OIDC_GROUPS_CLAIM` | Claim containing group memberships. Defaults to `groups`. |
| `OIDC_ADMIN_GROUP` | Optional OIDC group whose members receive administrator access. |
| `OIDC_USER_MATCH_FIELD` | Field used to match an OIDC user to an existing account: `email` or `username`. Defaults to `email`. |

> **OIDC redirect URI:** Do not set `OIDC_REDIRECT_URI`. The application generates the callback URL from the current request. See [OIDC / SSO](../integrations/oidc.md).

## Frontend development

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Frontend build-time API base URL. |
| `VITE_USE_MOCK_DATA` | Enables frontend mock data/development behavior instead of normal API-backed behavior. This is a frontend-only development setting. |

## Legacy and application-managed settings

Some settings are stored through the application's setup/settings system rather than being intended as environment variables.

Environment-provided values take precedence wherever the application defines an environment-backed setting.

Never put real credentials or secrets into `example.env`.
