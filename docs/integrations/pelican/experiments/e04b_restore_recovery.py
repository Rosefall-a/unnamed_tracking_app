"""E04b: what a truncate-restore of a capture that ignored server.jar leaves behind, and how to recover.

usage: e04b_restore_recovery.py <server.json> <backup.tar.gz downloaded by E04>
1. Try to start: observe the failure the user would see.
2. Reinstall (Client API settings/reinstall) to restore the runtime without touching the world.
3. Start, wait for readiness, confirm the restored world identity (seed).
4. Stop, download every world file through the Client API and compare with the backup archive.
"""
import hashlib
import io
import json
import sys
import tarfile
import time

import requests

from ptlab import Api, Console, record, wait_for

server = json.load(open(sys.argv[1]))["identifier"]
backup = tarfile.open(sys.argv[2])
exp = "E04b-restore-recovery"
c = Api("client", "client_player", exp)
con = Console(c, server)
con.pump(0.5)

# 1. Start with server.jar missing.
c.post(f"servers/{server}/power", {"signal": "start"})
seen = con.pump(8)
lines = [e["args"][0] for e in seen if e["event"] in ("console output", "daemon message")]
statuses = [e["args"][0] for e in seen if e["event"] == "status"]
print("start without server.jar -> statuses", statuses, "| console tail:", lines[-3:])
record(exp, {"step": "start without runtime", "statuses": statuses, "console_tail": lines[-5:]})

# 2. Reinstall: re-runs the egg install script; the world directory is left in place.
t0 = time.monotonic()
r = c.post(f"servers/{server}/settings/reinstall")
print("reinstall ->", r.status_code)
wait_for(lambda: c.get(f"servers/{server}", quiet=True).json()["attributes"]["is_installing"] is False, 120, 1, "reinstall")
print(f"reinstall finished after {time.monotonic() - t0:.2f}s; root:",
      sorted(f["attributes"]["name"] for f in c.get(f"servers/{server}/files/list", params={"directory": "/"}).json()["data"]))

# 3. Start and confirm identity.
con.events.clear()
c.post(f"servers/{server}/power", {"signal": "start"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 120)
con.send("send command", "seed")
print("after recovery:", con.until(lambda m: m["event"] == "console output" and "Seed: [" in m["args"][0], 10)["args"][0])
c.post(f"servers/{server}/power", {"signal": "stop"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)

# 4. Byte comparison against the backup, file by file, via the Client API download URLs.
#    level.dat is rewritten by the recovery start/stop above, so it is compared separately.
same, differ = [], []
for member in backup.getmembers():
    if not member.isfile() or not member.name.startswith("world/"):
        continue
    want = hashlib.sha256(backup.extractfile(member).read()).hexdigest()
    url = c.get(f"servers/{server}/files/download", params={"file": "/" + member.name}, quiet=True).json()["attributes"]["url"]
    got = hashlib.sha256(requests.get(url, timeout=60).content).hexdigest()
    (same if got == want else differ).append(member.name)
print("identical:", len(same), "| differ:", differ)
record(exp, {"step": "compare with backup", "identical": same, "differ": differ})
con.close()
