"""E08c: crash detection in isolation (no crash in the preceding 60 s), plus Wings reattachment.

usage: e08c_crash_isolated.py <server.json>
Run right after restarting Wings: reports the first websocket status (reattachment), waits 65 s so
Wings' crash guard is clear, crashes the game (stand-in `ut-crash`, exit 137) and records the timeline.
"""
import json
import sys
import time

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
c = Api("client", "client_bridge", "E08b-runtime-failures")
con = Console(c, server)
first = con.pump(3)
first_status = [e["args"][0] for e in first if e["event"] == "status"][:2]
print("websocket status after Wings restart:", first_status,
      "| REST:", c.get(f"servers/{server}/resources").json()["attributes"]["current_state"])
record("E08b-runtime-failures", {"case": "wings back", "first_status": first_status})
if first_status[-1:] != ["running"]:
    c.post(f"servers/{server}/power", {"signal": "start"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["running"], 90)
time.sleep(65)
con.events.clear()
t0 = time.time()
con.send("send command", "ut-crash")
con.pump(40)
timeline = [(round(e["_t"] - t0, 1), e["event"], (e.get("args") or [""])[0][:100]) for e in con.events if e["event"] != "stats"]
timeline = [x for x in timeline if x[1] == "status" or "Daemon" in x[2] or "Done (" in x[2] or "crash" in x[2].lower()]
for x in timeline:
    print(" ", x)
record("E08b-runtime-failures", {"case": "crash while running (isolated)", "timeline": timeline})
con.close()
