# API

The backend is a FastAPI application and generates its OpenAPI documentation from the running code.

## Interactive documentation

For a running instance, open:

```text
https://<your-host>/api/docs
```

The exact endpoints and request/response schemas shown there are generated from the installed application, so this is the authoritative API reference for that deployment.

## Authentication

The normal web application authenticates with a server-side session cookie.

API clients can also authenticate with a user API key:

```http
Authorization: Bearer utk_<secret>
```

User API keys are created for individual accounts and can be revoked. The backend hashes the key for persistence rather than storing the full secret.

The game API and other authenticated routes resolve the caller from either the bearer API key or the normal session cookie.

## Title protection

`PATCH /api/game/update/{id}`, `/api/movie/update/{id}`, `/api/tv/update/{id}`,
and `/api/anime/update/{id}` accept an optional JSON boolean `title_lock`:

- Omitted: preserve existing protection. A manual title change still automatically locks it.
- `true`: protect the title, including when its text is unchanged.
- `false`: remove protection. A title change and protection change in the same request are atomic.

Protection is stored in `locked_fields` as `"title"`. Providers, imports, and
background metadata updates preserve protected fields. Only a valid application
sign-in session (password or OIDC) may explicitly change protection or edit an
already-protected title. API keys may still edit an unprotected title; that edit
automatically protects it. Sending an unchanged title with an ordinary update is allowed.

**Title protection is enforced by the backend. An API client cannot remove
protection or modify a protected title merely by supplying `title_lock=false`
or another request parameter.** These attempts return `403 Forbidden`. API-key
authentication takes precedence even when a valid session cookie is also supplied.
User-Agent, Origin, Referer, and client-defined UI headers grant no authority.

Plugin credentials do not establish application sign-in sessions. Existing
`media.write` and `api.full` grants do not authorize protected-title management:
direct plugin sync title edits are forbidden, while metadata enrichment preserves
the title. There is currently no plugin protected-metadata capability.

For new mutation paths, use the shared metadata locking service. Ordinary edits
must pass the authenticated actor to `apply_updates_with_locking`; provider and
import updates must use `apply_metadata_updates`. Load existing rows under a
database row lock before checking protection, so a concurrent UI save cannot
leave a worker using stale lock state. Never assign a persisted library title
directly or accept a replacement `locked_fields` list from a caller.

## User preferences

User preferences are exposed through the existing preferences API. The AniList automatic-import feature adds these per-user fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `anilist_import_enabled` | boolean | Enables scheduled AniList imports for the user. Defaults to `false`. |
| `anilist_import_username` | string | Public AniList username to import. Empty by default; maximum 100 characters. |
| `anilist_import_interval_minutes` | integer | Minimum 60 minutes and maximum 43,200 minutes (30 days). Defaults to 1,440 minutes (24 hours). |
| `anilist_import_update_existing` | boolean | Allows matching existing titles to be updated from AniList. Defaults to `false`. |
| `anilist_import_last_run_at` | integer or null | Unix timestamp maintained by the scheduler after a scheduled import attempt. Defaults to `null`. |

The preferences are scoped to individual users rather than deployments.

The frontend presents the interval as Hourly, Every 6 hours, Twice daily, Daily, or Weekly, with a custom interval from 1 to 720 hours.

## Playnite API surface

The Playnite extension currently uses these authenticated endpoints:

- `GET /api/game/list`
- `POST /api/game/create`
- `PATCH /api/game/update/{game_id}`
- `POST /api/game/{game_id}/assets/{asset_kind}`

See [Playnite](../integrations/playnite.md) for the integration-specific behavior.

## OIDC API surface

The OIDC login flow is exposed under `/api/auth/oidc`:

- `GET /api/auth/oidc/status` — reports whether OIDC is available and the login providers exposed on the login page.
- `GET /api/auth/oidc/login` — starts the default OIDC login.
- `GET /api/auth/oidc/login/{provider_slug}` — starts a named provider when its autostart policy permits it.
- `GET /api/auth/oidc/callback` — receives the default provider callback.
- `GET /api/auth/oidc/callback/{provider_slug}` — receives a named-provider callback.

OIDC callback handling creates or links a local account and then creates the application's normal session.

## Configuration API

The setup/configuration API is generated from the backend configuration registry. It is used by the generic setup UI and by the post-install configuration editor.

The configuration schema deliberately masks secret values. Environment-owned fields are reported as locked rather than allowing the browser to override deployment configuration.

For the configuration model and environment precedence, see [Configuration](../setup/configuration.md).

## API changes

When changing an API route:

1. Update its Pydantic request/response models where needed.
2. Keep authentication and user scoping explicit.
3. Add or update backend tests.
4. Verify the generated `/api/docs` output.
5. Update integration documentation when a documented client such as Playnite depends on the contract.
