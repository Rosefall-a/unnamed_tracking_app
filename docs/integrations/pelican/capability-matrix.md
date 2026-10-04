# Capability matrix

Columns say **where** each capability comes from. Status words:

* **VERIFIED**: observed in this investigation
* **PARTIALLY VERIFIED**: observed with a caveat (usually the Minecraft stand-in)
* **DOCUMENTED**: read in source or docs, not run
* **REQUIRES PLUGIN**: needs a Pelican plugin
* **REQUIRES GAME ADAPTER**: needs adapter knowledge
* **UNKNOWN**
* **BLOCKED**

"Bridge" means the proposed UT host bridge (D1); "Plugin" means the UT Pelican Worlds plugin.

## Run

| Capability | UT (plugin / bridge) | Pelican API | Pelican plugin | Game adapter | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| List servers | bridge `servers.list` (filtered by assignment) | `GET /api/client` | — | — | **VERIFIED** | E06 |
| Server metadata, limits, egg variables | bridge | `GET /servers/{id}`, `/startup` | — | maps variables → game version | **VERIFIED** | E02, E06 |
| Server status (live) | bridge websocket cache | Wings ws `status` | — | — | **VERIFIED** | E02 |
| Server status (REST) | not used | `GET /resources` | — | — | **VERIFIED as stale** (~20 s; 200 while Wings is down) | E02, E08b |
| Node, allocation, join address | bridge `join_info` | `network/allocations` (`alias ?: ip`, port) | — | join instructions | **VERIFIED** (loopback allocations are not joinable) | E03 |
| Start / stop / restart / kill | bridge `servers.power` | `POST /power` | — | stop timeout | **VERIFIED** | E02 |
| Readiness | bridge (ws `running`) + plugin timeout | egg `startup.done` match | — | readiness string lives in the egg; ready timeout | **VERIFIED** (no Pelican timeout; Luanti `--terminal` breaks it) | E02, E08b, E10 |
| Crash detection | bridge | ws daemon lines + auto-restart | — | — | **VERIFIED** | E08b |
| Create server | later milestone (D2) | `POST /api/application/servers` + `external_id` | optional policy plugin | egg choice | **VERIFIED** (admin key) | E01 |
| Choose node / allocation / egg / resources / startup / env | later milestone | Application API create and `PATCH build/startup` | — | defaults per game | **VERIFIED** (create, build, startup patch) | E01, E03, E08b |
| Duplicate world → server | UT unique binding | `external_id` unique → 422 | — | — | **VERIFIED** | E01 |
| Deploy save (staged swap) | bridge `worlds.deploy` | upload URL, `decompress`, `rename`, `delete`, `write` | — | world root, required files | **VERIFIED** | E03, E08b, E10 |
| Deploy large save (> upload limit) | bridge part splitting | as above | — | single-file worlds need a higher limit | **VERIFIED** (multi-file) | E12 |
| Deploy via Wings pull | not used | `files/pull` | — | — | **BLOCKED** for LAN UT (works from public addresses) | E05 |
| Verify the deployed world | plugin `verify_running` | `files/contents`, console command | — | identity rule | **VERIFIED** (seed and level name; Luanti seed) | E03, E10 |
| Detect a silently regenerated world | plugin identity check | — | — | identity rule | **VERIFIED** (MC stand-in, Luanti) | E08b, E10 |
| Custody marker | bridge | `files/write`, `files/contents` | — | — | **VERIFIED** | E11 |
| Archive safety (traversal, links, bombs) | bridge validator | Wings safe paths + space check | — | — | **VERIFIED** (Pelican side) | E08a |
| Least-privilege identity | dedicated subuser key | subuser permissions, `allowed_ips` | — | — | **VERIFIED** (key minting caveat) | E06 |

## Track

