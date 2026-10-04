# Experimental test report

Every result below was observed against a real Pelican Panel `v1.0.0-beta38` and Wings `v1.0.0-beta29`. The environment is described in [test-environment.md](test-environment.md). Scripts are in [`experiments/`](experiments/). Every API call they made is in [`evidence/api-calls.jsonl`](evidence/api-calls.jsonl), with credentials and signed URLs redacted. A from-scratch [reproduction run](#reproduction-run) is recorded at the end.

The game server for E01–E09 and E11–E12 is a **Minecraft 26.1.2-protocol stand-in** (Minestom), because Mojang and PaperMC downloads are blocked by the environment's network policy. It follows the upstream Vanilla egg contract: `server.properties` port rewrite, the `)! For help, type ` readiness line, `stop`, and the vanilla console line formats for join, leave, `seed`, `data get entity` and `save-*`. E10 uses a **real** Luanti (Minetest) 5.6.1 server. Where a result depends on stand-in behaviour rather than Pelican behaviour, it is marked *stand-in*.

Status words follow the capability matrix: **VERIFIED** (observed here), **PARTIALLY VERIFIED** (observed with a caveat), **DOCUMENTED** (read in source or docs, not run).

## E01: create a server for a world (Application API)

`POST /api/application/servers` with `external_id: "ut-world:demo-a"`, egg, image, limits and default allocation.

| Measure | Result |
| --- | --- |
| Create | **201 in 1.18 s**. Status `installing`. |
| Install (egg script) | Finished after **3.17 s** (`status` back to `null`). |
| `GET /servers/external/ut-world:demo-a` | 200, same UUID |
| Second create with the same `external_id` | **422** `The external id has already been taken.` |

VERIFIED. `external_id` is a usable idempotency key for "this world already has a server". The previous session also observed that a single-worker Panel deadlocks on the synchronous Panel → Wings → Panel create call, and that Pelican rolls the half-created server back after a 15 s timeout. The current environment runs 8 PHP workers.

## E02: power lifecycle and readiness (Client API + websocket, non-admin owner)

| Transition | Time | Signal used |
| --- | --- | --- |
| start → ready | 3.86 s | console line `Done (…)! For help, type "help"` |
| stop → offline | 1.16 s | websocket `status: offline` |
| restart → ready | 4.39 s | statuses seen: `running, stopping, offline, starting` |
| kill → offline | 0.58 s | websocket `status: offline` |

`GET /resources` returned `current_state: offline` while the server was demonstrably running. The Panel caches this endpoint (the previous session measured 20 s). **Readiness must come from the websocket.** Websocket event types seen: `console output`, `stats`, `status`. VERIFIED.

## E03: deploy a saved world (Client API only)

Sequence: stop → `GET files/upload` (signed Wings URL, valid 15 min) → multipart upload → `PUT files/rename world → world.ut-prev-<ts>` → `POST files/decompress` → `POST files/delete <archive>` → start → `send command seed` → protocol client.

| Swap | Upload | Decompress | Start → running | Identity check | Protocol client |
| --- | --- | --- | --- | --- | --- |
| A → B (385 KB) | 0.48 s | 0.60 s | 4.07 s | `Seed: [1337]`, `Level "UT Test World B"` | diamond markers at the pillar and pad; spawn at the saved position (−6, 9) |
| B → A (357 KB) | — | — | 3.64 s | `Seed: [424242]`, `Level "UT Test World A"` | gold markers; saved position (4, 4) |

VERIFIED.

**Finding:** a `127.0.0.1` allocation is silently re-bound by Wings to the `pelican0` gateway (`environment/allocations.go` `DockerBindings`), so the Panel-reported join address was not joinable. Use `0.0.0.0` with an allocation alias. The Application API field is `alias`; `ip_alias` is silently ignored. The build endpoint also returns a misleading **404** when moving a server to an allocation not listed in `add_allocations`.

## E04, E04b, E04c: capture and restore via backups

| Step | Result |
| --- | --- |
| Hot capture: `save-off` → `save-all` → `POST backups` (with `ignored`) → websocket `backup completed` | **1.68 s**, 434 403 bytes, sha1 in the event, signed download verified |
| Restore **while running** with `truncate: true` | **Racy (upstream).** Wings truncated the root before the server stopped; the game's shutdown save hit `NoSuchFileException: world/level.dat` *(stand-in log; the ordering is Wings')*. |
| Truncate-restore of a backup that ignored `server.jar` | Root left with only `server.properties` and `world`. Start crash-loops: `Exit code: 1` … `Aborting automatic restart, last crash occurred less than 60 seconds ago`. |
| Recovery: `POST settings/reinstall` | 202, runtime back in **4.25 s**, world untouched (`Seed: [1337]`) |
| **World-only capture (E04d):** `ignored: "*\n!world\n!world/**"` | backup contains **only `world/`** (7 entries): no asides, custody marker or `server.jar` |
| **Safe restore (E04c):** stop → confirm offline → rename world aside → restore `truncate:false` → websocket `backup restore completed` | **7/7 world files byte-identical** to the backup before first start; then running in 3.34 s, `Seed: [1337]`, diamond marker seen by the client |

