# Development roadmap

The milestones follow what the investigation found, not a fixed four-release split. Each one is usable on its own and builds toward the world-centric product. Two decisions reshape the obvious order:

* **D4** puts custody and capture-back inside the first user-facing milestone, because Continue Playing without them can overwrite progress.
* **D2** moves server creation late.

| Milestone | Theme | User-visible outcome |
| --- | --- | --- |
| **M0** | World foundations in core | Safer world maps, checksums, 26.1 worlds render; no Pelican yet |
| **M1** | Continue Playing | Press a button, your saved Minecraft world runs on Pelican and you're told how to join; Stop & Save brings it home |
| **M2** | Hosted play history | Who played, when and for how long, per world; crash-aware; periodic snapshots |
| **M3** | Maps of your worlds | A map for every snapshot, session trails, explored-area growth |
| **M4** | Snapshot management | Restore any snapshot safely, retention, branch a world, move it to another server |
| **M5** | Provisioning and breadth | UT can create the server; Luanti adapter; multiple Panels |
| **M6** | Deep preservation | Environment capture, schedules, long-term export |

---

## M0: World foundations in core (no Pelican)

* **User-facing:** world-map renders and thumbnails work for 26.1-layout worlds and for `tar.gz` saves. Each world-save version shows its size, sha256 and source.
* **Backend:** add `sha256, source, metadata, game_version, data_version, parent_version_id` to `game_archive_versions`. Add `adapter_id, identity` to world archives. Add a `world_map_renders` table, replacing in-memory status and keyed by version. Safe extraction for zip **and tar.gz** with bounds on entries, total size and ratio, and link and device rejection. Make the thumbnail aware of the 26.1 layout (`dimensions/minecraft/overworld/region`).
* **Frontend:** version list shows checksum, source and size; map per version.
* **Plugin capabilities:** define (not yet grant) `games.worlds.read` / `games.worlds.write` contracts.
* **Pelican-side:** none.
* **Game adapter:** Minecraft identity extraction from `level.dat` (seed, name, `DataVersion`) at upload time.
* **Tests:** extraction-bomb, traversal and symlink fixtures (from E08a); 26.1 and legacy layout fixtures (E09); migration tests.
* **Security:** closes the unbounded `extractall` noted in [security-model.md](security-model.md).
* **Dependencies:** none.
* **Acceptance:** world A/B archives from the experiments upload, show identity, and render (thumbnail + fallback map). A bomb or symlink archive is refused with a precise reason.

## M1: Continue Playing (Run + custody + Stop & Save) for Minecraft Java

* **User-facing:**
  * An admin connects a Pelican Panel (URL + key of a dedicated `ut-bridge` account) and assigns Pelican servers to UT users.
  * A user binds one of their worlds to an assigned server.
  * **Continue Playing** on the game page and on each world: validate → deploy (if needed) → start → wait → "Ready: join `host:port`, Minecraft 26.1.2".
  * **Stop & Save** (cold capture → new snapshot).
  * Clear failures with automatic swap-back, and notifications when ready or failed.
* **Backend (bridge):**
  * Connection registry with Fernet secrets, health checks and sibling-key audit.
  * Origin-bound Panel client.
  * Websocket supervisor for **status only**.
  * Deploy job: validate, stop and wait offline, part upload under `upload_size`, staging decompress, rename swap, custody marker, start, readiness timeout, identity check, rollback.
  * Capture job: world-only backup via negated `ignored`, signed download stream, new version with provenance.
  * Custody state machine and server assignments.
  * `hosted_runtimes` and `runtime_events` tables.
