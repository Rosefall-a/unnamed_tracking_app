"""E08a: hostile and broken archives through the deploy path (signed upload + files/decompress).

usage: e08a_archive_safety.py <server.json> <good_archive>
Runs as the least-privilege bridge identity against a stopped server. Each case uploads an
archive, decompresses it into a fresh staging directory, then records the API result, what
landed inside the server volume and whether anything escaped onto the host.
"""
import gzip
import io
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path

import requests

from ptlab import Api, Console, record

server_info = json.load(open(sys.argv[1]))
server, uuid = server_info["identifier"], server_info["uuid"]
good = Path(sys.argv[2]).read_bytes()
exp = "E08a-archive-safety"
c = Api("client", "client_bridge", exp)
volume = Path("/var/lib/pelican/volumes") / uuid
work = Path("/srv/pelican/evidence/e08a")
shutil.rmtree(work, ignore_errors=True)
work.mkdir(parents=True)
SENTINELS = [Path("/tmp/ut-escape.txt"), Path("/tmp/ut-abs.txt"), Path("/var/lib/pelican/volumes/ut-up.txt"),
             Path("/etc/ut-through-symlink.txt"), Path("/var/lib/pelican/ut-through-symlink.txt")]
for s in SENTINELS:
    s.unlink(missing_ok=True)

con = Console(c, server)
con.pump(0.5)
if [e["args"][0] for e in con.events if e["event"] == "status"][-1:] != ["offline"]:
    c.post(f"servers/{server}/power", {"signal": "stop"})
    con.until(lambda m: m["event"] == "status" and m["args"] == ["offline"], 60)
con.close()


def tar_gz(build) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        build(tf)
    return buf.getvalue()


def add(tf, name, data=b"ut", **kw):
    info = tarfile.TarInfo(name)
    for k, v in kw.items():
        setattr(info, k, v)
    if info.type == tarfile.REGTYPE:
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    else:
        tf.addfile(info)


def traversal(tf):
    add(tf, "world/level.dat", b"not really nbt")
    add(tf, "../../../../tmp/ut-escape.txt")
    add(tf, "/tmp/ut-abs.txt")
    add(tf, "world/../../ut-up.txt")


def symlinks(tf):
    add(tf, "world/etc-link", type=tarfile.SYMTYPE, linkname="/etc")
    add(tf, "world/etc-link/ut-through-symlink.txt")
    add(tf, "world/up-link", type=tarfile.SYMTYPE, linkname="../../..")
    add(tf, "world/up-link/ut-through-symlink.txt")
    add(tf, "world/hard", type=tarfile.LNKTYPE, linkname="/etc/passwd")


def bomb_bytes(gib: int) -> bytes:
    """A tar.gz containing one file of `gib` GiB of zeros, streamed so it never sits in memory."""
    path = work / f"bomb-{gib}g.tar.gz"
    if not path.exists():
        with gzip.open(path, "wb", compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode="w|") as tf:
                info = tarfile.TarInfo("world/zeros.bin")
                info.size = gib * 1024**3

                class Zeros(io.RawIOBase):
                    left = info.size

                    def readable(self):
                        return True

                    def readinto(self, b):
                        n = min(len(b), self.left)
                        b[:n] = bytes(n)
                        self.left -= n
                        return n

                tf.addfile(info, io.BufferedReader(Zeros(), 1 << 20))
    return path.read_bytes()


cases = {
    "path traversal + absolute paths": tar_gz(traversal),
    "symlink + hardlink escape": tar_gz(symlinks),
    "truncated archive (60%)": good[: int(len(good) * 0.6)],
    "not an archive (random bytes)": os.urandom(200_000),
    "decompression bomb (6 GiB of zeros, disk limit 4 GiB)": bomb_bytes(6),
}


def upload(name: str, blob: bytes):
    url = c.get(f"servers/{server}/files/upload").json()["attributes"]["url"]
    return requests.post(url, params={"directory": "/"}, files={"files": (name, blob)}, timeout=600)


def tree(root: Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*")) if root.exists() else []:
        kind = "L" if p.is_symlink() else ("d" if p.is_dir() else "f")
        size = p.lstat().st_size if kind == "f" else ""
        out.append(f"{kind} {p.relative_to(root)} {size}".strip())
    return out


for label, blob in cases.items():
    name = f"case-{int(time.time() * 1000)}.tar.gz"
    staging = f"/.ut-staging/{name[:-7]}"
    t0 = time.monotonic()
    up = upload(name, blob)
    c.post(f"servers/{server}/files/create-folder", {"root": "/", "name": staging.lstrip("/")})
    # Move the archive into staging so extraction is confined there.
    c.call("PUT", f"servers/{server}/files/rename", json_body={"root": "/", "files": [{"from": name, "to": f"{staging.lstrip('/')}/{name}"}]})
    r = c.post(f"servers/{server}/files/decompress", {"root": staging, "file": name}, timeout=600)
    detail = r.text[:300] if r.status_code >= 400 else ""
    landed = tree(volume / staging.lstrip("/"))
    escaped = [str(s) for s in SENTINELS if s.exists()]
    print(f"\n== {label}\n   upload {up.status_code} ({len(blob)} bytes), decompress HTTP {r.status_code} in {time.monotonic() - t0:.1f}s {detail}")
    print(f"   landed in staging: {landed[:8]}{' ...' if len(landed) > 8 else ''}")
    print(f"   escaped to host: {escaped or 'none'}")
    record(exp, {"case": label, "upload_status": up.status_code, "decompress_status": r.status_code,
                 "detail": detail, "landed": landed[:20], "escaped": escaped})
    c.post(f"servers/{server}/files/delete", {"root": "/", "files": [".ut-staging"]})

# Interrupted upload: the client dies after 40% of a multipart body.
url = c.get(f"servers/{server}/files/upload").json()["attributes"]["url"]
before = set(tree(volume))


def chunks():
    head = b"--b\r\nContent-Disposition: form-data; name=\"files\"; filename=\"interrupted.tar.gz\"\r\n\r\n"
    yield head
    yield good[: int(len(good) * 0.4)]
    raise ConnectionAbortedError("simulated client crash mid-upload")


try:
    requests.post(url, params={"directory": "/"}, data=chunks(), headers={"Content-Type": "multipart/form-data; boundary=b"}, timeout=30)
    outcome = "completed?"
except Exception as exc:  # noqa: BLE001 - recording whatever the client library raises
    outcome = type(exc).__name__
time.sleep(2)
after = [p for p in tree(volume) if p not in before]
print(f"\n== interrupted upload: client saw {outcome}; new entries in volume: {after or 'none'}")
record(exp, {"case": "interrupted upload", "client": outcome, "new_entries": after})
