"""E07: Track — derive player sessions and server uptime from the Pelican websocket only.

usage: e07_tracking.py <server.json>
Uses the least-privilege bridge identity (client_bridge). Two protocol clients join and leave at
different times while a third observer polls positions through the console. Afterwards the
script derives, from websocket events alone:
  * server runtime sessions (status running -> offline) and the stats.uptime counter;
  * per-player sessions (joined/left lines) and their durations;
  * sampled positions from `data get entity <player> Pos`.
Ground truth is the bot schedule, so the derived numbers can be checked.
"""
import json
import re
import subprocess
import sys
import threading
import time

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
exp = "E07-tracking"
c = Api("client", "client_bridge", exp)
info = c.get(f"servers/{server}").json()["attributes"]
alloc = [a["attributes"] for a in info["relationships"]["allocations"]["data"] if a["attributes"]["is_default"]][0]
host, port = alloc["ip_alias"] or alloc["ip"], str(alloc["port"])

con = Console(c, server)
con.pump(0.5)
if [e["args"][0] for e in con.events if e["event"] == "status"][-1:] == ["running"]:
    c.post(f"servers/{server}/power", {"signal": "stop"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
con.events.clear()
t_power = time.time()
c.post(f"servers/{server}/power", {"signal": "start"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 120)

schedule = {"Alice": (2, 24), "Bob": (8, 10)}  # name -> (join offset s, stay s)
truth = {}


def run_bot(name, delay, stay):
    time.sleep(delay)
    truth[name] = {"start": time.time()}
    subprocess.run(["node", "bot.js", host, port, name, str(stay * 1000)], cwd="/srv/pelican/standin/bot",
                   capture_output=True, timeout=120)
    truth[name]["end"] = time.time()


threads = [threading.Thread(target=run_bot, args=(n, d, s)) for n, (d, s) in schedule.items()]
for t in threads:
    t.start()
deadline = time.time() + 34
while time.time() < deadline:
    for name in ("Alice", "Bob"):
        con.send("send command", f"data get entity {name} Pos")
    con.pump(3)
for t in threads:
    t.join()
time.sleep(2)
con.send("send command", "list")
con.pump(2)
c.post(f"servers/{server}/power", {"signal": "stop"})
con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
t_off = time.time()
con.close()

# ---- derive everything from the websocket stream ----
ev = con.events
statuses = [(e["_t"], e["args"][0]) for e in ev if e["event"] == "status"]
uptimes = [json.loads(e["args"][0]).get("uptime") for e in ev if e["event"] == "stats"]
run_start = next(t for t, s in statuses if s == "running")
run_end = next(t for t, s in statuses if s == "offline" and t > run_start)
join_re = re.compile(r": (\w+) joined the game")
left_re = re.compile(r": (\w+) left the game")
login_re = re.compile(r": (\w+)\[/([\d.]+):\d+\] logged in with entity id \d+ at \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)")
pos_re = re.compile(r": (\w+) has the following entity data: \[([-\d.]+)d, ([-\d.]+)d, ([-\d.]+)d\]")
sessions, open_ = [], {}
positions, logins = [], []
for e in ev:
    if e["event"] != "console output":
        continue
    line = e["args"][0]
    if m := join_re.search(line):
        open_[m.group(1)] = e["_t"]
    elif m := left_re.search(line):
        start = open_.pop(m.group(1), None)
        if start:
            sessions.append({"player": m.group(1), "start": start, "end": e["_t"], "seconds": round(e["_t"] - start, 1)})
    if m := login_re.search(line):
        logins.append({"player": m.group(1), "source_ip": m.group(2), "spawn": [float(m.group(i)) for i in (3, 4, 5)]})
    if m := pos_re.search(line):
        positions.append({"player": m.group(1), "t": round(e["_t"] - run_start, 1), "pos": [round(float(m.group(i)), 1) for i in (2, 3, 4)]})

server_runtime = round(run_end - run_start, 1)
print(f"server runtime (status running->offline): {server_runtime}s; last stats.uptime: {max(u for u in uptimes if u) / 1000:.1f}s; "
      f"power-on to offline: {t_off - t_power:.1f}s")
for s in sessions:
    real = truth[s["player"]]
    print(f"  session {s['player']}: {s['seconds']}s (bot ran {real['end'] - real['start']:.1f}s incl. connect/disconnect)")
union = sorted((s["start"], s["end"]) for s in sessions)
occupied, cur_s, cur_e = 0.0, None, None
for s, e in union:
    if cur_e is None or s > cur_e:
        occupied += (cur_e - cur_s) if cur_e else 0
        cur_s, cur_e = s, e
    else:
        cur_e = max(cur_e, e)
occupied += (cur_e - cur_s) if cur_e else 0
print(f"sum of player playtime: {sum(s['seconds'] for s in sessions):.1f}s; time with >=1 player online: {occupied:.1f}s; "
      f"empty server time: {server_runtime - occupied:.1f}s")
print("logins:", logins)
print("position samples:", len(positions), positions[:4], "...")
print("event types:", sorted({e["event"] for e in ev}))
record(exp, {"server_runtime_s": server_runtime, "sessions": sessions, "logins": logins,
             "positions": positions, "occupied_s": round(occupied, 1)})