VERIFIED.

## E05: can Wings fetch the world itself (`files/pull`)?

| Source address | Result |
| --- | --- |
| `127.0.0.1` | Panel **500** (opaque). Wings log: `destination resolves to internal network location` |
| `172.18.0.1` (RFC1918) | Panel **500** (opaque), same Wings error |
| `192.0.2.2` (not RFC1918) | **204 in 1.73 s, sha256 intact** |

Wings hard-blocks loopback, RFC1918, link-local, ULA and `::1` (`router/downloader/downloader.go`). This is not configurable. Pulls are throttled to **5 per 10 min per server**. VERIFIED. **Consequence:** pull cannot be the deploy path for a UT instance on the same LAN as Wings.

## E06: least-privilege bridge identity

A dedicated non-admin Pelican account (`utbridge`) is added by the server owner as a subuser with 17 permissions:

`websocket.connect, control.console, control.start, control.stop, control.restart, file.read, file.read-content, file.create, file.update, file.delete, backup.read, backup.create, backup.download, backup.restore, allocation.read, startup.read, settings.reinstall`

| Probe | Result |
| --- | --- |
| 11 operations the Run/Capture/Restore sequences need | **11/11 allowed** |
| 10 operations outside the set (startup variable, docker image, rename, subusers ×2, compress, databases, schedules, activity, Application API) | **10/10 → 403** |
| Another user's server, power on it, and a non-existent UUID | **404, 404, 404**: no existence leak |
| `POST /api/client/account/api-keys` with the bridge key | ⚠️ **200**: a client key can mint sibling keys (minted key `allowed_ips: []`) |
| `allowed_ips = [203.0.113.7]`, call from 127.0.0.1 | **403**; with `[127.0.0.1]` → 200 |

VERIFIED. Notable mappings from source: `decompress`, `upload` and `pull` need `file.create`; `rename` needs `file.update`; renaming a backup needs `backup.delete`.

## E07: Track from the websocket only (bridge identity)

Two protocol clients follow a schedule; positions are polled with `data get entity <p> Pos`.

| Measure | Value |
| --- | --- |
| Server runtime (status running → offline) | **41.7 s** (`stats.uptime` 43.3 s) |
| Alice session (joined → left lines) | **26.0 s** (client ran 27.4 s including connect/disconnect) |
| Bob session | **11.8 s** (client ran 13.0 s) |
| Sum of player playtime | 37.8 s |
| Time with ≥1 player online | 26.0 s |
| Empty-server time | 15.7 s |
| Position samples | 13 |
| Login line | `Alice[/172.18.0.1:…] logged in with entity id … at (x, y, z)`. Source IP is the Docker gateway (NAT), not the client. |

VERIFIED (Pelican transport). The console line formats are *stand-in* reproductions of vanilla's.

## E08a: hostile and broken archives (bridge identity, staging directory)

