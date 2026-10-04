"""E08b: runtime failure modes an orchestrator has to recognise and recover from.

usage: e08b_runtime_failures.py <server.json> <world_dir_of_known_good_world>
Cases: invalid / revoked credentials, Panel unreachable, a save without level.dat, a save from a
newer game version, a server that never becomes ready, a crash while running, and Wings down.
The bridge identity is used for everything except the startup override (admin, test-only).
"""
import io
import json
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import nbtlib
import requests

from ptlab import PANEL, Api, Console, record, wait_for

info = json.load(open(sys.argv[1]))
server, sid = info["identifier"], info["id"]
good_world = Path(sys.argv[2])
exp = "E08b-runtime-failures"
c = Api("client", "client_bridge", exp)
app = Api("application", "app_full", exp)
work = Path("/srv/pelican/evidence/e08b")
shutil.rmtree(work, ignore_errors=True)
work.mkdir(parents=True)


def note(case, **kw):
    print(f"\n== {case}\n   " + "\n   ".join(f"{k}: {v}" for k, v in kw.items()))
    record(exp, {"case": case, **kw})


# 1. Credentials -----------------------------------------------------------------------------
bad = requests.get(f"{PANEL}/api/client", headers={"Authorization": "Bearer pacc_notarealkey0000000000000000000000000000000", "Accept": "application/json"})
note("invalid client key", status=bad.status_code, body=bad.text[:160])
try:
    requests.get("http://127.0.0.1:8001/api/client", timeout=3)
except requests.ConnectionError as exc:
    note("panel unreachable", error=type(exc).__name__)


# Helpers ------------------------------------------------------------------------------------
def stop(con):
    if [e["args"][0] for e in con.events if e["event"] == "status"][-1:] != ["offline"]:
        c.post(f"servers/{server}/power", {"signal": "stop"})
        con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 90)


def deploy(con, world_dir: Path, label: str):
    """Stage + swap, as recommended: upload, extract in staging, rename old world aside, move in."""
    stop(con)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(world_dir, arcname="world")
    url = c.get(f"servers/{server}/files/upload").json()["attributes"]["url"]
    requests.post(url, params={"directory": "/"}, files={"files": (f"{label}.tar.gz", buf.getvalue())}, timeout=120).raise_for_status()
    stage = f".ut-staging-{label}"
    c.post(f"servers/{server}/files/create-folder", {"root": "/", "name": stage})
    c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/", "files": [{"from": f"{label}.tar.gz", "to": f"{stage}/{label}.tar.gz"}]})
    c.post(f"servers/{server}/files/decompress", {"root": f"/{stage}", "file": f"{label}.tar.gz"}).raise_for_status()
    names = {f["attributes"]["name"] for f in c.get(f"servers/{server}/files/list", params={"directory": "/"}).json()["data"]}
    if "world" in names:
        c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/", "files": [{"from": "world", "to": f"world.ut-prev-{label}"}]})
    c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/", "files": [{"from": f"{stage}/world", "to": "world"}]})
    c.post(f"servers/{server}/files/delete", {"root": "/", "files": [stage]})


def start_and_watch(con, seconds):
    con.events.clear()
    c.post(f"servers/{server}/power", {"signal": "start"})
    con.pump(seconds)
    statuses = [e["args"][0] for e in con.events if e["event"] == "status"]
    lines = [e["args"][0] for e in con.events if e["event"] in ("console output", "daemon message")]
    return statuses, lines


con = Console(c, server)
con.pump(0.5)

# 2. A save without level.dat ------------------------------------------------------------------
nolevel = work / "nolevel"
shutil.copytree(good_world, nolevel)
(nolevel / "level.dat").unlink()
deploy(con, nolevel, "nolevel")
statuses, lines = start_and_watch(con, 8)
con.send("send command", "seed")
seed = con.until(lambda m: m["event"] == "console output" and "Seed: [" in m["args"][0], 10)["args"][0]
note("save without level.dat", statuses=statuses, warn=[l for l in lines if "WARN" in l or "Level" in l][:3],
     seed_after_start=seed.split(": ", 1)[1], expected_seed="[424242]")

