"""E10: the same Run/Capture/Visualise sequence against a second game (Luanti / Minetest 5.6).

usage: e10_luanti.py <server.json> <work_dir>
1. Generate two identifiable worlds offline (fixed seeds, a world mod that emerges terrain and builds a marker).
2. Deploy A then B with the Minecraft sequence (upload -> staging decompress -> swap -> start),
   verifying identity from map_meta.txt / players.sqlite read back through the Client API.
3. Probe the console contract (readiness line, /status, stop) and the "missing world" case.
4. Capture through a Pelican backup, render the capture with minetestmapper (no game assets).
"""
import io
import json
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import requests

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
work = Path(sys.argv[2])
shutil.rmtree(work, ignore_errors=True)
work.mkdir(parents=True)
exp = "E10-luanti"
c = Api("client", "client_player", exp)
steps = []


def step(name, **kw):
    steps.append({"step": name, **kw})
    print(f"  {name}: {kw}")


MARKER_MOD = """
-- Discovery-only world mod: emerge an area around spawn and build an identifying marker pillar.
minetest.after(1, function()
  minetest.emerge_area({x=-96, y=-32, z=-96}, {x=96, y=64, z=96}, function(_, _, remaining)
    if remaining == 0 then
      for y = 0, 40 do minetest.set_node({x=0, y=y, z=0}, {name="%s"}) end
      minetest.log("action", "UT marker %s built")
    end
  end)
end)
"""


def make_world(label: str, seed: int, marker: str) -> Path:
    root = work / label
    (root / "worlds").mkdir(parents=True)
    mod = root / "worlds" / "world" / "worldmods" / "ut_marker"
    mod.mkdir(parents=True)
    (mod / "mod.conf").write_text("name = ut_marker\ndepends = default\n")
    (mod / "init.lua").write_text(MARKER_MOD % (marker, marker))
    (root / "minetest.conf").write_text(f"name = utadmin\nfixed_map_seed = {seed}\nserver_announce = false\n")
    subprocess.run(["chmod", "-R", "777", str(root)])
    name = f"ut-luanti-gen-{label}"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--name", name, "-v", f"{root}:/home/container", "--entrypoint",
                    "/usr/games/minetestserver", "utpelican/yolk-luanti:local", "--gameid", "minetest",
                    "--world", "/home/container/worlds/world", "--config", "/home/container/minetest.conf",
                    "--logfile", "/home/container/gen.log"],
                   check=True, capture_output=True)
    time.sleep(25)
    subprocess.run(["docker", "stop", "-t", "20", name], capture_output=True)
    subprocess.run(["docker", "rm", name], capture_output=True)
    world = root / "worlds" / "world"
    # players.sqlite is only created once a player joins; no headless Luanti client is available here,
    # so player state is documented rather than verified for this game.
    meta = dict(l.split(" = ", 1) for l in (world / "map_meta.txt").read_text().splitlines() if " = " in l)
    print(f"world {label}: seed={meta.get('seed')} files={sorted(p.name for p in world.iterdir())}")
    return world


def deploy(con, world: Path, label: str):
    st = [e["args"][0] for e in con.events if e["event"] == "status"][-1:]
    if st != ["offline"]:
        c.post(f"servers/{server}/power", {"signal": "stop"})
        con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(world, arcname="world")
    up = c.get(f"servers/{server}/files/upload").json()["attributes"]["url"]
    requests.post(up, params={"directory": "/worlds"}, files={"files": (f"{label}.tar.gz", buf.getvalue())}, timeout=120).raise_for_status()
    stage = f".ut-staging-{label}"
    c.post(f"servers/{server}/files/create-folder", {"root": "/worlds", "name": stage})
    c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/worlds", "files": [{"from": f"{label}.tar.gz", "to": f"{stage}/{label}.tar.gz"}]})
    c.post(f"servers/{server}/files/decompress", {"root": f"/worlds/{stage}", "file": f"{label}.tar.gz"}).raise_for_status()
    names = {f["attributes"]["name"] for f in c.get(f"servers/{server}/files/list", params={"directory": "/worlds"}).json()["data"]}
    if "world" in names:
        c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/worlds", "files": [{"from": "world", "to": f"world.ut-prev-{label}-{int(time.time())}"}]})
    c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/worlds", "files": [{"from": f"{stage}/world", "to": "world"}]})
    c.post(f"servers/{server}/files/delete", {"root": "/worlds", "files": [stage]})


def start(con) -> float:
    con.events.clear()
    t0 = time.monotonic()
    c.post(f"servers/{server}/power", {"signal": "start"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 90)
    return round(time.monotonic() - t0, 2)


def remote_seed() -> str:
    txt = c.get(f"servers/{server}/files/contents", params={"file": "/worlds/world/map_meta.txt"}).text
    return dict(l.split(" = ", 1) for l in txt.splitlines() if " = " in l).get("seed")


world_a = make_world("a", 111111, "default:goldblock")
world_b = make_world("b", 222222, "default:diamondblock")
con = Console(c, server)
con.pump(0.5)

deploy(con, world_a, "a")
ready = start(con)
done_line = next((e["args"][0] for e in con.events if e["event"] == "console output" and "Server for gameid" in e["args"][0]), None)
step("deploy A + start", ready_s=ready, readiness_line=done_line, seed_on_server=remote_seed())
con.send("send command", "/status")
status_lines = [e["args"][0][:200] for e in con.pump(3) if e["event"] == "console output"]
step("console /status", output=status_lines[-3:])

deploy(con, world_b, "b")
ready = start(con)
step("swap to B + start", ready_s=ready, seed_on_server=remote_seed())

# Missing world: Luanti silently creates a new one, like Minecraft without level.dat.
c.post(f"servers/{server}/power", {"signal": "stop"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/worlds", "files": [{"from": "world", "to": "world.ut-hidden"}]})
start(con)
step("start with world missing", seed_on_server=remote_seed())
c.post(f"servers/{server}/power", {"signal": "stop"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
c.post(f"servers/{server}/files/delete", {"root": "/worlds", "files": ["world"]})
c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/worlds", "files": [{"from": "world.ut-hidden", "to": "world"}]})

# Capture via backup and render.
b = c.post(f"servers/{server}/backups", {"name": "ut-luanti-capture", "ignored": "worlds/world.ut-*\nworlds/.ut-staging*"}).json()["attributes"]
meta = json.loads(con.until(lambda m: m["event"] == "backup completed", 120)["args"][0])
url = c.get(f"servers/{server}/backups/{b['uuid']}/download").json()["attributes"]["url"]
cap = work / "capture"
with tarfile.open(fileobj=io.BytesIO(requests.get(url, timeout=120).content)) as tf:
    tf.extractall(cap, filter="data")
cap_world = cap / "worlds" / "world"
row = (sqlite3.connect(cap_world / "players.sqlite").execute("SELECT name, posX/10, posY/10, posZ/10, yaw FROM player").fetchall()
       if (cap_world / "players.sqlite").exists() else "no players.sqlite (no player has joined)")
png = work / "luanti-capture-map.png"
r = subprocess.run(["/usr/games/minetestmapper", "--colors", "/usr/share/minetest/colors.txt", "-i", str(cap_world), "-o", str(png), "--draworigin",
                    "--drawscale", "--geometry", "-160:-160+320+320"], capture_output=True, text=True)
step("capture + render", bytes=meta["file_size"], sha1=meta["checksum"], files=sorted(p.name for p in cap_world.iterdir()),
     players=row, mapper_rc=r.returncode, mapper_err=r.stderr[-200:], image=png.name if png.exists() else None)
con.close()
record(exp, {"summary": steps})