| Case | Wings outcome | Left in staging | Escaped to host |
| --- | --- | --- | --- |
| `../../../../tmp/…`, `/tmp/…`, `world/../../…` | rejected during the pre-walk (`readdir ..: invalid argument`) | nothing | none |
| symlink to `/etc` then write through it; hardlink to `/etc/passwd` | symlink written as a **0-byte regular file**; the next entry fails `not a directory` | **partial `world/`** | none |
| truncated tar.gz (60%) | `extract: unexpected EOF` | nothing | none |
| random bytes named `.tar.gz` | `gzip: invalid header` | nothing | none |
| 6 GiB of zeros (6.2 MB compressed) vs a 4 GiB disk limit | refused before writing (by `SpaceAvailableForDecompression`, per Wings' source; Wings logs nothing) | nothing | none |
| upload aborted at 40% | client `ConnectionError` | no new entries | none |

**Every refusal reached the Client API as an opaque `500 RequestException`**, because the Panel discards Wings' error text. VERIFIED.

## E08b: runtime failures

| Case | Observed |
| --- | --- |
| Invalid key | 401 `AuthenticationException` |
| Panel unreachable | connection error |
| Save **without `level.dat`** | `status: running` with a **new random world** (`Seed: [3044165615555320525]`, expected 424242). **Silent substitution.** *(stand-in mirrors vanilla's "create if missing")* |
| Save from a newer version (`DataVersion` + 1000) | crash loop `starting → offline → starting → offline` *(stand-in emulates vanilla's refusal)* |
| Never ready (readiness line suppressed) | `starting` for 45 s+ on both the websocket and REST. **Pelican has no readiness timeout.** |
| Crash (`exit 137`), isolated | unrequested `offline` → `[pelican Daemon] Detected server process in a crashed state! Exit code: 137, Out of memory: false` → automatic restart → `running` at 3.3 s. **No "left the game" lines.** |
| Wings down, Panel up | game keeps running. `GET server`, `GET resources` and `GET websocket` return **stale 200s**; power and files → 500 |
| Wings back | reattaches to the running container; status `running` |

VERIFIED (Pelican behaviour). The game-specific reactions are *stand-in*.

## E08d: deleting the server that hosts a world

`DELETE /api/application/servers/{id}` → 204. Afterwards the Client API returns 404, the `external_id` lookup returns 404, the volume and container are gone, and **the backup archive is gone** (`/var/lib/pelican/backups/<server>/<backup>.tar.gz` present before, absent after; Wings default `remove_backups_on_server_delete: true`). VERIFIED.

## E09, E09b: Visualise from a captured save, with no game assets

* World state from `level.dat`: level name, seed, `DataVersion`, version name, `DayTime`, weather, spawn. Player state from `players/data/<uuid>.dat`: position, dimension, rotation.
* Explored chunks from the region headers: 545 in the original world-A archive, **682** in a later capture.
* An asset-free top-down map (top block per column) with spawn, saved player positions and the session's live position trail: [`img/e09b-snapshot-map-with-session-trail.png`](evidence/img/e09b-snapshot-map-with-session-trail.png).
* Association record (session → Pelican backup → sha256 → map): [`evidence/e09b-association.json`](evidence/e09b-association.json).

| Renderer | Result |
| --- | --- |
| BlueMap CLI 5.23 (what UT core ships) | First pass generates config as UT's `bluemap.py` describes. Render fails fetching **Mojang's version manifest** (blocked here), because BlueMap needs the official client jar for textures. |
| mcmap 3.0.4 | Rejects the stand-in's chunks (it requires `Status == "full"`; Minestom writes lowercase `status`). **Not meaningful for vanilla either way.** |
| UT core `generate_world_thumbnail` | **False** on the 26.1 layout (`dimensions/minecraft/overworld/region`); **True** on the same regions in the pre-26.1 `region/` layout. The layout comes from Minestom 26.1's `AnvilLoader`. Vanilla confirmation is pending. PARTIALLY VERIFIED. |
| Adapter-style renderer (E09) | VERIFIED |

## E10: second game, Luanti (Minetest 5.6.1, real server)

The same Pelican sequence was run with the owner key: generate → upload → staging decompress → swap → start → verify.

| Step | Result |
| --- | --- |
| Deploy A, start | running in 1.56 s, `map_meta.txt` `seed = 111111` read back via `files/contents`. Readiness line `Server for gameid="minetest" listening on 0.0.0.0:25584.` |
| Swap to B | running in 1.52 s, `seed = 222222` |
| Start with the world missing | **new world created silently** (`seed = 11465726307056329104`) |
| Capture (backup) and render with `minetestmapper` | 684 809 bytes; 289 map blocks rendered from the open `colors.txt`: [`img/e10-luanti-capture-minetestmapper.png`](evidence/img/e10-luanti-capture-minetestmapper.png) |
| Upstream egg's `--terminal` mode | stdout becomes an ncurses UI, the readiness line never reaches Pelican, and the server stays `starting`. Without `--terminal`, console commands are not read, so stop must be `^C` (SIGINT). |
| Player join / positions | **not verified.** No headless Luanti client is available, and `players.sqlite` is created only on first join. DOCUMENTED. |

## E11: custody mechanics (bridge identity)

* `POST files/write /.ut-custody.json` → 204. It reads back identical and survives server runs. VERIFIED.
* A cheap fingerprint from `files/list` (size and `modified_at`): a played session changed **7** entries (including the player file). An **idle** start/stop also changed **6** (`level.dat` and region files). A metadata fingerprint can tell "the server ran since deploy" but **not** "there is real progress". VERIFIED *(rewrite behaviour is the stand-in's; vanilla also rewrites `level.dat` on every save)*.

## E12: worlds larger than the node upload limit

With Wings `api.upload_limit: 1` (MB):

* A single 4.3 MB archive → **400** `File whole.tar.gz is larger than the maximum file upload size of 1 MB.` The upload goes straight to Wings, so this error *is* informative.
* The same world as **7 part archives** split on file boundaries, each decompressed into one staging directory → **8/8 files byte-identical**, in 15.9 s.

VERIFIED. The Wings default limit is **100 MB**; UT allows world saves up to **2000 MB**. Splitting cannot help a world dominated by one file larger than the limit (for example Luanti's `map.sqlite`).

## Screenshots

| Image | Shows |
| --- | --- |
| [`01-player-dashboard-servers.png`](evidence/img/01-player-dashboard-servers.png) | Non-admin owner's server list |
| [`02-minecraft-console-running-player-joined.png`](evidence/img/02-minecraft-console-running-player-joined.png) | World A running (`seed 424242`), a client joined at its saved position, join address `127.0.0.1:25581` from the alias |
| [`03-minecraft-files-world-custody-marker.png`](evidence/img/03-minecraft-files-world-custody-marker.png) | `world`, accumulated `world.ut-prev-*` asides, `.ut-custody.json` |
| [`04-minecraft-backups-captures.png`](evidence/img/04-minecraft-backups-captures.png) | Captures taken as Pelican backups |
| [`05-minecraft-subuser-bridge-identity.png`](evidence/img/05-minecraft-subuser-bridge-identity.png) | The dedicated bridge account as a subuser |
| [`06-luanti-console-running.png`](evidence/img/06-luanti-console-running.png) | Second game running under Pelican |
| [`07-admin-servers-external-ids.png`](evidence/img/07-admin-servers-external-ids.png) | Both world hosts, eggs and aliased allocations |

## Reproduction run

The environment was rebuilt from scratch with [`setup_env.sh`](experiments/setup_env.sh), and every experiment above was rerun unattended, in run 1's order, with [`run_all.sh`](experiments/run_all.sh). This happened on 2026-10-04 from 20:18 to 20:34 UTC, against the same Panel and Wings versions. The output is in [`evidence/rerun/run_all.log`](evidence/rerun/run_all.log), every API call is in [`evidence/rerun/api-calls.jsonl`](evidence/rerun/api-calls.jsonl), and the recaptured UI screenshots are in [`evidence/rerun/img/`](evidence/rerun/img/).

**Every result reproduced.** Status codes, error texts, file listings, seeds, markers and verdicts are unchanged. Timings moved by less than a second, except E07's server runtime and empty-server time, which were each about 2 s shorter; its player sessions matched to 0.1 s.

| Experiment | Run 1 | Reproduction |
| --- | --- | --- |
| E01 | 201 in 1.18 s, installed in 3.17 s, duplicate `external_id` → 422 | 201 in 1.12 s, installed in 3.12 s, 422 |
| E02 | ready 3.86 s, stop 1.16 s, restart 4.39 s, kill 0.58 s; `/resources` stale | 3.69 s, 1.05 s, 4.18 s, 0.56 s; `/resources` reported `offline` while running |
| E03 | running in 4.07 s (A → B) and 3.64 s (B → A); seeds, levels, markers and saved positions verified | 3.51 s and 3.44 s; the same checks pass |
| E04 | capture in 1.68 s (434 403 bytes); restore while running races the shutdown save; truncate leaves `server.properties` and `world`, no runtime | 1.59 s (433 594 bytes); the same `NoSuchFileException: world/level.dat`; the same root; the server never reaches `running` |
| E04b | crash loop, then `settings/reinstall` restores the runtime in 4.25 s, world intact | the same console lines; 4.09 s; `Seed: [1337]` |
| E04c | 7/7 files byte-identical before first start; running in 3.34 s; diamond marker | 7/7; 3.33 s; diamond marker |
| E04d | only `world/` (7 entries) | the same |
| E05 | loopback → 500, `172.18.0.1` → 500, `192.0.2.2` → 204 in 1.73 s, intact | 500, 500, 204 in 1.67 s, intact; Wings logs `destination resolves to internal network location` |
| E06 | 11/11 allowed, 10/10 → 403, cross-tenant 404 ×3, key minting → 200; `allowed_ips` checked by hand | identical; the `allowed_ips` probes are now scripted: 403, then 200 |
| E07 | Alice 26.0 s, Bob 11.8 s, runtime 41.7 s, empty 15.7 s, 13 samples | 25.9 s, 11.8 s, 39.6 s, 13.7 s, 13 samples |
| E08a | every hostile input refused with an opaque 500, nothing escaped, the symlink left as a 0-byte file | the same, with the same four Wings errors |
| E08b | 401; connection error; new random world without `level.dat`; crash loop on a newer save; `starting` past 45 s; stale 200s while Wings is down; reattach | the same (the substituted seed was 7853411258948005392) |
| E08c | exit 137 detected, automatic restart, running at 3.3 s | exit 137, running at 3.5 s |
| E08d | container, volume and backup archive gone; both lookups 404 | the same |
| E09 | world B state and map | the same map, byte for byte (same sha256) |
| E09b | 682 explored chunks in the capture | 682 |
| E10 | A ready in 1.56 s (seed 111111), B in 1.52 s (222222), new world when missing, 684 809-byte capture, 289 blocks rendered | 1.57 s, 1.53 s, new world, 684 958 bytes, 289 blocks |
| E11 | marker round-trips; 7 entries changed after play, 6 after an idle start/stop | the same |
| E12 | single archive → 400 with the size message; 7 parts, 8/8 files identical in 15.9 s | 400; 8/8 identical in 15.5 s |

Rechecked by hand, because no script covers them:

* UT core `generate_world_thumbnail` returns `False` on the 26.1 layout and `True` on the same region files in the legacy `region/` layout.
* mcmap 3.0.4 reports `Canvas is empty!` on both layouts. The stand-in's chunks carry a lowercase `status: minecraft:full`, where vanilla writes `Status`.
* BlueMap still stops at Mojang's version manifest, seen again through the UT app's World Map card.
* E08a's decompression-bomb row: Wings logs nothing for it in either run. The `SpaceAvailableForDecompression` attribution comes from Wings' source; what was observed is a 500 with nothing extracted.
* The screenshots were recaptured with `screenshots.mjs`. The admin server list now also shows E06's other-tenant server, and a "Health 1" badge from Pelican's used-disk-space check, which reacts to this container's disk allowance.

The committed scripts did not run unattended on a fresh environment at first. The rerun needed these fixes:

* `setup_env.sh` pulled base images from Docker Hub, which rate-limited it (429), and hardcoded the sandbox proxy's port for Maven. It now uses `mirror.gcr.io` and `HTTPS_PROXY`.
* `ptlab.wait_for` crashed on connection errors while Wings restarted (E08b).
* E04 ended in a `TimeoutError` at the very hazard it demonstrates; it now records the hazard.
* E05 hardcoded run 1's host address.
* E06 depended on a hand-made other-tenant server and left its minted key behind. E10 depended on a hand-made Luanti server.
* E04d has to run after E06, because it uses the bridge subuser.
* The harness's redaction missed the `secret_token` of keys minted through the API (see [test-environment.md](test-environment.md#reproducing)).
