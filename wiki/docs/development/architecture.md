# Architecture

Unnamed Tracking App is split into a Python/FastAPI backend and a Vue/Vite frontend, with PostgreSQL providing persistent application data.

## Repository structure

The main application code lives under `src/`:

- `src/backend/src/api/` — FastAPI routes and API schemas.
- `src/backend/src/core/` — configuration, authentication, and other shared backend infrastructure.
- `src/backend/src/database/` — database access and migrations.
- `src/backend/src/features/` — feature-specific backend logic.
- `src/frontend/src/components/` — reusable Vue components.
- `src/frontend/src/views/` — application pages/views.
- `src/frontend/src/services/` — frontend API/service clients.
- `src/frontend/src/router/` — Vue Router configuration.
- `src/frontend/src/state/` — frontend state management.
- `src/frontend/src/types/` — shared frontend TypeScript types.

The backend is the source of truth for application configuration and API behavior. The frontend consumes those APIs rather than maintaining a second backend configuration system.

## Configuration architecture

Deployment configuration is defined by the backend configuration registry.

The flow is:

```
CONFIG_REGISTRY
      |
      v
EnvConfigHandler
      |
      +--> process environment
      +--> .env
      +--> persisted application configuration
      +--> startup-mode defaults
      |
      v
/api/setup/configuration
      |
      v
Vue setup renderer
```

Environment values have higher precedence than persisted settings. Environment-owned fields are treated as deployment-owned and are not editable through the setup UI.

The setup UI is generated from the backend schema, so adding a normal configuration field should generally be handled in the registry rather than by hard-coding another field into the Vue setup component.

## Per-user scheduled AniList imports

AniList automatic imports are implemented as a lightweight extension of the existing application scheduler.

The flow is:

```
existing scheduler loop
        |
        v
per-user AniList preferences
        |
        v
check whether each user's interval is due
        |
        v
reusable AniList import service
        |
        v
that user's anime library
```

The scheduler reads each user's preferences, skips disabled or incomplete configurations, and runs a bounded batch of due users.

The current scheduler checks for due AniList imports once per minute and processes at most four users per tick. This is intentionally bounded so a deployment with many users does not let AniList imports starve the application's other scheduled work.

AniList scheduling is per user rather than an administrator-configured deployment job. It therefore does not use the administrator's Scheduled Tasks settings.

## Database

PostgreSQL is the normal production database.

Schema changes are managed with Alembic migrations. The application startup process applies pending migrations before the backend is considered ready.

Migrations should remain on a single history line. Multiple Alembic heads are treated as an error and should be resolved before deployment.

The application applies pending Alembic migrations during startup. Keep the migration history on a single head and add a new migration rather than editing one that has already shipped.

## Production container

The production deployment is packaged separately under `src/docker-container/`.

The production image contains:

- the built Vue frontend;
- the Python backend and runtime dependencies;
- Nginx;
- the startup/status page and startup scripts.

The container's entrypoint coordinates startup: it prepares the status page, waits for PostgreSQL, applies migrations, starts Uvicorn, waits for the backend health check, and then switches Nginx to the ready configuration.

This means the public HTTP endpoint can display startup status while the application is still initializing.

### Logging architecture

Production-container logging intentionally uses the existing stdout/stderr path rather than introducing a second log aggregation system. Entrypoint lifecycle messages go to stdout, Nginx errors go to stderr, backend output is retained in /run/unnamed-tracking/backend.log, and migration output is retained in /run/unnamed-tracking/migration.log.

The structured startup endpoints expose only status and concise details. Raw backend and migration logs are not public HTTP resources. Operators retrieve detailed logs through Docker logging facilities or directly from the retained files inside the container.

The production entrypoint does not print configuration secrets. New logging code must preserve that rule.
## Artwork and local image copies

A game's artwork is stored as PNG files in its folder: `key_art.png` (600 by 900) and `banner.png` (3840 by 1240, often 5 to 10 MB), plus a logo and an icon. A page rarely needs that much, so smaller copies are made and kept in a cache.

**Games.** `GET /api/game/<id>/assets/<kind>` accepts `?w=<pixels>` (64 to 4096) and returns a JPEG no wider than that. The route that serves it is `api/routes/default_game_assets.py`, which is registered before the one in `games.py` and so is the one that answers. Copies live at `<data>/users/<user-id>/.cache/asset-previews/<game-id>/<kind>-<width>.jpg` and are rebuilt when the original is newer. They are written to a temporary file and moved into place, so a request never reads half a file. The widths the app uses (banner 1920 and 800, cover 400) are also made as soon as artwork is saved (`helpers/asset_previews.py`). An image already as small as asked for is sent unchanged.