* **Frontend:** declarative `game.overview.after-header` panel (no `frontend.native`); Worlds page (plugin route); connection settings section (admin).
* **Plugin capabilities (new):** `pelican.servers.read`, `pelican.servers.power`, `pelican.worlds.deploy`, `pelican.worlds.capture`, `games.worlds.read`, `games.worlds.write`. Plus existing `tasks.background`, `plugin.settings`, `plugin.storage`, `notifications.send`, `frontend.page.extend`, `frontend.context.game`, `frontend.navigation.main`, `frontend.settings`, `frontend.routes`. New UI context: `frontend.context.world` or a world-actions slot.
* **Pelican-side:** a `ut-bridge` account added as a subuser with the 17 permissions on each participating server; key `allowed_ips`; node `upload_size` ≥ the part size. **No Pelican plugin.**
* **Game adapter:** `minecraft-java` descriptor: world root from `server.properties`, `required: [level.dat]`, identity, `DataVersion` compatibility, readiness timeout, `seed` verification, cold capture.
* **Tests:**
  * Unit tests: validator, state machine, custody transitions.
  * Integration suite against a disposable Pelican built by `experiments/setup_env.sh` (nightly or manual CI job): E03, E04c, E08a, E08b and E12 scenarios through the bridge.
  * A **vanilla and Paper confirmation run** once Mojang and PaperMC hosts are allowed.
* **Security:** server assignment enforced on every call; command allow-list; no deletes; no `kill` without consent; throttles respected.
* **Dependencies:** M0; open questions Q1 (assignment model) and Q2 (bridge placement detail).
* **Acceptance:**
  * With the two test worlds: Continue Playing on an empty bound server → the client sees the right markers.
  * Stop & Save → a new version, byte-identical to the server's world.
  * Continue Playing again does **not** redeploy (custody `on_server`).
  * Deploying world B onto a server holding world A is refused until A is captured.
  * A save without `level.dat` is refused before upload, and if forced, detected after start and rolled back.
  * A newer-version world is reported as such, with the previous world restored.

## M2: Hosted play history (Track)

* **User-facing:** per-world timeline (deploys, starts, stops, crashes, captures); per-world and per-game **hosted playtime** shown next to the existing counter (D5); player list with last seen; "currently online" on the world card; optional session-end auto-capture and periodic hot snapshots.
* **Backend:** the websocket supervisor parses adapter patterns into `play_sessions` (crash closes open sessions); reconciliation via `list` after a bridge restart; `events.poll` extension (`hosted.*`); the capture **skip rule** (no sessions since the last capture → skip); hot capture (`save-off`/`save-all` → backup → `save-on`).
* **Frontend:** timeline and session list components (declarative); hosted-playtime badge.
* **Plugin capabilities:** `pelican.events.subscribe`. Hosted sessions are written by the bridge, so **no `games.write`**.
* **Pelican-side:** unchanged. Optionally detect the `player-counter` plugin and use `/query/players` as a presence fallback.
* **Game adapter:** join, leave, login and `list` patterns; hot-capture commands.
* **Tests:** the E07 scenario (two players, overlapping), crash mid-session (E08b), a Wings restart during a session, JWT refresh past 10 minutes.
* **Security:** player-name validation; console parsing caps.
* **Dependencies:** M1.
* **Acceptance:** hosted playtime within ±2 s of client ground truth; server runtime and occupied time reported separately; a crash closes sessions with `end_reason=crash`.

## M3: Maps of your worlds (Visualise)

* **User-facing:** a map for every snapshot (BlueMap via the existing core pipeline, D6); a fallback top-down map when BlueMap can't run; session position trails and saved player positions; explored-area growth between snapshots; world facts (day, weather, spawn, version).
* **Backend:** a render job per new version (`world_map_renders`); opt-in position sampling with retention; overlay data API.
* **Frontend:** map viewer per version (existing iframe viewer); overlay layer; snapshot comparison (explored chunks).
* **Plugin capabilities:** none new beyond M2 (reads go through `games.worlds.read`).
* **Pelican-side:** unchanged.
* **Game adapter:** `position_command` and pattern; the fallback renderer.
* **Tests:** the E09/E09b association reproduced through UT; BlueMap on vanilla worlds (needs Mojang egress).
* **Security:** renders run on validated extractions only.
* **Dependencies:** M0, M2 (trails).
* **Acceptance:** each captured version has a map; the trail from a session appears on the following snapshot's map.

## M4: Snapshot management (Preserve)

