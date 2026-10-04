"""E09b: a play session -> a captured snapshot -> a map of that snapshot with the session's trail.

usage: e09b_session_snapshot_map.py <server.json> <out_dir>
As the bridge identity: start, let a client play while the server moves it around, sample
positions over the websocket, flush + back up the world, download the archive, render it with
E09 and write the association record (session, snapshot checksum, map) that UT would store.
"""
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

import requests

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
exp = "E09b-session-snapshot-map"
c = Api("client", "client_bridge", exp)
info = c.get(f"servers/{server}").json()["attributes"]
alloc = [a["attributes"] for a in info["relationships"]["allocations"]["data"] if a["attributes"]["is_default"]][0]
con = Console(c, server)
con.pump(0.5)
if [e["args"][0] for e in con.events if e["event"] == "status"][-1:] != ["running"]:
    c.post(f"servers/{server}/power", {"signal": "start"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 120)

bot = threading.Thread(target=lambda: subprocess.run(
    ["node", "bot.js", alloc["ip_alias"] or alloc["ip"], str(alloc["port"]), "UTPlayer", "30000"],
    cwd="/srv/pelican/standin/bot", capture_output=True, timeout=120))
bot.start()
con.until(lambda m: m["event"] == "console output" and "UTPlayer joined the game" in m["args"][0], 60)
session_start = time.time()
route = [(10, 100, 10), (40, 100, 30), (70, 100, -20), (30, 100, -60), (-40, 100, -40), (-60, 100, 30), (-20, 100, 60)]
samples = []
pos_re = re.compile(r"UTPlayer has the following entity data: \[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]")
for x, y, z in route:
    con.send("send command", f"tp UTPlayer {x} {y} {z}")
    con.pump(1.5)
    con.send("send command", "data get entity UTPlayer Pos")
    m = con.until(lambda e: e["event"] == "console output" and pos_re.search(e["args"][0]), 10)
    p = pos_re.search(m["args"][0])
    samples.append({"t": round(m["_t"] - session_start, 1), "pos": [float(p.group(i)) for i in (1, 2, 3)]})
bot.join()
con.until(lambda m: m["event"] == "console output" and "UTPlayer left the game" in m["args"][0], 60)
session_end = time.time()

# Capture: flush, freeze saving, back up, unfreeze.
for cmd, expect in (("save-off", "Automatic saving is now disabled"), ("save-all", "Saved the game")):
    con.send("send command", cmd)
    con.until(lambda m: m["event"] == "console output" and expect in m["args"][0], 15)
b = c.post(f"servers/{server}/backups", {"name": f"ut-session-{int(session_start)}", "ignored": "world.ut-prev-*\n.ut-staging*\nserver.jar\nlogs"}).json()["attributes"]
done = con.until(lambda m: m["event"] == "backup completed", 120)
con.send("send command", "save-on")
con.close()
meta = json.loads(done["args"][0])
url = c.get(f"servers/{server}/backups/{b['uuid']}/download").json()["attributes"]["url"]
archive = out / f"snapshot-{b['uuid']}.tar.gz"
archive.write_bytes(requests.get(url, timeout=300).content)
sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
extract = out / f"snapshot-{b['uuid']}"
with tarfile.open(archive) as tf:
    tf.extractall(extract, filter="data")
(out / "samples.json").write_text(json.dumps(samples))
png = out / f"map-{b['uuid']}.png"
render = subprocess.run([sys.executable, "e09_visualise.py", str(extract / "world"), str(png), str(out / "samples.json")],
                        capture_output=True, text=True, check=True)
summary = json.loads(render.stdout)
association = {
    "session": {"player": "UTPlayer", "started_at": int(session_start), "ended_at": int(session_end),
                "seconds": round(session_end - session_start, 1), "position_samples": samples},
    "snapshot": {"pelican_backup_uuid": b["uuid"], "pelican_sha1": meta["checksum"], "bytes": meta["file_size"],
                 "sha256": sha256, "captured_after_session": True},
    "map": {"image": png.name, "explored_chunks": summary["explored_chunks"], "world": summary["world"],
            "saved_player_positions": summary["players"]},
}
(out / "association.json").write_text(json.dumps(association, indent=1))
record(exp, association)
print(json.dumps(association, indent=1)[:1500])
