"""E08d: what survives when the Pelican server hosting a world is deleted (missing/deleted server case).

usage: e08d_server_deletion.py
Creates a disposable friend-owned server (external_id ut-world:delete-me): take a backup, delete the server through
the Application API, then check the Client API, the external_id lookup, the backup record and the
backup archive on the node.
"""
import subprocess
import time
from pathlib import Path

from ptlab import Api, Console, record

exp = "E08d-server-deletion"
app = Api("application", "app_full", exp)
friend = Api("client", "client_friend", exp)
friend_id = app.get("users", params={"filter[username]": "utfriend"}).json()["data"][0]["attributes"]["id"]
free = [a["attributes"]["id"] for a in app.get("nodes/1/allocations", params={"per_page": 100}).json()["data"]
        if not a["attributes"]["assigned"] and a["attributes"]["alias"]][0]
srv = app.post("servers", {
    "name": "Disposable world host", "external_id": "ut-world:delete-me", "user": friend_id, "egg": 1,
    "docker_image": "~utpelican/yolk-java25:local", "startup": "java -Xms128M -jar {{SERVER_JARFILE}}",
    "environment": {"SERVER_JARFILE": "server.jar", "ARTIFACT_URL": "http://172.18.0.1:8099/server.jar"},
    "limits": {"memory": 1024, "swap": 0, "disk": 2048, "io": 500, "cpu": 100},
    "feature_limits": {"databases": 0, "allocations": 0, "backups": 2}, "allocation": {"default": free},
}).json()["attributes"]
time.sleep(8)
sid, ident, uuid = srv["id"], srv["identifier"], srv["uuid"]
b = friend.post(f"servers/{ident}/backups", {"name": "before-delete"}).json()["attributes"]
con = Console(friend, ident)
con.until(lambda m: m["event"].startswith("backup"), 60)
con.close()
backups_dir = Path("/var/lib/pelican/backups") / uuid
on_disk_before = sorted(p.name for p in backups_dir.glob(f"{b['uuid']}*"))
r = app.call("DELETE", f"servers/{sid}")
time.sleep(3)
result = {
    "delete_status": r.status_code,
    "client_get_after": friend.get(f"servers/{ident}").status_code,
    "external_lookup_after": app.get("servers/external/ut-world:delete-me").status_code,
    "backup_archive_on_node_before": on_disk_before,
    "backup_archive_on_node_after": sorted(p.name for p in backups_dir.glob(f"{b['uuid']}*")),
    "volume_exists_after": Path(f"/var/lib/pelican/volumes/{uuid}").exists(),
    "container_exists_after": subprocess.run(["docker", "inspect", uuid], capture_output=True).returncode == 0,
}
print(result)
record(exp, result)
