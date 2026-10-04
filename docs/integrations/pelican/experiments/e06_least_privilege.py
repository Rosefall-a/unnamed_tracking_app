"""E06: a least-privilege Pelican identity for the UT bridge.

usage: e06_least_privilege.py <server.json>
The server owner (client_player) adds a dedicated non-admin account (utbridge, key client_bridge)
as a subuser with only the permissions the Run/Capture/Restore sequences need. Every allowed
operation is exercised, every excluded permission is probed, a server the bridge was never
added to is probed for existence leaks, and per-key allowed_ips enforcement is checked.
"""
import json
import sys

import requests

from ptlab import Api, Console, record

server = json.load(open(sys.argv[1]))["identifier"]
exp = "E06-least-privilege"
owner = Api("client", "client_player", exp)
bridge = Api("client", "client_bridge", exp)
friend = Api("client", "client_friend", exp)
app = Api("application", "app_full", exp)

# The cross-tenant probes need a server the bridge was never added to: one owned by utfriend.
if not friend.get("").json()["data"]:
    friend_id = app.get("users", params={"filter[username]": "utfriend"}).json()["data"][0]["attributes"]["id"]
    egg = [e["attributes"]["id"] for e in app.get("eggs").json()["data"] if e["attributes"]["name"].startswith("UT Stand-in Minecraft")][0]
    free = [a["attributes"]["id"] for a in app.get("nodes/1/allocations", params={"per_page": 100}).json()["data"]
            if not a["attributes"]["assigned"] and a["attributes"]["alias"]][0]
    created = app.post("servers", {
        "name": "Friend world", "external_id": "ut-world:friend", "user": friend_id, "egg": egg,
        "docker_image": "~utpelican/yolk-java25:local", "startup": "java -Xms128M -XX:MaxRAMPercentage=95.0 -jar {{SERVER_JARFILE}}",
        "environment": {"SERVER_JARFILE": "server.jar", "ARTIFACT_URL": "http://172.18.0.1:8099/server.jar"},
        "limits": {"memory": 1024, "swap": 0, "disk": 2048, "io": 500, "cpu": 100},
        "feature_limits": {"databases": 0, "allocations": 0, "backups": 2}, "allocation": {"default": free},
    })
    print("created a utfriend-owned server for the cross-tenant probes ->", created.status_code)

BRIDGE_PERMISSIONS = [
    "websocket.connect", "control.console", "control.start", "control.stop", "control.restart",
    "file.read", "file.read-content", "file.create", "file.update", "file.delete",
    "backup.read", "backup.create", "backup.download", "backup.restore",
    "allocation.read", "startup.read", "settings.reinstall",
]

existing = {u["attributes"]["username"]: u["attributes"]["uuid"] for u in owner.get(f"servers/{server}/users").json()["data"]}
if "utbridge" in existing:
    r = owner.post(f"servers/{server}/users/{existing['utbridge']}", {"permissions": BRIDGE_PERMISSIONS})
else:
    r = owner.post(f"servers/{server}/users", {"email": "bridge@ut-pelican.test", "permissions": BRIDGE_PERMISSIONS})
print("owner grants subuser ->", r.status_code)

# What the bridge can see at all.
listing = bridge.get("").json()["data"]
print("bridge server list:", [(s["attributes"]["identifier"], s["attributes"].get("server_owner")) for s in listing])
print("permissions the Panel reports for the bridge:", sorted(bridge.get(f"servers/{server}").json()["meta"]["user_permissions"]))

results = []


def probe(label, expect, fn):
    r = fn()
    ok = (r.status_code < 400) == (expect == "allow")
    results.append({"op": label, "expect": expect, "status": r.status_code, "as_expected": ok})
    print(f"  {'OK ' if ok else 'BAD'} {expect:5s} {r.status_code} {label}")


