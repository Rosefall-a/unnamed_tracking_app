# Data model proposal

Games → worlds → snapshots → runtimes → sessions → visualisations.

The existing `game_archives` (kind `world_save`) and `game_archive_versions` tables become the world and its snapshots. Everything new is **host-owned core data**, not plugin storage. It must outlive the plugin, the Pelican server, and a plugin uninstall or purge (D3). Names are illustrative.

## Extended existing tables

### `game_archives` (kind `world_save`) = **World**

| Column (new) | Type | Purpose |
| --- | --- | --- |
| `adapter_id` | text, nullable | `minecraft-java`, `luanti`, … Chosen at creation or detected on first validation |
| `identity` | jsonb | Stable identity extracted by the adapter (Minecraft: seed, level name; Luanti: seed, gameid). Used to catch a server silently generating a new world (E08b, E10). |

### `game_archive_versions` = **Snapshot**

| Column (new) | Type | Purpose |
| --- | --- | --- |
| `sha256` | char(64) | Integrity; dedupe; part of the custody marker |
| `source` | text | `upload` \| `pelican_capture` \| `pelican_backup_import` |
| `runtime_id` | fk `hosted_runtimes`, nullable | Where it was captured from |
| `pelican_backup_uuid` | uuid, nullable | Pelican's transient copy (may disappear, E08d) |
| `capture_mode` | text, nullable | `hot` \| `cold` |
| `game_version` / `data_version` | text / int, nullable | Compatibility checks (newer-version crash loop, E08b) |
| `metadata` | jsonb | Adapter extraction: level name, day, weather, spawn, explored chunk count, saved players (E09) |
| `parent_version_id` | fk self, nullable | Lineage now; branching later |

## New tables

### `hosting_connections`

One Pelican Panel per row (more than one Panel later).

| Column | Notes |
| --- | --- |
| `id`, `provider` (`pelican`), `panel_url` (origin, fixed) | The bridge only talks to this origin and the Wings hosts the Panel returns |
| `credential_encrypted`, `credential_identifier` | Fernet, like `AppIntegrationSettings`; only the `pacc_…` identifier is ever displayed |
| `status`, `last_checked_at`, `last_error` | Health: auth, key-sprawl audit (E06), Wings reachability |
| `created_by` | Admin |

### `hosting_server_assignments`

Which UT user may use which Pelican server (open question Q1).

| Column | Notes |
| --- | --- |
| `connection_id`, `server_uuid` | Unique together |
| `user_id` | UT owner of that runtime slot |
| `assigned_by`, `assigned_at`, `method` | `admin` \| `claim_code` |

### `hosted_runtimes`

The binding of one world to one server.

| Column | Notes |
| --- | --- |
| `id`, `world_id` (fk `game_archives`), `connection_id`, `server_uuid`, `server_identifier`, `external_id` | Unique active binding per world **and** per server |
| `custody_state` | `in_ut` \| `deploying` \| `on_server` \| `capturing` \| `conflict` \| `detached` |
| `deployed_version_id`, `deployed_at`, `deploy_job_id` | What is on the server; mirrored in `/.ut-custody.json` (E11) |
| `captured_through` | Last successful capture time while `on_server` |
| `join_host`, `join_port`, `game_version` | From `alias ?: ip` and egg variables (E03) |
| `last_status`, `last_status_at`, `node_reachable` | From the websocket supervisor, not REST (E02, E08b) |

### `runtime_events` (append-only)

`id, runtime_id, world_id, type, payload jsonb, source (ws|api|bridge), occurred_at`.

Types: `status`, `crash` (exit code, OOM flag), `deploy.started|succeeded|failed|rolled_back`, `capture.started|succeeded|failed`, `restore.*`, `detached`, `conflict`. Delivered to the plugin through `events.poll` as `hosted.*` event types.

### `play_sessions` (D5)

| Column | Notes |
| --- | --- |
| `id`, `world_id`, `runtime_id`, `game_id` (denormalised), `user_id` (world owner) | |
| `player_key`, `player_name` | UUID when the adapter can resolve one, else the name |
| `started_at`, `ended_at` | From join and leave lines (E07) |
| `end_reason` | `left` \| `crash` \| `server_stopped` \| `bridge_lost` \| `reconciled` |
| `captured_in_version_id` | The snapshot that first contains this session's progress |

Derived, never stored in `Game.playtime_seconds`:

* **hosted playtime** per world and per game = Σ session durations;
* **server runtime** = Σ `running → offline` intervals from `runtime_events`;
* **occupied time** = union of session intervals.

E07 shows why all three differ: 37.8 s player time, 41.7 s runtime, 26.0 s occupied.

### `position_samples` (optional, retention-limited)

`session_id, t, x, y, z, dimension`. Off by default. Kept at most N days, or downsampled once a snapshot exists.

### `world_map_renders`

Replaces the in-memory render status in `bluemap.py`.

`version_id, renderer (bluemap|adapter), status, detail, output_path, thumbnail_path, created_at`. A render belongs to a **version**, so history works: the world as of each snapshot, with that window's session overlays (E09b).

## Plugin-facing contracts (proposal)

DTOs exposed through the gateway, never ORM objects:

* `WorldRepresentation {id, game_id, name, adapter_id, identity, latest_version, runtime?}`
* `WorldVersionRepresentation {id, created_at, size, sha256, source, game_version, metadata, capture_mode}`
* `HostedRuntimeRepresentation {id, world_id, server {identifier, name}, custody_state, deployed_version_id, join {host, port}, status, node_reachable}`
* `PlaySessionRepresentation {id, world_id, player_name, started_at, ended_at, end_reason}`
* Events: `hosted.runtime.status`, `hosted.runtime.crash`, `hosted.player.joined`, `hosted.player.left`, `hosted.deploy.*`, `hosted.capture.*`

No contract carries archive bytes, Pelican credentials, signed URLs or file paths.

## Lifecycle rules

* A world deleted in UT (soft delete) detaches its runtime. Nothing on the server is deleted automatically.
* A Pelican server deleted → `detached` on the next refresh. The world, versions, sessions and renders are untouched (E08d shows Pelican loses its backups).
* Plugin disable or uninstall stops orchestration. **Host-owned world data stays**; a plugin purge only removes plugin configuration.
* Retention: archive versions follow a per-world policy (keep the last N plus daily/weekly). `.ut-prev/*` asides on servers keep the newest N (screenshot 03 shows them accumulating). Position samples are time-boxed.