* **User-facing:** restore any snapshot (safe sequence), "save current first" enforced; retention policies; branch a snapshot into a new world; move a world to another assigned server.
* **Backend:** restore job (Flow 7, never `truncate`, never while running); a Pelican backup immediately before swaps as the short-lived safety net (needs `backup.delete` for rotation, an 18th permission); retention sweeper for UT versions and `.ut-prev/` asides.
* **Frontend:** version actions (restore, branch); retention settings.
* **Plugin capabilities:** unchanged (`pelican.worlds.deploy` covers restore).
* **Pelican-side:** add `backup.delete` to the bridge's subuser permissions if the safety net is enabled.
* **Tests:** the E04c scenario through UT; retention edge cases; restore while a player is online (must refuse or stop with consent).
* **Security:** destructive actions double-confirmed; audit events.
* **Dependencies:** M1 (M3 is nice to have for previews).
* **Acceptance:** restoring version N gives a byte-identical world (E04c) and keeps the pre-restore state as a version.

## M5: Provisioning and breadth

* **User-facing:** "Create a server for this world" (admin-enabled); the Luanti adapter; several Pelican Panels.
* **Backend:** an optional Application key (admin, IP-pinned) and server creation with `external_id = ut-world:<uuid>` (E01); egg and node allow-lists in UT; Luanti adapter (cold capture, `minetestmapper` fallback, upload-limit check for `map.sqlite`).
* **Pelican-side:** optionally a small Pelican plugin to enforce allowed eggs and nodes server-side ([audit](pelican-plugin-audit.md)); Luanti egg without `--terminal` (E10).
* **Tests:** the E01 scenario; E10 through UT.
* **Dependencies:** M1–M2.
* **Acceptance:** the E10 sequence runs through UT unchanged apart from the adapter descriptor.

## M6: Deep preservation and automation

Environment capture (egg export, game version, mod and plugin list), scheduled snapshots, long-term export (download a world with its history and maps), share a read-only world page, cross-instance migration. Mostly product decisions; the technical primitives exist after M4.

---

## Out of scope for the first implementation

| Item | Why (evidence) |
| --- | --- |
| Arbitrary Pelican administration (users, nodes, databases, schedules) | Not needed; widens the credential |
| Generic filesystem browsing of game servers | The bridge only touches the world root and the `.ut-*` namespace |
| Automatic mod installation or updates | Needs per-loader logic (e.g. the `minecraft-modrinth` Pelican plugin's domain) |
| Arbitrary server configuration (startup, image, variables) | Not in the 17 permissions (E06) |
| Universal game support | One adapter per game; the descriptor format is proven on two games (E10) |
| Automatic game version upgrades | Newer worlds crash-loop older servers (E08b); upgrades are destructive |
| Live web maps (BlueMap/squaremap on the server) | Needs Paper, plugin install and an extra allocation (D6 chose snapshots) |
| Server creation in M1–M4 | D2 |
| SFTP | Password-equivalent credential |
| Pelican companion plugin | Not required ([audit](pelican-plugin-audit.md)) |
| Cross-game save conversion | No basis |

## Proposed PRs

| # | Repository → base | Content | Milestone |
| --- | --- | --- | --- |
| 1 | `unnamed_tracking_app` → `plugin-manager` | **This PR:** discovery record (docs and experiments only) | — |
| 2 | `unnamed_tracking_app` → `plugin-manager` | Core world foundations: version provenance columns, safe zip/tar extraction, 26.1 thumbnail, render table | M0 |
| 3 | `unnamed_tracking_app` → `plugin-manager` | Pelican bridge: connections, origin-bound client, health and key audit, `pelican.*` and `games.worlds.*` contracts and gateway methods, deploy and capture jobs, custody, websocket status supervisor | M1 |
| 4 | `unnamed_tracking_app_plugins` → `main` | `official/pelican-worlds` v0.1: orchestrator, `minecraft-java` descriptor, declarative UI | M1 |
| 5 | `unnamed_tracking_app` | Disposable-Pelican integration test job (from `setup_env.sh`) | M1 |
| 6+ | both | M2 onward | M2+ |
