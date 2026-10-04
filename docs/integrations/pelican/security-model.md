# Security model

Goal: Pelican support must not weaken the plugin sandbox, and every credential and capability is the least that works. ✅ marks a control verified in the experiments.

## Trust boundaries

| Boundary | Who is trusted | Control |
| --- | --- | --- |
| Browser → UT backend | Authenticated UT user | Existing session auth; plugin UI is declarative or sandboxed; actions are re-authorised server-side |
| UT backend gateway → plugin (sandbox) | Plugin is **untrusted code** | Bubblewrap with no network and no app-data mounts; grants checked per call; 64 KiB transport |
| UT backend (bridge) → Pelican Panel | Panel is a **semi-trusted remote** | Fixed origin per connection; TLS; least-privilege key; response size bounds; no redirects |
| Bridge → Wings (signed URLs, websocket) | Wings hosts the Panel names | Only URLs returned by the Panel for the bound server; bounded transfers; JWT refresh |
| Wings → game container | Game server is **untrusted** (it runs user content) | Its output (console, files) is parsed as untrusted input by the bridge and adapter |
| UT user ↔ another UT user | Mutually untrusted | Server assignments; world ownership; every bridge method scoped to the caller |

## Credentials

| Credential | Where | Scope | Notes |
| --- | --- | --- | --- |
| Pelican client key of a **dedicated** `ut-bridge` account | UT core, **Fernet-encrypted** like `AppIntegrationSettings`; never in plugin storage, never echoed (only the `pacc_…` identifier is shown) | Only servers whose owners added `ut-bridge` as a subuser with the **17 permissions** ✅ (E06) | Set `allowed_ips` to UT's egress ✅. Audit sibling keys on every health check, because client keys can mint keys ✅ (E06). Rotate by creating a new key and deleting the old one. |
| Pelican Application key | **Not stored** in milestones 1–4 (D2) | — | If server creation is added: admin-only, `server: rw`, `node/allocation/egg/user: r`, IP-pinned. Pelican cannot scope it by node or egg, so it is effectively admin. |
| Wings JWTs and signed URLs | Bridge memory only | 10–15 min, one server ✅ | Redacted from logs and evidence ✅ |
| SFTP | Not used | — | Password-equivalent, whole-tree |

**Why not each UT user's own Pelican key:** an account key carries the user's full power (no scopes ✅) and can mint more keys ✅. A dedicated subuser identity bounded per server by its owner is strictly narrower.

