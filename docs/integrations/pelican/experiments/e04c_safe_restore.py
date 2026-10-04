"""E04c: the restore sequence the orchestrator should use, verified byte-for-byte before first start.

usage: e04c_safe_restore.py <server.json> <backup_uuid> <backup.tar.gz> <expect_seed> <expect_block>
stop -> confirm offline -> rename current world aside -> restore (truncate=false) -> wait for the
"backup restore completed" websocket event -> compare every world file with the archive -> start ->
seed + protocol-client verification.
"""
import hashlib
import json
import subprocess
import sys
import tarfile
import time

import requests

from ptlab import Api, Console, record, wait_for

server = json.load(open(sys.argv[1]))["identifier"]
backup_uuid, archive, expect_seed, expect_block = sys.argv[2], tarfile.open(sys.argv[3]), sys.argv[4], sys.argv[5]
exp = "E04c-safe-restore"
c = Api("client", "client_player", exp)
con = Console(c, server)
con.pump(0.5)
steps = []


def step(name, t0, **extra):
    steps.append({"step": name, "s": round(time.monotonic() - t0, 2), **extra})
    print(f"  {name}: {steps[-1]}")


t = time.monotonic()
if [e["args"][0] for e in con.events if e["event"] == "status"][-1:] != ["offline"]:
    c.post(f"servers/{server}/power", {"signal": "stop"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
step("stop -> offline", t)

t = time.monotonic()
aside = f"world.ut-prev-{int(time.time())}"
r = c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/", "files": [{"from": "world", "to": aside}]})
step("rename world aside", t, status=r.status_code, to=aside)

t = time.monotonic()
r = c.post(f"servers/{server}/backups/{backup_uuid}/restore", {"truncate": False})
step("restore request", t, status=r.status_code)
done = con.until(lambda m: m["event"] in ("backup restore completed", "daemon error"), 120)
step("websocket restore event", t, event=done["event"])
wait_for(lambda: c.get(f"servers/{server}", quiet=True).json()["attributes"]["status"] is None, 60, 1, "restore status")
step("panel status cleared", t)

t = time.monotonic()
same, differ = [], []
for member in archive.getmembers():
    if not member.isfile() or not member.name.startswith("world/"):
        continue
    want = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    url = c.get(f"servers/{server}/files/download", params={"file": "/" + member.name}, quiet=True).json()["attributes"]["url"]
    (same if hashlib.sha256(requests.get(url, timeout=60).content).hexdigest() == want else differ).append(member.name)
step("byte comparison before first start", t, identical=len(same), differ=differ)

t = time.monotonic()
con.events.clear()
c.post(f"servers/{server}/power", {"signal": "start"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 120)
con.send("send command", "seed")
seed = con.until(lambda m: m["event"] == "console output" and "Seed: [" in m["args"][0], 10)["args"][0]
step("start -> running", t, seed=seed.split(": ", 1)[1], seed_ok=f"[{expect_seed}]" in seed)

info = c.get(f"servers/{server}").json()["attributes"]
alloc = [a["attributes"] for a in info["relationships"]["allocations"]["data"] if a["attributes"]["is_default"]][0]
out = subprocess.run(["node", "bot.js", alloc["ip_alias"] or alloc["ip"], str(alloc["port"]), "UTPlayer", "1000"],
                     cwd="/srv/pelican/standin/bot", capture_output=True, text=True, timeout=90).stdout.strip().splitlines()
seen = json.loads(out[0])
ok = (seen.get("pillarTop") or {}).get("name") == expect_block.split(":")[-1]
step("protocol client", t, pillar=seen.get("pillarTop"), position=seen.get("position"), verified=ok)
record(exp, {"summary": steps})
con.close()
print("RESULT:", "PASS" if ok and not differ and f"[{expect_seed}]" in seed else "FAIL")
