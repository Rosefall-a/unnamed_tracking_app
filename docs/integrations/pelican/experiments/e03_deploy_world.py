"""E03: deploy a saved world archive into a Pelican server using only the Client API.

usage: e03_deploy_world.py <server.json> <archive> <expect_block> [--no-stop]
Sequence: stop -> wait offline -> signed upload -> rename current world aside -> decompress ->
verify listing -> delete archive -> start -> wait running (websocket) -> console `seed` -> bot.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
archive = Path(sys.argv[2])
expect_block = sys.argv[3]
no_stop = "--no-stop" in sys.argv
exp = "E03-deploy-world"
c = Api("client", "client_player", exp)
steps = []


def step(name, t0, **extra):
    steps.append({"step": name, "s": round(time.monotonic() - t0, 2), **extra})
    print(f"  {name}: {steps[-1]}")


con = Console(c, server)
con.pump(0.5)
state = [e["args"][0] for e in con.events if e["event"] == "status"]
t = time.monotonic()
if not no_stop:
    c.post(f"servers/{server}/power", {"signal": "stop"})
    if not state or state[-1] != "offline":
        try:
            con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
        except TimeoutError:
            pass
    step("stop", t)

t = time.monotonic()
signed = c.get(f"servers/{server}/files/upload").json()["attributes"]["url"]
with archive.open("rb") as fh:
    r = requests.post(signed, params={"directory": "/"}, files={"files": (archive.name, fh)}, timeout=600)
record(exp, {"surface": "wings", "method": "POST", "path": "<signed upload url>", "status": r.status_code,
             "request": f"<multipart {archive.stat().st_size} bytes>", "response": r.text[:300]})
step("upload", t, status=r.status_code, bytes=archive.stat().st_size)
r.raise_for_status()

t = time.monotonic()
listing = {f["attributes"]["name"]: f["attributes"] for f in c.get(f"servers/{server}/files/list", params={"directory": "/"}).json()["data"]}
moved = None
if "world" in listing:
    moved = f"world.ut-prev-{int(time.time())}"
    r = c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/", "files": [{"from": "world", "to": moved}]})
    step("rename current world aside", t, status=r.status_code, to=moved)

t = time.monotonic()
r = c.post(f"servers/{server}/files/decompress", {"root": "/", "file": archive.name}, timeout=300)
step("decompress", t, status=r.status_code, body=r.text[:200])
r.raise_for_status()
world = [f["attributes"]["name"] for f in c.get(f"servers/{server}/files/list", params={"directory": "/world"}).json()["data"]]
step("verify listing /world", t, entries=world)
r = c.post(f"servers/{server}/files/delete", {"root": "/", "files": [archive.name]})
step("delete uploaded archive", t, status=r.status_code)

t = time.monotonic()
con.events.clear()
c.post(f"servers/{server}/power", {"signal": "start"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 120)
step("start -> status running", t)
con.send("send command", "seed")
seed_line = con.until(lambda m: m["event"] == "console output" and "Seed: [" in m["args"][0], 10)["args"][0]
level_line = next((e["args"][0] for e in con.events if e["event"] == "console output" and "Level \"" in e["args"][0]), None)
step("console seed via websocket", t, seed=seed_line.split(": ", 1)[1], level=level_line and level_line.split(": ", 1)[1])

info = c.get(f"servers/{server}").json()["attributes"]
alloc = [a["attributes"] for a in info["relationships"]["allocations"]["data"] if a["attributes"]["is_default"]][0]
bot = subprocess.Popen(["node", "bot.js", alloc["ip_alias"] or alloc["ip"], str(alloc["port"]), "UTPlayer", "1000", "rescan"],
                       cwd="/srv/pelican/standin/bot", stdout=subprocess.PIPE, text=True)
con.until(lambda m: m["event"] == "console output" and "UTPlayer joined the game" in m["args"][0], 60)
time.sleep(3)
con.send("send command", "tp UTPlayer 8 110 8")
out = bot.communicate(timeout=90)[0].strip().splitlines()
spawn, rescan = json.loads(out[0]), json.loads(out[-1])
ok = bool(rescan.get("pillarTop")) and rescan["pillarTop"]["name"] == expect_block.split(":")[-1]
step("bot verification", t, join=f"{alloc['ip_alias'] or alloc['ip']}:{alloc['port']}", spawn_position=spawn.get("position"),
     pillar=rescan.get("pillarTop"), pad=rescan.get("padTop"), verified=ok)
joins = [e["args"][0].split(": ", 1)[1] for e in con.pump(2) + con.events if e["event"] == "console output"
         and ("joined the game" in e["args"][0] or "left the game" in e["args"][0] or "logged in" in e["args"][0])]
step("player events from console", t, lines=sorted(set(joins)))
record(exp, {"summary": steps, "archive": archive.name, "moved_previous_world_to": moved})
con.close()
print("RESULT:", "PASS" if ok else "FAIL")
