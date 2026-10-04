# Unnamed Tracking plugin system and data model audit

Base: `plugin-manager` @ `b52b0719`. Plugins repo: `unnamed_tracking_app_plugins@main` (`9a88160`). Every statement below was read in code. Where the wiki and code disagree, it says so.

## Lifecycle (host-owned)

| Area | What exists | Fit for a Pelican plugin |
| --- | --- | --- |
| Install | Preview → verify (archive limits, canonical payload SHA-256, Ed25519 publisher signature, compatibility, dependencies, route ownership) → per-capability allow/deny → commit with a durable receipt | ✅ standard |
| Manifest | `manifest_version 1`, ID and semver, entrypoint, SDK and app ranges, capabilities and permissions with rationales, backend routes, UI document, optional sandboxed `frontend` and privileged `native_frontend`, `storage.quota_mb` | ✅ |
| Enable / disable / start / stop | Persisted preference. Disable stops workers and keeps grants and secrets. | ✅ |
| Update | Staged; **new scopes require review**; same verified publisher key keeps grants; unsigned updates lose all grants | ✅ adding a bridge capability later means a reviewed update |
| Rollback / reinstall | Packages switch, data is kept; revocations survive | ✅ |
| Uninstall / purge | Removes package, storage and grants | ⚠️ the host-side world/runtime/session tables proposed here must **not** be purged with the plugin (decision D3: UT is the record) |
| Failure handling | Failed activation restores the predecessor and its grants; health = process survives the grace period | ✅ |

## Runtime isolation (what plugin code can physically do)

* Each worker runs in **Bubblewrap with its own network namespace and no network** (`wiki/…/plugin-runtime.md`, `src/plugin-runtime/runtime.py`).
* No application-data mounts. `/plugin-data` is empty; storage goes through the broker.
* `ResourceLimits`: **60 CPU-seconds** (`RLIMIT_CPU`, cumulative per process), 256 MiB address space, 256 files, 32 processes. An unexpected exit is logged (`runtime.exited`). **No automatic restart was found** in `runtime.py`, which is a risk for a long-lived poller and should be confirmed.
* Actions and backend routes: JSON only, **48 KiB request, 64 KiB response, 30 s wall timeout**.

**Consequence:** a sandboxed plugin can never hold a websocket or move world bytes. This is why decision D1 places that work in a host bridge.

## Capability registry (`plugin_api/contracts.py`, `capabilities.py`)

Hierarchical, default-deny, installation-scoped, optionally user-scoped. Device scope exists but no transport authenticates a device. Risk bands are host-owned.

| Capability | Gateway methods actually deployed | Relevance |
| --- | --- | --- |
| `network.outbound` (high) | `network.request` → **host-executed** `outbound_json`: **GET/POST only**, JSON object body ≤ 64 KiB, JSON response ≤ 4 MiB, 8 s timeout, header allow-list `accept, authorization, x-emby-token`, redirects refused, **any host or IP** | Too narrow for Pelican: no PUT (rename), no DELETE, no binary, no websocket. Too broad as an SSRF surface: no destination allow-list. |
| `plugin.storage` | `storage.get/put/delete/keys`, `secrets/<key>` via the frontend bridge. Runtime-local. **64 MiB default quota.** | Plugin config and state only; never saves |
| `plugin.settings` | `settings.get` | Admin config (Panel URL, defaults) |
| `tasks.background` | `tasks.subscribe/unsubscribe/subscribers/request`: per-user consent to background work; workers loop and `sleep` (Jellyfin pattern) | Poller and orchestrator loop |
| `games.read` | `games.list`, `games.metadata.search` | Find the game a world belongs to |
| `games.write` (high) | **No deployed gateway method.** Used only in the validation harness (`validation.py`). | Can't record hosted playtime, last played or status. A new method is needed (Track milestone) |
| `documents.read` | `documents.list/read` (≤ 5 MiB, PDF or text) | Not world saves |
| `media.read/write` | `media.list/import/sync` (movies, TV, anime) | Not games |
| `events.subscribe` | `events.poll` synthesises `game.updated` and `media.added` from table timestamps | A natural delivery path for hosted-world events, once extended |
| `notifications.send` (high) | user-scoped in-app notification, then provider fan-out | "Your world is ready" / "server crashed" |
| `frontend.page.extend` + `frontend.context.game` (low) | declarative content at the `game.overview.after-header` slot, with the game ID in action context | "Continue Playing" panel on the game page, **without** `frontend.native` |
| `frontend.navigation.*`, `frontend.routes`, `frontend.settings` (low) | sidebar entry, plugin pages, settings section | "Worlds" page and connection settings |
| `frontend.native` (critical) | Vue bundle in the host document | Optional; avoid for milestone 1 |
| `backend.routes.plugin` (high) | JSON routes under `/api/plugins/<id>/…` | Optional (plugin pages can use actions) |
| `api.full` (critical) | implies the domain APIs | **Not needed. Do not request it.** |
| `sessions.*` | **Login sessions**, not play sessions | Name collision to avoid in new contracts |

