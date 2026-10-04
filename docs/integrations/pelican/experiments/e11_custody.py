"""E11: custody mechanics for "Continue Playing" (decision D4) with the least-privilege bridge identity.

usage: e11_custody.py <server.json>
1. Write a custody marker (.ut-custody.json) next to the world with files/write and read it back.
2. Fingerprint the hosted world cheaply from files/list (size + modified_at of the key files).
3. Play (start, protocol client joins and moves, stop) and fingerprint again: did the hosted world
   change since deploy, i.e. does the server now hold progress UT has not captured?
4. Start + stop with nobody joining: does an idle run also change the fingerprint?
"""
import json
import subprocess
import time

import sys

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
exp = "E11-custody"
c = Api("client", "client_bridge", exp)
info = c.get(f"servers/{server}").json()["attributes"]
alloc = [a["attributes"] for a in info["relationships"]["allocations"]["data"] if a["attributes"]["is_default"]][0]
con = Console(c, server)
con.pump(0.5)


def stop():
    if [e["args"][0] for e in con.events if e["event"] == "status"][-1:] != ["offline"]:
        c.post(f"servers/{server}/power", {"signal": "stop"})
        con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)


def start():
    con.events.clear()
    c.post(f"servers/{server}/power", {"signal": "start"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 90)


def fingerprint() -> dict:
    fp = {}
    for d in ("/world", "/world/players/data", "/world/dimensions/minecraft/overworld/region"):
        for f in c.get(f"servers/{server}/files/list", params={"directory": d}, quiet=True).json()["data"]:
            a = f["attributes"]
            if a["is_file"]:
                fp[f"{d}/{a['name']}"] = (a["size"], a["modified_at"])
    return fp


def diff(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


stop()
marker = {"world_id": "ut-world:demo-a", "archive_id": "00000000-0000-0000-0000-00000000000a",
          "version_id": "00000000-0000-0000-0000-0000000000a1", "sha256": "bff42363408b4486", "deployed_at": int(time.time())}
w = c.call("POST", f"servers/{server}/files/write", params={"file": "/.ut-custody.json"}, data=json.dumps(marker),
           headers={"Content-Type": "text/plain"})
back = c.get(f"servers/{server}/files/contents", params={"file": "/.ut-custody.json"}).json()
print("custody marker write:", w.status_code, "| read back equal:", back == marker)
fp0 = fingerprint()
print("fingerprint entries:", len(fp0))

start()
t0 = time.time()
subprocess.Popen(["node", "bot.js", alloc["ip_alias"] or alloc["ip"], str(alloc["port"]), "UTPlayer", "6000"],
                 cwd="/srv/pelican/standin/bot", stdout=subprocess.DEVNULL)
con.until(lambda m: m["event"] == "console output" and "UTPlayer joined the game" in m["args"][0], 60)
con.send("send command", "tp UTPlayer 120 100 -80")
con.until(lambda m: m["event"] == "console output" and "UTPlayer left the game" in m["args"][0], 60)
stop()
fp1 = fingerprint()
played = diff(fp0, fp1)
print(f"after a played session: {len(played)} changed entries, e.g. {played[:4]}")

start()
time.sleep(5)
stop()
fp2 = fingerprint()
idle = diff(fp1, fp2)
print(f"after an idle start/stop: {len(idle)} changed entries, e.g. {idle[:4]}")
marker_after = c.get(f"servers/{server}/files/contents", params={"file": "/.ut-custody.json"}).json()
print("marker survives runs:", marker_after == marker)
con.close()
record(exp, {"marker_write": w.status_code, "marker_roundtrip": back == marker, "played_changed": played,
             "idle_changed": idle, "marker_survives": marker_after == marker})
