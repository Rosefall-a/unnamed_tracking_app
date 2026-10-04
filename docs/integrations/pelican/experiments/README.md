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

Building the stand-in needs JDK 25, because Minestom 26.x targets class version 69:

```bash
docker run --rm -v "$PWD/standin-server":/src -w /src maven:3-eclipse-temurin-25 mvn -q -B package
```
