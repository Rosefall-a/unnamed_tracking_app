# Pelican × Unnamed Tracking: discovery record

> **This directory does not implement the Pelican integration.** It establishes the experimentally validated architecture and requirements for implementation.

> Unnamed Tracking remembers your games and worlds. Pelican runs them.

| | |
| --- | --- |
| Host repository | `Rosefall-a/unnamed_tracking_app` |
| Base branch / commit | `plugin-manager` @ `b52b0719a68083deca125a2c8a067670753ca8bd` |
| Discovery branch | `pelican-plugin-feature` |
| Plugins repository reference | `Rosefall-a/unnamed_tracking_app_plugins@main` (`9a88160`) |
| Pelican under test | Panel `v1.0.0-beta38` (`e84a4afd`), Wings `v1.0.0-beta29` |
| Games under test | Minecraft 26.1.2-protocol **stand-in** (Mojang/PaperMC blocked here), **Luanti 5.6.1** (real) |

## Documents

| # | Document | Contents |
| --- | --- | --- |
| 1 | [architecture.md](architecture.md) | Proposed complete integration, flows, failure handling, rejected alternatives |
| 2 | [capability-matrix.md](capability-matrix.md) | Evidence-based Run / Track / Visualise / Preserve matrix |
| 3 | [pelican-api-audit.md](pelican-api-audit.md) | Endpoints, permissions, throttles, websocket protocol, quirks |
| 4 | [pelican-plugin-audit.md](pelican-plugin-audit.md) | What a Pelican plugin can do; why none is needed for M1–M4 |
| 5 | [ut-plugin-audit.md](ut-plugin-audit.md) | Plugin lifecycle, sandbox, capability registry, existing data model |
| 6 | [game-adapters.md](game-adapters.md) | Minecraft vs Luanti (vs Terraria), minimum adapter abstraction |
| 7 | [data-model.md](data-model.md) | Games → worlds → snapshots → runtimes → sessions → maps |
| 8 | [security-model.md](security-model.md) | Trust boundaries, credentials, least privilege, archive safety |
| 9 | [roadmap.md](roadmap.md) | Milestones M0–M6, out of scope, proposed PRs |
| 10 | [experiment-report.md](experiment-report.md) | Exactly what was tested and observed (E01–E12), and a from-scratch reproduction run |
| 11 | [test-environment.md](test-environment.md) | How to rebuild the Pelican environment and rerun every experiment |
| 12 | [open-questions.md](open-questions.md) | Decisions taken, decisions open, experiments still pending |
| — | [`experiments/`](experiments/), [`evidence/`](evidence/) | Scripts, eggs, yolks, redacted API logs and screenshots from the original and reproduction runs, maps |

## Answers to the discovery questions

**Run**

| Question | Answer | Evidence |
| --- | --- | --- |
| Discover a Pelican server? | **Yes.** `GET /api/client` with a least-privilege subuser key lists exactly the servers that added it | E06 |
| Start / stop / restart? | **Yes** (3.9 s / 1.2 s / 4.4 s; kill 0.6 s) | E02 |
| Create one? | **Yes**, with an admin Application key and `external_id` (duplicate → 422). Deferred by D2. | E01 |
| Deploy a real save? | **Yes**, through the Client API only: part upload → staging decompress → rename swap; verified by seed, level name, saved position and in-game markers, A↔B; also Luanti | E03, E10, E12 |
| Know when it is ready? | **Yes, from the websocket only.** REST is stale. Pelican has no timeout, so UT must own one. | E02, E08b |
| Tell the user how to join? | **Yes**: `alias ?: ip` and port of the default allocation. `127.0.0.1` allocations aren't joinable. | E03 |

**Track**

| Question | Answer | Evidence |
| --- | --- | --- |
| Identify players? | **Partly.** Names from console lines (stand-in reproduces vanilla); UUIDs from player files; IPs hidden by Docker NAT | E07, E09 |
| Track sessions? | **Yes**, from websocket join/leave, within ±1.3 s; crashes close sessions | E07, E08b |
| Uptime vs playtime? | **Yes**: 41.7 s runtime, 37.8 s player time, 26.0 s occupied | E07 |
| Meaningful world state? | **Yes, from saves**: seed, day, weather, spawn, version, explored chunks, player positions | E09 |

**Visualise**

