"""E01: create a server for a UT world through the Application API and wait for installation."""
import json
import sys
import time

from ptlab import Api, wait_for

external_id = sys.argv[1] if len(sys.argv) > 1 else "ut-world:demo-a"
allocation = int(sys.argv[2]) if len(sys.argv) > 2 else 1
app = Api("application", "app_full", "E01-create-server")
player_id = app.get("users", params={"filter[username]": "utplayer"}).json()["data"][0]["attributes"]["id"]
body = {
    "name": f"UT host for {external_id}", "description": "Created by UT discovery experiment E01",
    "external_id": external_id, "user": player_id, "egg": 1,
    "docker_image": "~utpelican/yolk-java25:local",
    "startup": "java -Xms128M -XX:MaxRAMPercentage=95.0 -jar {{SERVER_JARFILE}}",
    "environment": {"SERVER_JARFILE": "server.jar", "ARTIFACT_URL": "http://172.18.0.1:8099/server.jar"},
    "limits": {"memory": 1536, "swap": 0, "disk": 4096, "io": 500, "cpu": 200},
    "feature_limits": {"databases": 0, "allocations": 0, "backups": 5},
    "allocation": {"default": allocation}, "start_on_completion": False,
}
t0 = time.monotonic()
r = app.post("servers", body)
print("create:", r.status_code, f"{time.monotonic() - t0:.2f}s")
r.raise_for_status()
s = r.json()["attributes"]
print(json.dumps({k: s[k] for k in ["id", "uuid", "identifier", "external_id", "status", "node", "allocation"]}))
sid = s["id"]
waited = wait_for(lambda: app.get(f"servers/{sid}", quiet=True).json()["attributes"]["status"] is None,
                  300, 2, "install")
print(f"install finished after {waited}s")
r = app.get(f"servers/external/{external_id}")
print("lookup by external_id:", r.status_code, r.json()["attributes"]["uuid"] == s["uuid"])
r = app.post("servers", body)
print("duplicate external_id create:", r.status_code, json.dumps(r.json())[:300])
json.dump({"id": sid, "uuid": s["uuid"], "identifier": s["identifier"], "external_id": external_id},
          open(f"/srv/pelican/evidence/server-{external_id.split(':')[-1]}.json", "w"))