S = f"servers/{server}"
probe("GET resources", "allow", lambda: bridge.get(f"{S}/resources"))
probe("GET websocket credentials", "allow", lambda: bridge.get(f"{S}/websocket"))
probe("GET files/list", "allow", lambda: bridge.get(f"{S}/files/list", params={"directory": "/"}))
probe("GET files/upload (signed URL)", "allow", lambda: bridge.get(f"{S}/files/upload"))
probe("POST files/create-folder", "allow", lambda: bridge.post(f"{S}/files/create-folder", {"root": "/", "name": "ut-e06"}))
probe("PUT files/rename", "allow", lambda: bridge.call("PUT", f"{S}/files/rename", json_body={"root": "/", "files": [{"from": "ut-e06", "to": "ut-e06b"}]}))
probe("POST files/delete", "allow", lambda: bridge.post(f"{S}/files/delete", {"root": "/", "files": ["ut-e06b"]}))
probe("GET backups", "allow", lambda: bridge.get(f"{S}/backups"))
probe("GET network/allocations", "allow", lambda: bridge.get(f"{S}/network/allocations"))
probe("GET startup", "allow", lambda: bridge.get(f"{S}/startup"))
probe("POST command (list)", "allow", lambda: bridge.post(f"{S}/command", {"command": "list"}))

probe("PUT startup/variable", "deny", lambda: bridge.call("PUT", f"{S}/startup/variable", json_body={"key": "SERVER_JARFILE", "value": "x.jar"}))
probe("PUT settings/docker-image", "deny", lambda: bridge.call("PUT", f"{S}/settings/docker-image", json_body={"docker_image": "x"}))
probe("POST settings/rename", "deny", lambda: bridge.post(f"{S}/settings/rename", {"name": "pwned"}))
probe("GET users (subusers)", "deny", lambda: bridge.get(f"{S}/users"))
probe("POST users (add subuser)", "deny", lambda: bridge.post(f"{S}/users", {"email": "x@ut-pelican.test", "permissions": ["control.start"]}))
probe("POST files/compress", "deny", lambda: bridge.post(f"{S}/files/compress", {"root": "/", "files": ["server.properties"]}))
probe("GET databases", "deny", lambda: bridge.get(f"{S}/databases"))
probe("GET schedules", "deny", lambda: bridge.get(f"{S}/schedules"))
probe("GET activity", "deny", lambda: bridge.get(f"{S}/activity"))
probe("POST account/api-keys (mint new key)", "deny", lambda: bridge.post("account/api-keys", {"description": "escalate", "allowed_ips": []}))
probe("GET application/servers", "deny", lambda: requests.get("http://127.0.0.1:8000/api/application/servers",
      headers={"Authorization": bridge.session.headers["Authorization"], "Accept": "application/json"}))


def call_with_ip_restricted_key(allowed_ips):
    """Mints an owner key limited to allowed_ips, calls the Client API from 127.0.0.1, deletes the key.

    The key's secret is only held in memory; the logged creation response has it redacted.
    """
    minted = owner.post("account/api-keys", {"description": "ut-e06-allowed-ips", "allowed_ips": allowed_ips}).json()
    identifier = minted["attributes"]["identifier"]
    try:
        return requests.get("http://127.0.0.1:8000/api/client", timeout=30, headers={
            "Authorization": f"Bearer {identifier}{minted['meta']['secret_token']}", "Accept": "application/json"})
    finally:
        owner.call("DELETE", f"account/api-keys/{identifier}")


probe("key with allowed_ips [203.0.113.7], called from 127.0.0.1", "deny", lambda: call_with_ip_restricted_key(["203.0.113.7"]))
probe("key with allowed_ips [127.0.0.1], called from 127.0.0.1", "allow", lambda: call_with_ip_restricted_key(["127.0.0.1"]))

# A server the bridge was never added to (owned by utfriend).
other = [s["attributes"]["identifier"] for s in friend.get("").json()["data"]]
if other:
    probe("GET another user's server", "deny", lambda: bridge.get(f"servers/{other[0]}"))
    probe("POST power on another user's server", "deny", lambda: bridge.post(f"servers/{other[0]}/power", {"signal": "start"}))
probe("GET a server UUID that does not exist", "deny", lambda: bridge.get("servers/00000000"))

con = Console(bridge, server)
events = {e["event"] for e in con.pump(2)}
print("bridge websocket events in 2s:", sorted(events))
con.close()
record(exp, {"permissions": BRIDGE_PERMISSIONS, "results": results})

# The key-minting probe succeeds (a known finding), so remove the sibling key it created.
for key in bridge.get("account/api-keys").json()["data"]:
    if key["attributes"]["description"] == "escalate":
        print("deleted minted sibling key ->", bridge.call("DELETE", f"account/api-keys/{key['attributes']['identifier']}").status_code)
print("RESULT:", "PASS" if all(r["as_expected"] for r in results) else "CHECK (see BAD lines; key minting is a known finding)")