**Logging Panel responses:** creating a key returns its secret once, in `meta.secret_token` ✅. The discovery harness first redacted only a fixed list of field names and wrote one such secret to its evidence log (see [test-environment.md](test-environment.md#reproducing)). Any bridge request logging must therefore redact by field-name pattern (`*token*`, `*secret*`, `*password*`), not by a fixed list.

## UT capabilities (least privilege)

The plugin requests: `pelican.servers.read`, `pelican.servers.power`, `pelican.worlds.deploy`, `pelican.worlds.capture`, `pelican.events.subscribe`, `games.read`, `games.worlds.read`, `games.worlds.write`, `tasks.background`, `plugin.storage`, `plugin.settings`, `notifications.send`, `frontend.navigation.main`, `frontend.settings`, `frontend.routes`, `frontend.page.extend`, `frontend.context.game`.

It does **not** request `network.outbound` (all Pelican traffic goes through the origin-bound bridge), `frontend.native`, `backend.routes.host`, `api.full`, `games.write` (hosted playtime is separate, D5), or any `sessions.*` (those are login sessions).

## Operation-level controls

| Risk | Control |
| --- | --- |
| **Arbitrary filesystem access** on the game server | The bridge accepts only (a) the adapter's world root and (b) the `.ut-staging/`, `.ut-prev/` and `/.ut-custody.json` names. No caller-supplied paths. Pelican confines the Client API to the server volume, and the openat2-based safe paths held in E08a ✅. |
| **Arbitrary filesystem access** in UT | No archive bytes or paths cross into the sandbox. The bridge writes only new archive versions under the world's own directory. |
| **Path traversal / absolute paths** in archives | Rejected by the bridge validator before upload. Wings also rejects them ✅ (E08a). |
| **Symlinks and hardlinks** | Rejected by the validator. Wings turns them into regular files and then aborts **mid-extraction** ✅, which staging contains. |
| **Malformed or truncated archives** | Validator dry-run. Wings rejects them ✅ with an opaque 500, so UT must produce the explanation itself. |
| **Decompression bombs / oversized saves** | Validator sums uncompressed sizes against the server's `limits.disk` minus usage, the UT `MAX_WORLD_SAVE_SIZE_MB`, and the per-entry ratio. Wings' own pre-check refused 6 GiB ✅. |
| **Malicious content inside a valid world** (e.g. crafted NBT, Lua `worldmods/`) | Parsers handle untrusted bytes with size caps. **Luanti `worldmods/` is code the game server executes** (E10 used one), so deploying a world can run Lua on the server. That's acceptable inside the game container, but UT must label it and must never execute world content itself. |
| **Destructive operations** | Never delete a world in place: swap into `.ut-prev/` with retention. Never `truncate` a restore. Never restore while running ✅ (E04). `kill` only with explicit user consent after the stop timeout. |
| **Save deletion** | UT archives are the record (D3). The bridge never deletes UT versions; retention is an explicit, logged policy. |
| **Server deletion** | Not available to the bridge (no Application key). If it happens out-of-band, the runtime becomes `detached` and nothing in UT is lost ✅ (E08d). |
| **Cross-user access** | Bridge methods resolve server → assignment → UT user. Pelican's 404 for foreign servers ✅ is defence in depth, not the control, because the shared bridge account can see every server it was added to. |
| **Console injection** | Only adapter-declared command templates, with arguments restricted to known player names; never free text from users. |
| **Untrusted console output** | Regex parsing with length caps. Player names are validated against the adapter's charset before storage or display. |
| **SSRF via the bridge** | The connection origin is fixed by an admin. Wings URLs are accepted only as returned by that Panel for that server. No redirects. |
| **Denial of service** | Respect Pelican's throttles (websocket credentials 5/min, restore 3/15 min, pull 5/10 min, 256/min overall). One deploy or capture job per world and per server. Bounded concurrency per connection. Upload parts sized under `upload_size`. Readiness and stop timeouts. Position sampling off by default. |

## Pre-existing risks noticed in UT core (outside this PR's scope)

1. **World-map extraction has no size bound.** `features/world_map/bluemap.py` calls `zipfile.ZipFile(...).extractall()` on uploaded world saves. Python sanitises `..` and absolute names and doesn't create symlinks, but there's no limit on the total uncompressed size or entry count, so a zip bomb uploaded as a world save can fill the data volume when a render is requested.
2. **`network.request` has no destination policy.** `plugin_api/outbound.py` executes in the **backend** and allows any `http(s)` host, including loopback, RFC1918 and link-local addresses. A plugin granted `network.outbound` can reach internal JSON services on the backend's networks. Wings applies exactly this block to its own pulls (E05).

Both are worth separate issues. The Pelican design avoids both: it uses an origin-bound bridge, and capture-to-render goes through a validated tar extraction.

## Residual risks

* The bridge account is shared across UT users. Its compromise exposes every server that added it, limited to the 17 permissions. Mitigations: `allowed_ips`, key audit, and per-server opt-in by owners.
* Pelican's opaque 500s hide Wings' errors, so some failures can only be reported generically when they happen server-side (Wings down, disk full during extraction).
* The stand-in reproduces vanilla's file and console contracts; vanilla- and Paper-specific behaviour (log formats, the 26.1 layout) still needs a confirmation run when Mojang and PaperMC hosts are allowed.
