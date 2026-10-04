# Experiment scaffolding

Disposable tooling used to validate Pelican behaviour for the discovery record. None of this is
production code, and none of it is part of the Unnamed Tracking integration.

| Path | Purpose |
| --- | --- |
| `standin-server/` | Minecraft Java 26.1.2-protocol stand-in on Minestom. It mimics the vanilla console/log contract, `server.properties`, and an Anvil world with `level.dat` and player data. It is used while Mojang/PaperMC downloads are blocked in the test environment. |
| `egg/egg-ut-standin-minecraft.yaml` | Pelican egg for the stand-in. Same config contract as the upstream Vanilla egg. |
| `ptlab.py` | Pelican Application/Client API and websocket harness. Logs every call (redacted) to an evidence JSONL. |
| `bot.js` | mineflayer headless client. Reports position, markers and online players. |
| `make_test_world.py` | Builds identifiable test worlds (seed, level name, marker blocks, saved player position). |
| `e01_create_server.py` | Server creation via the Application API with `external_id`. |
| `e02_lifecycle.py` | Power lifecycle and readiness via the Client API and websocket. |
| `e03_deploy_world.py` | World deployment through the Client API: stop, upload, rename aside, decompress, start, verify. |
| `e04_backups.py` | Backups as capture/restore, including restore-while-running behaviour. |
| `e04b_restore_recovery.py` | What a truncate-restore of a capture that ignored `server.jar` leaves, and recovery by reinstall. |
| `e04c_safe_restore.py` | The recommended restore sequence, verified byte-for-byte before first start. |
| `e05_files_pull.py` | Whether Wings can fetch a world itself (`files/pull`) from loopback, RFC1918 and public addresses. |
| `e06_least_privilege.py` | A dedicated subuser identity with only the Run/Capture/Restore permissions; allowed and denied probes. |
| `e07_tracking.py` | Player sessions, positions and server uptime derived from the websocket alone. |
| `e08a_archive_safety.py` | Traversal, symlink, truncated, non-archive and decompression-bomb archives; interrupted upload. |
| `e08b_runtime_failures.py` | Bad credentials, Panel/Wings down, save without `level.dat`, newer-version save, never-ready, crash. |
| `e08d_server_deletion.py` | What survives when the server hosting a world is deleted. |
| `e09_visualise.py` | World state, saved players, explored chunks and an asset-free top-down map from a Minecraft save. |
| `e09b_session_snapshot_map.py` | A play session, its captured snapshot, and a map of that snapshot with the session trail. |
| `e10_luanti.py` | The same deploy/verify/capture/map sequence against Luanti (Minetest 5.6), the second game. |
| `egg/egg-ut-luanti.yaml`, `yolks/luanti/` | Luanti egg (upstream contract minus `--terminal`) and local image. |
| `e11_custody.py` | Custody marker write/read and whether the hosted world changed since deploy. |
| `screenshots.mjs` | Playwright capture of the Pelican UI evidence in `../evidence/img/`. |
| `setup_env.sh` | Rebuilds the whole disposable Panel + Wings environment from release artifacts. |
| `mkkey.php` | Creates API keys through Pelican's own `KeyCreationService`. |
| `yolks/` | Local rebuilds of the Pelican Java 25 yolk and installer images. |
| `../evidence/api-calls.jsonl` | Every API call the experiments made, with credentials and signed URLs redacted. |

Building the stand-in needs JDK 25, because Minestom 26.x targets class version 69:

```bash
docker run --rm -v "$PWD/standin-server":/src -w /src maven:3-eclipse-temurin-25 mvn -q -B package
```
