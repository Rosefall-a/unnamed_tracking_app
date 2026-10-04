"""E02: power lifecycle and readiness through the Client API + websocket as the server owner."""
import json
import sys
import time

from ptlab import Api, Console, wait_for

server = json.load(open(sys.argv[1]))["identifier"]
client = Api("client", "client_player", "E02-lifecycle")
info = client.get(f"servers/{server}").json()["attributes"]
alloc = [a["attributes"] for a in info["relationships"]["allocations"]["data"] if a["attributes"]["is_default"]][0]
print("join info:", {"ip": alloc["ip"], "alias": alloc["ip_alias"], "port": alloc["port"]},
      "| sftp:", info["sftp_details"], "| limits:", info["limits"])
print("state before:", client.get(f"servers/{server}/resources").json()["attributes"]["current_state"])

con = Console(client, server)
con.pump(1)
timeline = []


def phase(label, signal, done):
    t0 = time.monotonic()
    client.post(f"servers/{server}/power", {"signal": signal})
    msg = con.until(done, 120)
    timeline.append((label, round(time.monotonic() - t0, 2), msg.get("args")))
    print(f"{label}: {timeline[-1][1]}s -> {msg['event']} {msg.get('args')}")


ready = lambda m: m["event"] == "console output" and ")! For help, type " in m["args"][0]
offline = lambda m: m["event"] == "status" and m["args"] == ["offline"]
phase("start->console Done", "start", ready)
statuses = [e["args"][0] for e in con.events if e["event"] == "status"]
print("status events seen during start:", statuses)
print("resources while running:", {k: v for k, v in client.get(f"servers/{server}/resources").json()["attributes"].items() if k != "resources"})
phase("stop->offline", "stop", offline)
phase("start again->Done", "start", ready)
con.events.clear()
phase("restart->Done", "restart", ready)
print("status events during restart:", [e["args"][0] for e in con.events if e["event"] == "status"])
phase("kill->offline", "kill", offline)
kill_tail = [e["args"][0] for e in con.events if e["event"] in ("console output", "daemon message")][-3:]
print("console tail after kill:", kill_tail)
event_types = sorted({e["event"] for e in con.events})
print("websocket event types observed:", event_types)
con.close()
