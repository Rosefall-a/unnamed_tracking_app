"""E04d: a world-only capture using Pelican's backup `ignored` list with negation patterns.

usage: e04d_world_only_capture.py <server.json>
Backs up with ignored = "*", "!world", "!world/**" (bridge identity) and lists what the archive holds.
"""
import io
import json
import sys
import tarfile

import requests

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
c = Api("client", "client_bridge", "E04d-ignore-negation")
con = Console(c, server)
con.pump(0.5)
b = c.post(f"servers/{server}/backups", {"name": "ut-negation-test", "ignored": "*\n!world\n!world/**"}).json()["attributes"]
con.until(lambda m: m["event"] == "backup completed", 60)
url = c.get(f"servers/{server}/backups/{b['uuid']}/download").json()["attributes"]["url"]
names = tarfile.open(fileobj=io.BytesIO(requests.get(url, timeout=60).content)).getnames()
top = sorted({n.split("/")[0] for n in names})
print("top-level entries:", top, "| total entries:", len(names))
record("E04d-ignore-negation", {"ignored": "*\\n!world\\n!world/**", "top_level": top, "entries": len(names)})
con.close()