**Movies, TV shows and anime.** Their posters and backdrops are addresses on TMDB or AniList. `GET /api/media-image/<movie|tv|anime>/<id>/<poster|backdrop|hero>` downloads the picture once, shrinks it (posters to 400 pixels, backdrops to 1920) and keeps it under `.cache/media-images/`. `hero` is the backdrop, or the poster when there is no backdrop. The file name includes a hash of the source address, so editing the address makes a fresh copy and removes the old one.

The address is whatever was saved on the title, so `helpers/remote_images.py` treats it as untrusted: only http and https, only hosts whose every address is public (loopback, private, link-local and reserved ranges are refused), no redirects, and a 15 MB limit. If a download fails the route answers with a redirect to the original address, so the browser still gets the picture.

Both caches are disposable. Deleting `.cache/` loses nothing that cannot be rebuilt.

**Frontend.** `utils/gameImages.ts` adds the size to a game artwork URL (`sizedAssetUrl`) and starts a download early (`preloadImage`). `utils/mediaImages.ts` turns a title's stored address into the local URL, with a short stamp of the address so a changed picture is not served from the browser's memory. Card grids use `loading="lazy"` on images, and tiles that are CSS backgrounds use the `v-lazy-bg` directive (`directives/lazyBackground.ts`), which sets the image once the tile is near the screen.

## How a game page opens

`services/games.ts` keeps every game it has fetched in an entity cache (`peekGame`). Opening a game from the library draws it from that cache straight away and refreshes it from the server behind it. Its achievements, variants and parent game are requested in parallel with the game, and fill in when they arrive instead of holding the page back. The hero and poster downloads start before the game's details have returned. When there is nothing cached (opening the address directly), a loading screen is shown whose hero, poster and tab bar match the real page's sizes, so the page does not jump when it replaces it.

## Shared building blocks

Movies, TV shows and anime, and game collections and media lists, were near copies of each other. They now share code, and a change to one of these pieces changes all of them:

| Piece | Used by |
| --- | --- |
| `MediaDetailHero`, `MediaDetailTabs`, `ExpandableDescription` | The Movie, TV and Anime detail pages. |
| `MediaFormShell`, `MediaMetadataSearch`, `useMetadataSearch` | The three Add and Edit dialogs. |
| `services/mediaApi.ts` | The movie, TV and anime services (list, get, create, update, delete, trash). |
| `api/routes/media_common.py` | The movie, TV and anime routes (library list, soft delete, trash, restore, purge, title search). |
| `CollectionTile`, `useCardOrder` | The Collections and Lists overview pages. |
| `CollectionDetailHeader`, `CollectionItemTile`, `CollectionAddDialog`, `useReorderGrid` | The collection and list detail pages. |
| `GameMediaPanel`, `MediaTile`, `MediaEditDialog` | Screenshots, Clips, Soundtrack and Docs. |
| `GameArchivesPanel`, `ArchiveCard`, `ArchiveEditDialog` | Saves and Worlds. |

Style rules that were identical across the near copies sit in `src/styles/shared/` and are imported by each component with `<style scoped src="...">`. Rules that belong to one component live in that component. A component's scoped styles do not reach into another component's markup, which is why a shared piece owns the CSS for its own elements.

When adding a field to movies, TV shows and anime, look for the shared piece first and only add per-kind code where the kinds really differ.

## Library ranks

The Movie, TV and Anime list endpoints return `score_ranks`: the position of every rated title for that user across the whole library, highest score first, ties broken by sort title, deleted titles left out. It is computed on the server so a rank does not depend on which page or search result the browser holds.

## Game page settings

What a game's page shows is stored in two places: the user's defaults as the `game_page` preference, and a game's own overrides in `games.page_settings` (JSONB). `core/page_settings.py` validates both, and `utils/gamePage.ts` merges them (defaults, then the game's overrides) and decides which tabs are visible, tucked into the more menu, or hidden. Only what differs from the defaults is stored on a game.

## Migrations for the game pages work

The game pages work adds its tables and columns in one migration, `d4a8b2c6e9f1`, which follows the password policy migration. It uses the create-if-missing helpers, so it is safe on a database adopted from an older history, and its downgrade drops what it added.

## API

The backend exposes the application's REST API under `/api`.

Interactive API documentation is generated by the running FastAPI application and is available at:

`/api/docs`

See [API Documentation](api.md) for how to access it.

## Authentication

Normal application authentication uses server-side sessions and authentication cookies.

OIDC/SSO is integrated into the same application authentication flow. OIDC provider credentials are kept server-side; client secrets are not exposed to the frontend.

See [OIDC / SSO](../integrations/oidc.md) for provider configuration.

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