**Doc drift:** `plugin-runtime.md` says "the current gateway does not expose a general-purpose network forwarding method", but `network.request` now exists (added with media sync, #383).

## Data model (what already exists)

| Concept | Model | Notes for the integration |
| --- | --- | --- |
| Game | `games` (`database/models/game.py`) | `playtime_seconds` (**overwritten by Steam sync**, `library_sync.py:559`), `last_played`, `resume_note`, `status`, `external_id` (library provider), `parent_game_id` + `relationship_type` (modpack, mod, DLC tree) |
| **World / save** | `game_archives` with `kind="world_save"` (`game_archive.py`) | Named, durable identity ("Main World") with `deleted_at` soft delete. **This is the world.** |
| **Snapshot** | `game_archive_versions` | `filename`, `size`, `uploaded_at`. **No checksum, provenance, game version or source.** Files live under `/data/users/<uid>/games/<folder>/world_saves/<archive>/`. Uploads are streamed and capped by `MAX_WORLD_SAVE_SIZE_MB = 2000`. |
| Map | `features/world_map/bluemap.py`, `thumbnail.py`, routes in `api/routes/game_archives.py` | BlueMap CLI 5.23 render of an archive's **latest** version. In-memory status. Extraction is **zip only** (Pelican backups are `tar.gz`). The thumbnail reads `world/region` only (fails on the 26.1 layout, E09). The first render downloads Mojang assets. |
| Game profiles and stat snapshots | `game_profiles`, `game_profile_stat_snapshots` | OSRS-specific today; a pattern for periodic snapshots |
| Media | `media_items` (screenshots, clips, soundtrack) | Map renders could become media items later |
| Integration secrets | `AppIntegrationSettings`, `core/crypto.py` | **Fernet-encrypted, never echoed.** The precedent for the bridge credential |
| Notifications | `notifications`, `notification_deliveries`, providers | Reused via `notifications.send` |
| Jobs / scheduled tasks | `features/jobs.py`, `job_setting` | Reused for periodic capture and retention |
| Play sessions | **none** | New (decision D5) |
| Server runtime binding | **none** | New |

## What is sufficient, and what is missing

Sufficient as-is: lifecycle, consent and review; secrets and storage for plugin configuration; background-task consent; notifications; declarative UI on the game page; settings pages.

Missing, all **proposed, not implemented** (see [architecture](architecture.md) and [roadmap](roadmap.md)):

1. **Pelican bridge capabilities** (D1), host-implemented, Panel-URL-bound: power, status, websocket subscription, deploy-from-archive, capture-to-archive, small-file read and write, and a backup operations subset.
2. **World archive capabilities**: `games.worlds.read` (list worlds and versions, metadata) and `games.worlds.write` (create a version from a bridge capture, record provenance). No raw bytes cross into the sandbox.
3. **Hosted play-session writes**: `games.play_sessions.write` (or a bridge-internal writer) for D5.
4. **A world context** for UI: a `frontend.context.world` and/or a `game.worlds.item.actions` slot, so "Continue Playing" can sit on each world, not only on the game header.
5. **Core fixes the integration depends on**: tar.gz extraction for world renders; the 26.1 world-layout-aware thumbnail; checksum and provenance columns on archive versions.
