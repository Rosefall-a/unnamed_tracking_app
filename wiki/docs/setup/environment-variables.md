# Environment Variables

This page lists the environment variables currently used by the application.

## Database

| Variable | Description |
|---|---|
| `POSTGRES_USER` | PostgreSQL username. Required for the normal PostgreSQL configuration. |
| `POSTGRES_PASSWORD` | PostgreSQL password. Required for the normal PostgreSQL configuration. |
| `POSTGRES_DB` | PostgreSQL database name. Required for the normal PostgreSQL configuration. |
| `POSTGRES_HOST` | PostgreSQL host. Defaults to `db`. |
| `POSTGRES_PORT` | PostgreSQL port. Defaults to `5432`. |
| `DATABASE_URL` | Legacy database connection URL. Prefer the individual `POSTGRES_*` variables. |

## Application

| Variable | Description |
|---|---|
| `SECRET_KEY` | Stable key used for encryption at rest and session/authentication signing. If omitted, the application generates and persists one. |
| `AUTH_COOKIE_SECURE` | Controls whether authentication cookies require HTTPS. Defaults to `false`. |
| `DEBUG` | Enables debug mode. Defaults to `false`. |
| `STARTUP_MODE` | Selects a startup profile. `development`/ `dev` uses development defaults, `testing` uses testing defaults, and other values use normal setup behavior. |
| `MAX_UPLOAD_SIZE_MB` | Maximum general upload size in MB. Defaults to `15`. |
| `MAX_SAVE_ARCHIVE_SIZE_MB` | Maximum game save archive size in MB. Defaults to `4096`. |
| `MAX_CLIP_SIZE_MB` | Maximum clip size in MB. Defaults to `500`. |
| `MAX_WORLD_SAVE_SIZE_MB` | Maximum game world save size in MB. Defaults to `2000`. |

## First-user bootstrap

These variables are legacy bootstrap options. The normal setup UI is preferred.

| Variable | Description |
|---|---|
| `PRIMARY_USER_USERNAME` | Username for the initial administrator when using environment-based bootstrap. |
| `PRIMARY_USER_EMAIL` | Email address for the initial administrator when using environment-based bootstrap. |
| `PRIMARY_USER_PASSWORD` | Password for the initial administrator when using environment-based bootstrap. |

## Metadata and provider integrations

| Variable | Description |
|---|---|
| `STEAMGRIDDB_API_KEY` | API key used to access SteamGridDB metadata/art assets. |
| `RETROACHIEVEMENTS_API_KEY` | API key used to access RetroAchievements data. |
| `GIANTBOMB_API_KEY` | API key used to access GiantBomb game metadata. |
| `IGDB_CLIENT_ID` | IGDB client ID used for game metadata access. |
| `IGDB_CLIENT_SECRET` | IGDB client secret used for game metadata access. |
| `TMDB_API_KEY` | TMDB API key used for movie and TV metadata. |
| `OMDB_API_KEY` | OMDb API key used for movie/TV metadata. |
| `TVDB_API_KEY` | TVDB API key used for TV metadata. |
| `SCREENSCRAPER_DEVID` | ScreenScraper developer ID. |
| `SCREENSCRAPER_DEVPASSWORD` | ScreenScraper developer password. |
| `SCREENSCRAPER_SSID` | ScreenScraper session ID. |
| `SCREENSCRAPER_SSPASSWORD` | ScreenScraper session password. |
| `XBOX_CLIENT_ID` | Xbox integration client ID. |
| `XBOX_CLIENT_SECRET` | Xbox integration client secret. |

## OpenID Connect / SSO

| Variable | Description |
|---|---|
| `OIDC_ISSUER_URL` | OpenID Connect issuer/discovery URL. |
| `OIDC_CLIENT_ID` | OpenID Connect client ID. |
| `OIDC_CLIENT_SECRET` | OpenID Connect client secret. |
| `OIDC_REDIRECT_URI` | OpenID Connect callback URL. Normally generated automatically from the URL used to access the application. |
| `OIDC_SCOPES` | Space-separated OpenID Connect scopes. Defaults to `openid profile email`. |
| `OIDC_GROUPS_CLAIM` | Claim containing group memberships. Defaults to `groups`. |
| `OIDC_ADMIN_GROUP` | Optional OIDC group whose members receive administrator access. |
| `OIDC_USER_MATCH_FIELD` | Field used to match an OIDC user to an existing account: `email` or `username`. Defaults to `email`. |

## Frontend development

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Frontend build-time API base URL. |
| `VITE_USE_MOCK_DATA` | Enables frontend mock data/development behavior instead of normal API-backed behavior. |

## Legacy and application-managed settings

Some configuration settings are stored through the application's setup/settings system rather than being intended as environment variables. They are therefore not listed above even though they appear in the application's configuration registry.

Environment-provided values take precedence where the application defines an environment-backed setting.
