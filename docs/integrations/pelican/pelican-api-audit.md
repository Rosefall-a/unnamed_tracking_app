# Pelican API audit

Panel `v1.0.0-beta38` (`e84a4afd`), Wings `v1.0.0-beta29`. Sources: the route tables (`php artisan route:list`), request classes, `app/Enums/SubuserPermission.php`, `app/Enums/ResourceLimit.php`, `config/http.php`, and the Wings router and filesystem packages. Endpoints marked ✅ were exercised in the experiments ([report](experiment-report.md)).

## Surfaces and credentials

| Surface | Credential | Scope model | Notes |
| --- | --- | --- | --- |
| Client API `/api/client` | Account key `pacc_…` (identifier + 32-char token) | **No scopes on the key.** It carries the user's power: everything the user owns, plus subuser permissions on servers they were added to. | `allowed_ips` enforced ✅. A key can **mint and delete sibling keys** for its own account ✅. |
| Application API `/api/application` | Application key `papp_…` | Per-resource ACL: `server, node, allocation, user, egg, database_host, database, mount, role, plugin`, each none/read/write/read+write | Admin-created. Not scoped by node, egg or user. Plugins can register custom resources (`ApiKey::registerCustomResourceName`). |
| Wings HTTP | Short-lived JWTs minted by the Panel | Signed URL per operation | Upload URL 15 min ✅, download URL 15 min ✅, websocket JWT **10 min** (`token expiring` sent 3 min before expiry) |
| Wings websocket | JWT from `GET /servers/{id}/websocket` | `websocket.connect` + per-event permissions | Real-time status, console, stats, backup events ✅ |
| Wings SFTP `:2022` | Panel username + password or SSH key | `file.sftp` | Not used: it gives the bridge a password-equivalent credential and full-tree access |

Rate limits (`config/http.php`): Client API 256/min per user, Application API 256/min. Per-server `ResourceLimit` throttles (applied per server, not per user): websocket credentials 5/min, **backup restore 3/15 min**, **file pull 5/10 min** ✅ (hit in E05), subuser create 10/15 min, database create 2/min, allocation and schedule create 2/min.

## Endpoints the integration needs

| Purpose | Method + path (Client API unless noted) | Subuser permission | Verified |
| --- | --- | --- | --- |
| List servers visible to the key | `GET /api/client` | — | ✅ |
| Server details, limits, SFTP details, allocations | `GET /servers/{id}` | — (membership) | ✅ |
| Join address | `GET /servers/{id}/network/allocations`; use `ip_alias ?: ip` + `port` of `is_default` | `allocation.read` | ✅ |
| Egg variables (game version, world name) | `GET /servers/{id}/startup` | `startup.read` | ✅ |
| Power | `POST /servers/{id}/power {signal: start|stop|restart|kill}` | `control.start/stop/restart` | ✅ |
| Console command | `POST /servers/{id}/command` | `control.console` | ✅ |
| Live status, console, stats, backup events | `GET /servers/{id}/websocket` → Wings ws `auth` | `websocket.connect` | ✅ |
| Cached state (≈20 s stale) | `GET /servers/{id}/resources` | — | ✅ (stale) |
| List directory (`size`, `modified_at`) | `GET /servers/{id}/files/list?directory=` | `file.read` | ✅ |
| Read small text file | `GET /servers/{id}/files/contents?file=` (raw body) | `file.read-content` | ✅ |
| Download a file | `GET /servers/{id}/files/download?file=` → signed URL | `file.read-content` | ✅ |
| Upload | `GET /servers/{id}/files/upload` → signed URL → multipart `POST` to Wings (`directory` query) | `file.create` | ✅ |
| Create folder | `POST /servers/{id}/files/create-folder` | `file.create` | ✅ |
| Decompress (zip, tar, gz, …) | `POST /servers/{id}/files/decompress {root, file}` | `file.create` | ✅ |
| Rename / move | `PUT /servers/{id}/files/rename {root, files:[{from,to}]}` (works across directories) | `file.update` | ✅ |
| Delete | `POST /servers/{id}/files/delete {root, files}` | `file.delete` | ✅ |
| Write small file | `POST /servers/{id}/files/write?file=` (raw body) | `file.create` | ✅ |
| Remote pull | `POST /servers/{id}/files/pull {url, directory, filename, foreground}` | `file.create` | ✅ (blocked for LAN) |
| Backups | `GET/POST /servers/{id}/backups`, `GET …/{b}`, `GET …/{b}/download`, `POST …/{b}/lock`, `POST …/{b}/restore {truncate}`, `DELETE …/{b}` | `backup.read/create/download/restore/delete` | ✅ (except delete) |
| Reinstall runtime | `POST /servers/{id}/settings/reinstall` | `settings.reinstall` | ✅ |
| *(Later milestone)* create server | `POST /api/application/servers` (with `external_id`) | App key `server: rw` | ✅ |
| *(Later)* find by world | `GET /api/application/servers/external/{external_id}` | App key `server: r` | ✅ |
| *(Later)* change allocation and limits | `PATCH /api/application/servers/{id}/build` | App key `server: rw` | ✅ |
| *(Later)* add allocations | `POST /api/application/nodes/{n}/allocations {ip, alias, ports}` | App key `allocation: rw` | ✅ |
| *(Later)* delete server | `DELETE /api/application/servers/{id}` | App key `server: rw` | ✅ |
| Import egg | `POST /api/application/eggs/import` (raw YAML/JSON) | App key `egg: rw` | ✅ |