| Question | Answer | Evidence |
| --- | --- | --- |
| Player locations? | **Yes**: live via an adapter console command; saved positions from player files | E07, E09 |
| A map? | **Yes**: asset-free maps for Minecraft and Luanti. BlueMap (already in UT core) needs Mojang assets, blocked here | E09, E10 |
| A useful screenshot? | **Yes**: [snapshot map with session trail](evidence/img/e09b-snapshot-map-with-session-trail.png) | E09b |
| Maps ↔ sessions and snapshots? | **Yes**: association record (session → backup → sha256 → map) | E09b |
| What is game-specific? | World layout, identity, line formats, flush commands, player storage, renderer | [game-adapters.md](game-adapters.md) |

**Preserve**

| Question | Answer | Evidence |
| --- | --- | --- |
| Capture a save? | **Yes**: world-only hot backup + signed download, with checksum | E04, E04d |
| Restore it? | **Yes**: safe sequence, byte-identical. Restore-while-running and `truncate` are hazardous. | E04, E04b, E04c |
| Safely replace a running world? | **Only by stopping first.** Stage, swap, verify identity, and swap back on failure. | E04, E08b |
| Retain multiple versions? | **In UT, yes** (existing `game_archive_versions`). Not in Pelican: backups are count-limited and **deleted with the server**. | E08d |
| Reconstruct the environment? | **Unknown.** Egg, version and mods are not yet captured (M6) | — |

**Architecture**

| Question | Answer |
| --- | --- |
| What belongs in Unnamed Tracking? | The world, its snapshots, custody, sessions and maps (core); the **Pelican bridge** (core); orchestration and UI (plugin) |
| What belongs in Pelican? | Server lifecycle, files, backups, readiness and crash restart, unmodified |
| Is a Pelican companion plugin necessary? | **No** for M1–M4. `player-counter` is an optional presence source. |
| What belongs in game adapters? | Paths, identity, compatibility, console patterns, flush commands, player state, renderer |
| Required capabilities? | New: `pelican.servers.read/power`, `pelican.worlds.deploy/capture`, `pelican.events.subscribe`, `games.worlds.read/write`. Existing low-risk UI and task capabilities. **No `network.outbound`, `api.full` or `frontend.native`.** |
| Out of scope? | See [roadmap.md](roadmap.md#out-of-scope-for-the-first-implementation) |

## Recommendation: "I would build it this way"

1. **Architecture.** Keep the plugin sandbox intact. Add a **Pelican bridge to UT core** that owns the encrypted credential, an origin-bound Panel client, archive validation, byte streaming to and from Wings' signed URLs, and the websocket supervisor. The **Pelican Worlds plugin** orchestrates Continue Playing, Stop & Save and Restore over narrow `pelican.*` / `games.worlds.*` gateway methods. No companion plugin and no `api.full`.
2. **Data.** The world is the existing `world_save` archive and the snapshots are its versions (plus sha256 and provenance). Add hosted runtimes with custody state, runtime events, separate hosted play sessions, and per-version map renders. All host-owned, so they survive plugin uninstall and Pelican server deletion.
3. **Pelican side.** A dedicated `ut-bridge` account that server owners add as a subuser with 17 permissions; an IP-pinned key; a sibling-key audit; a node upload size that fits the part size.
4. **Game adapters.** A declarative descriptor per game plus a few sandboxed parsers on bounded bytes. Ship `minecraft-java` first, then `luanti` to prove the abstraction.
5. **First implementation milestone: M0** (core world foundations: provenance, safe tar/zip extraction, 26.1-aware thumbnail, version-keyed renders). It is independently useful and unblocks M1.
6. **Second: M1 Continue Playing** with custody and Stop & Save for Minecraft Java, gated on a vanilla/Paper confirmation run.
7. **Then:** M2 hosted play history → M3 maps of every snapshot → M4 snapshot management → M5 provisioning and Luanti → M6 deep preservation.
8. **Major risks:**
   * Stand-in vs vanilla differences (confirm once egress allows).
   * Pelican's opaque 500s.
   * The shared bridge account's blast radius.
   * Upload limits for single-file worlds.
   * Plugin worker CPU limit and restart behaviour.
   * BlueMap's Mojang dependency.
9. **Unresolved questions:**
   * Q1: server-to-user assignment.
   * Q2: bridge process model.
   * Q3: provider-neutral contract names.
   * Q6: privacy of other players' data.
   * See [open-questions.md](open-questions.md).
