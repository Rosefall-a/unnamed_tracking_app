"""E05: can Wings fetch a world archive itself (Client API files/pull) instead of UT uploading it?

usage: e05_files_pull.py <server.json> <archive> <artifact_host_dir>
Serves <archive> from the artifact host and asks Wings to pull it from several addresses:
loopback, the pelican0 gateway (RFC1918) and the host's non-RFC1918 address. Records the API
result, the Wings outcome and a sha256 of what landed on the server.
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import requests

from ptlab import Api, record

server = json.load(open(sys.argv[1]))["identifier"]
archive = Path(sys.argv[2])
shutil.copy(archive, Path(sys.argv[3]) / archive.name)
want = hashlib.sha256(archive.read_bytes()).hexdigest()
exp = "E05-files-pull"
c = Api("client", "client_player", exp)
targets = {
    "loopback": f"http://127.0.0.1:8099/{archive.name}",
    "pelican0 gateway (172.16/12)": f"http://172.18.0.1:8099/{archive.name}",
    "host address (192.0.2.2, not RFC1918)": f"http://192.0.2.2:8099/{archive.name}",
}
for label, url in targets.items():
    name = f"pulled-{int(time.time() * 1000)}.tar.gz"
    t0 = time.monotonic()
    r = c.post(f"servers/{server}/files/pull", {"url": url, "directory": "/", "filename": name, "foreground": True})
    landed = None
    if r.status_code == 204:
        dl = c.get(f"servers/{server}/files/download", params={"file": f"/{name}"}, quiet=True).json()["attributes"]["url"]
        landed = hashlib.sha256(requests.get(dl, timeout=60).content).hexdigest() == want
        c.post(f"servers/{server}/files/delete", {"root": "/", "files": [name]})
    detail = None if r.status_code == 204 else r.json()["errors"][0]["detail"]
    print(f"{label:40s} -> HTTP {r.status_code} in {time.monotonic() - t0:.2f}s; intact={landed}; detail={detail}")
    record(exp, {"target": label, "status": r.status_code, "intact": landed, "detail": detail})