# 3. A save from a newer game version -------------------------------------------------------------
newer = work / "newer"
shutil.copytree(good_world, newer)
lvl = nbtlib.load(newer / "level.dat")
data = lvl["Data"] if "Data" in lvl else lvl[""]["Data"]
data["DataVersion"] = nbtlib.Int(int(data["DataVersion"]) + 1000)
lvl.save()
deploy(con, newer, "newer")
statuses, lines = start_and_watch(con, 12)
note("save from a newer version", statuses=statuses,
     console=[l for l in lines if "ERROR" in l or "Daemon" in l][:4])

# 4. Restore the known-good world, then crash it while running --------------------------------------
deploy(con, good_world, "good")
statuses, _ = start_and_watch(con, 6)
t0 = time.monotonic()
con.events.clear()
con.send("send command", "ut-crash")
con.pump(75)  # Wings' crash detection restarts a crashed server if the previous crash was >60 s ago.
timeline = [(round(e["_t"] - con.events[0]["_t"], 1), e["event"], e["args"][0][:110] if e.get("args") else None)
            for e in con.events if e["event"] in ("status", "daemon message") or "Done (" in str(e.get("args"))]
note("crash while running", timeline=timeline)

# 5. Never ready: startup prints nothing matching the egg's done string (admin override, test only) ----
stop(con)
startup = app.get(f"servers/{sid}").json()["attributes"]["container"]
orig_cmd = startup["startup_command"]
body = {"startup": "env UT_STANDIN_NEVER_READY=1 " + orig_cmd, "environment": startup["environment"], "egg": 1,
        "image": startup["image"], "skip_scripts": True}
r = app.call("PATCH", f"servers/{sid}/startup", json_body=body)
statuses, lines = start_and_watch(con, 45)
res = c.get(f"servers/{server}/resources").json()["attributes"]
note("never becomes ready", startup_patch=r.status_code, statuses_after_45s=statuses, rest_state=res["current_state"],
     console_tail=lines[-2:])
c.post(f"servers/{server}/power", {"signal": "kill"})
time.sleep(2)
body["startup"] = orig_cmd
app.call("PATCH", f"servers/{sid}/startup", json_body=body)

# 6. Wings down while the Panel is up --------------------------------------------------------------
statuses, _ = start_and_watch(con, 6)
con.close()
wings = int(subprocess.check_output(["pgrep", "-f", "wings --config"]).split()[0])
os_kill = __import__("os").kill
os_kill(wings, signal.SIGTERM)
time.sleep(3)
container_alive = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", info["uuid"]], capture_output=True, text=True).stdout.strip()
probes = {}
for label, call in {"GET server": lambda: c.get(f"servers/{server}"),
                    "GET resources": lambda: c.get(f"servers/{server}/resources"),
                    "GET websocket": lambda: c.get(f"servers/{server}/websocket"),
                    "POST power stop": lambda: c.post(f"servers/{server}/power", {"signal": "stop"}),
                    "GET files/list": lambda: c.get(f"servers/{server}/files/list", params={"directory": "/"})}.items():
    r = call()
    probes[label] = r.status_code
note("wings down", game_container_still_running=container_alive, client_api=probes)
subprocess.Popen(["./wings", "--config", "/etc/pelican/config.yml"], cwd="/srv/pelican/wings",
                 stdout=open("/srv/pelican/logs/wings.log", "a"), stderr=subprocess.STDOUT,
                 env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "NO_PROXY": "127.0.0.1,localhost,172.18.0.0/16"},
                 start_new_session=True)
waited = wait_for(lambda: requests.get("http://127.0.0.1:8080/api/system", timeout=2).status_code == 401, 60, 1, "wings")
con = Console(c, server)
first = con.pump(3)
note("wings back", seconds_to_api=waited, first_status=[e["args"][0] for e in first if e["event"] == "status"][:2],
     resources=c.get(f"servers/{server}/resources").json()["attributes"]["current_state"])
con.close()