Pelican ships an OpenAPI description at `/docs/api/client.json` and `/docs/api/application.json` (Scramble).

## Websocket protocol (Wings)

* Client → server: `auth [jwt]`, `send command [cmd]`, `set state [signal]`, `send logs`, `send stats`.
* Server → client events (`server/events.go` and `router/websocket/message.go`): `auth success`, `status`, `console output`, `stats` (JSON including `uptime` in ms, memory, CPU, network, disk), `daemon message`, `install started/output/completed`, `backup completed` (JSON with checksum, size, uuid, `is_successful`), `backup restore completed`, `transfer logs/status`, `deleted`, `feature match`, `token expiring`, `token expired`, `jwt error`, `daemon error`.
* Crash detection arrives as `console output` lines prefixed `[pelican Daemon]:` (`Detected server process in a crashed state!`, `Exit code: N`, `Out of memory: bool`, `Aborting automatic restart, last crash occurred less than 60 seconds ago.`) ✅.
* Readiness = the egg's `config.startup.done` string matched on console output → `status: running` ✅. Pelican has no readiness timeout ✅.
* The JWT lasts 10 minutes. The consumer must refetch credentials (5/min/server throttle) and re-`auth` when it sees `token expiring`.

## Webhooks

Pelican can POST model and activity events to URLs (`WebhookConfiguration`, global scope for admins, server scope in the server UI). Server events include `server:power.*` *requests*, `server:file.*`, `server:backup.*` including `restore-complete/failed`, `server:subuser.*`, and `server:console.command`. **There are no readiness, crash, or player events**, and server-scoped webhooks cannot be created through the Client API. They are useful later for noticing out-of-band changes (someone else restored a backup or edited files). They are not a replacement for the websocket.

## Quirks and hazards (all observed)

1. **Stale REST state.** `/resources` lags by about 20 s and keeps returning 200 while Wings is down (E02, E08b).
2. **Opaque errors.** Every Wings failure relayed by the Panel (decompress, pull, power or files while Wings is down) becomes `500 RequestException` with a generic message (E05, E08a, E08b). Direct Wings calls such as the signed upload return the real message (E12).
3. **Loopback allocations** are re-bound to the `pelican0` gateway (E03). The Application API allocation field is `alias`, not `ip_alias`. `PATCH …/build` returns 404 when the new default allocation isn't also in `add_allocations`.
4. **Restore while running is racy** with `truncate` (E04). Always stop and confirm offline first.
5. **`truncate` + `ignored`** removes runtime files the backup skipped (E04b). Recover with `settings/reinstall`.
6. **Server deletion removes its backups** (E08d).
7. **`files/pull` refuses private and loopback addresses** (E05), with no configuration switch.
8. **Upload limit** defaults to 100 MB per file (`api.upload_limit`, mirrored by the node's `upload_size`) (E12).
9. **Symlink entries** become empty regular files, and a later entry through them aborts extraction **after** earlier entries were written (E08a). Extraction is not atomic.
10. **Missing world** → the game silently creates a new one (E08b Minecraft, E10 Luanti). Pelican cannot detect this.
