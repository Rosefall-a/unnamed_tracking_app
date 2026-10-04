"""E12: deploying a world larger than the node's upload limit, as independent part archives.

usage: e12_large_world_parts.py <server.json>   (run with Wings api.upload_limit lowered to 1 MB)
Builds a ~4.5 MB world of incompressible files, shows a single upload is refused, then uploads it as
part archives (each under the limit, split on file boundaries), decompresses every part into the
same staging directory and verifies each file byte-for-byte through the Client API.
"""
import hashlib
import io
import json
import os
import sys
import tarfile
import time

import requests

from ptlab import Api, record

server = json.load(open(sys.argv[1]))["identifier"]
exp = "E12-large-world-parts"
c = Api("client", "client_bridge", exp)
LIMIT = 1024 * 1024
files = {f"world/region/r.{i}.0.mca": os.urandom(600 * 1024) for i in range(7)}
files["world/level.dat"] = os.urandom(2048)
want = {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}


def tar_gz(names):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for n in names:
            info = tarfile.TarInfo(n)
            info.size = len(files[n])
            tf.addfile(info, io.BytesIO(files[n]))
    return buf.getvalue()


def upload(name, blob):
    url = c.get(f"servers/{server}/files/upload").json()["attributes"]["url"]
    return requests.post(url, params={"directory": "/.ut-staging-e12"}, files={"files": (name, blob)}, timeout=120)


c.post(f"servers/{server}/files/create-folder", {"root": "/", "name": ".ut-staging-e12"})
whole = tar_gz(list(files))
r = upload("whole.tar.gz", whole)
print(f"single archive {len(whole)} bytes -> {r.status_code} {r.text[:160]}")
record(exp, {"step": "single upload over limit", "bytes": len(whole), "status": r.status_code, "body": r.text[:200]})

# Greedy split on file boundaries so every part stays under the limit.
parts, current = [], []
for n in files:
    if current and len(tar_gz(current + [n])) > LIMIT * 0.95:
        parts.append(current)
        current = []
    current.append(n)
parts.append(current)
t0 = time.monotonic()
for i, names in enumerate(parts):
    blob = tar_gz(names)
    r = upload(f"part-{i}.tar.gz", blob)
    r.raise_for_status()
    d = c.post(f"servers/{server}/files/decompress", {"root": "/.ut-staging-e12", "file": f"part-{i}.tar.gz"})
    c.post(f"servers/{server}/files/delete", {"root": "/.ut-staging-e12", "files": [f"part-{i}.tar.gz"]})
    print(f"part {i}: {len(blob)} bytes, {len(names)} files -> upload {r.status_code}, decompress {d.status_code}")
ok = 0
for n, h in want.items():
    url = c.get(f"servers/{server}/files/download", params={"file": f"/.ut-staging-e12/{n}"}, quiet=True).json()["attributes"]["url"]
    ok += hashlib.sha256(requests.get(url, timeout=60).content).hexdigest() == h
print(f"{len(parts)} parts in {time.monotonic() - t0:.1f}s; {ok}/{len(want)} files byte-identical in staging")
record(exp, {"step": "part upload", "parts": len(parts), "identical": ok, "files": len(want)})
c.post(f"servers/{server}/files/delete", {"root": "/", "files": [".ut-staging-e12"]})
