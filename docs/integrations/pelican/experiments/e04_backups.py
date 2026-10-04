"""E04: Pelican backups as a save-capture / restore mechanism (Client API, owner key)."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time

import requests

from ptlab import Api, Console, record, wait_for

server = json.load(open(sys.argv[1]))["identifier"]
exp = "E04-backups"
c = Api("client", "client_player", exp)
con = Console(c, server)
con.pump(0.5)


def console(cmd, expect, timeout=15):
    con.send("send command", cmd)
    return con.until(lambda m: m["event"] == "console output" and expect in m["args"][0], timeout)["args"][0]


state = c.get(f"servers/{server}/resources").json()["attributes"]["current_state"]
if state != "running":
    c.post(f"servers/{server}/power", {"signal": "start"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 120)
print("server running; seed line:", console("seed", "Seed: ["))

# 1. Consistent hot capture: flush + freeze saving, back up, unfreeze.
print(console("save-off", "Automatic saving is now disabled"))
print(console("save-all", "Saved the game"))
t0 = time.monotonic()
b = c.post(f"servers/{server}/backups", {"name": "ut-capture-world-b", "ignored": "world.ut-prev-*\nserver.jar"}).json()["attributes"]
print("backup created:", {k: b[k] for k in ["uuid", "name", "ignored_files", "is_successful", "is_locked", "completed_at"]})
ws_backup = con.until(lambda m: m["event"].startswith("backup"), 120)
print("websocket backup event:", ws_backup["event"], ws_backup.get("args"))
done = c.get(f"servers/{server}/backups/{b['uuid']}").json()["attributes"]
print(f"backup finished after {time.monotonic() - t0:.2f}s:", {k: done[k] for k in ["is_successful", "checksum", "bytes", "completed_at"]})
print(console("save-on", "Automatic saving is now enabled"))

# 2. Download and inspect the archive.
url = c.get(f"servers/{server}/backups/{b['uuid']}/download").json()["attributes"]["url"]
blob = requests.get(url, timeout=120).content
record(exp, {"surface": "wings", "method": "GET", "path": "<signed backup download url>", "bytes": len(blob)})
names = tarfile.open(fileobj=io.BytesIO(blob)).getnames()
print("downloaded", len(blob), "bytes sha256", hashlib.sha256(blob).hexdigest()[:16], "entries:", sorted(n for n in names if n.count("/") < 2))
open("/srv/pelican/evidence/backup-world-b.tar.gz", "wb").write(blob)

# 3. Lock (protect from rotation/deletion) and list.
c.post(f"servers/{server}/backups/{b['uuid']}/lock")
print("backups:", [(x["attributes"]["name"], x["attributes"]["is_locked"], x["attributes"]["bytes"]) for x in c.get(f"servers/{server}/backups").json()["data"]])

# 4. Overwrite with world A, then restore while RUNNING to see what Pelican does.
subprocess.run([sys.executable, "e03_deploy_world.py", sys.argv[1], "/srv/pelican/worlds/a/ut-test-world-a.tar.gz",
                "minecraft:gold_block"], check=True, capture_output=True)
con.pump(1)
print("after deploying A:", console("seed", "Seed: ["))
t0 = time.monotonic()
r = c.post(f"servers/{server}/backups/{b['uuid']}/restore", {"truncate": True})
print("restore while running ->", r.status_code, r.text[:200])
events = []
try:
    con.until(lambda m: (events.append((m["event"], m.get("args"))) or False) or (m["event"] == "backup restore completed"), 120)
except TimeoutError:
    pass
print("events during restore:", [e for e in events if e[0] != "stats"][:12])
wait_for(lambda: c.get(f"servers/{server}", quiet=True).json()["attributes"]["status"] is None, 120, 1, "restore status")
print(f"restore finished after {time.monotonic() - t0:.2f}s; power state:",
      c.get(f"servers/{server}/resources").json()["attributes"]["current_state"])
listing = sorted(f["attributes"]["name"] for f in c.get(f"servers/{server}/files/list", params={"directory": "/"}).json()["data"])
print("root after truncate restore:", listing)
c.post(f"servers/{server}/power", {"signal": "start"})
try:
    con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 60)
    print("after restore:", console("seed", "Seed: ["))
except TimeoutError:
    # Expected when the backup ignored server.jar: truncate removed the runtime (E04b recovers it).
    print("server did not reach running after the truncate restore (runtime removed): hazard reproduced")
    record(exp, {"step": "start after truncate restore", "running": False, "root": listing})
con.close()