| Capability | UT | Pelican API | Pelican plugin | Game adapter | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Player join / leave | bridge ws supervisor | console via ws | — | line patterns | **PARTIALLY VERIFIED** (stand-in lines; Luanti docs only) | E07 |
| Player names | sessions | console | `player-counter` names | pattern | **PARTIALLY VERIFIED** | E07 |
| Player UUIDs | sessions | — | ping sample (if exposed) | player file names / `usercache.json` | **REQUIRES GAME ADAPTER** (player file per UUID seen) | E09 |
| Online player list (poll) | bridge | `list` command | `player-counter` `/query/players` | `list` pattern | **DOCUMENTED** (plugin), **PARTIALLY VERIFIED** (`list`) | source, E07 |
| Player IP | — | login line | — | pattern | **PARTIALLY VERIFIED**: shows the Docker NAT gateway, not the client | E07 |
| Session duration / playtime | `play_sessions` (D5) | — | — | — | **VERIFIED** (±1.3 s) | E07 |
| Server uptime ≠ playtime | `runtime_events` | ws `status`, `stats.uptime` | — | — | **VERIFIED** (41.7 s vs 37.8 s vs 26.0 s) | E07 |
| Sessions closed on crash | bridge | ws offline + daemon block | — | — | **VERIFIED** (no leave lines on crash) | E08b |
| Multiple players | sessions | — | — | — | **VERIFIED** (2 concurrent) | E07 |
| Last seen | sessions | — | — | — | derivable | E07 |
| Meaningful world events (advancements, deaths) | — | console | — | patterns | **UNKNOWN** | — |

## Visualise

| Capability | UT | Pelican API | Pelican plugin | Game adapter | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Live player position | bridge sampling | console command | — | `data get entity` | **PARTIALLY VERIFIED** (stand-in reproduces vanilla output) | E07, E09b |
| Saved position, dimension, rotation | capture metadata | backup download | — | player file parser | **PARTIALLY VERIFIED** | E09 |
| Biome | — | — | — | chunk section biomes | **UNKNOWN** (present in the format, not extracted) | — |
| World time, weather, seed, spawn, version | capture metadata | backup download / `files/download` | — | `level.dat` parser | **VERIFIED** | E09 |
| Explored area / loaded chunks | capture metadata | — | — | region headers | **VERIFIED** (545 → 682) | E09b |
| Map screenshot (asset-free) | renderer | — | — | top-block renderer, `minetestmapper` | **VERIFIED** (MC, Luanti) | E09, E10 |
| World map (BlueMap, existing core) | core world map | — | — | — | **BLOCKED** here (Mojang assets denied); works in UT core today with egress | E09 |
| Live web map | — | extra allocation | — | BlueMap / squaremap on Paper | **UNKNOWN** (Paper blocked) | — |
| Map ↔ session ↔ snapshot association | `world_map_renders` + `play_sessions` | — | — | — | **VERIFIED** (association record) | E09b |
| UT core thumbnail on the 26.1 layout | core | — | — | — | **PARTIALLY VERIFIED** broken (layout from Minestom 26.1) | E09 |

## Preserve

| Capability | UT | Pelican API | Pelican plugin | Game adapter | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Hot capture | bridge `worlds.capture` | `POST backups` + ws `backup completed` | — | flush commands | **VERIFIED** | E04 |
| World-only capture | bridge | backup `ignored` with negation | — | world root | **VERIFIED** | E04d |
| Download capture → UT version | bridge stream | signed download | — | — | **VERIFIED** (download + checksum; UT write is implementation) | E04, E09b |
| Restore (safe sequence) | bridge | rename + `restore truncate:false` | — | — | **VERIFIED** (7/7 byte-identical) | E04c |
| Restore while running | refused by design | `restore truncate:true` | — | — | **VERIFIED as hazardous** | E04 |
| Pelican backups as the record | not used (D3) | — | — | — | **VERIFIED as unsuitable** (deleted with the server) | E08d |
| Multiple versions, retention | `game_archive_versions` + policy | backup limit per server | — | — | **DOCUMENTED** (UT model exists) | audit |
| Checksums | new `sha256` | ws event sha1 | — | — | **VERIFIED** (Pelican sha1); UT column is new | E04 |
| Branching | `parent_version_id` | — | — | — | design only | — |
| Migration to another server | deploy elsewhere after capture | — | — | — | design only (= capture + deploy, both verified) | E03, E04 |
| Environment reconstruction (egg, version, mods) | — | egg export, startup | — | mod detection | **UNKNOWN** | — |

## Detection

| Capability | UT | Pelican API | Pelican plugin | Game adapter | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Game version detection | runtime `game_version` | egg variables, first console line | — | `level.dat` `Version.Name` / `DataVersion` | **VERIFIED** (save: `26.1.2` / 4790; console: `Starting minecraft server version 26.1.2`) | E09, E02 |
| Version compatibility | plugin `compatible()` | — | — | data version rule | **PARTIALLY VERIFIED** (newer world → crash loop detected) | E08b |
| Mod / plugin detection | — | `files/list mods/`, `plugins/` | `minecraft-modrinth` (manages mods) | mod folder rules | **REQUIRES GAME ADAPTER**, untested | — |
