"""Discovery harness for the Pelican experiments.

Thin wrappers around Pelican's public Application and Client APIs that append every request and
response to an evidence log (JSON lines) with credentials redacted. This is experiment
scaffolding only; it is not the Unnamed Tracking integration.

Configuration (environment):
    PELICAN_URL          Panel base URL (default http://127.0.0.1:8000)
    PELICAN_SECRETS_DIR  Directory holding <name>.key files (default /srv/pelican/secrets)
    PELICAN_EVIDENCE     Evidence JSONL path (default /srv/pelican/evidence/api-calls.jsonl)
"""

from __future__ import annotations

import json
import os
import re
import ssl
import time
from pathlib import Path
from typing import Any

import requests
import websocket

PANEL = os.environ.get("PELICAN_URL", "http://127.0.0.1:8000")
SECRETS = Path(os.environ.get("PELICAN_SECRETS_DIR", "/srv/pelican/secrets"))
EVIDENCE = Path(os.environ.get("PELICAN_EVIDENCE", "/srv/pelican/evidence/api-calls.jsonl"))
REDACT_KEYS = {"socket", "url"}
# Any field whose name contains one of these is redacted, e.g. token, token_id, daemon_token and
# the secret_token Pelican returns once when an API key is created.
REDACT_KEY_PARTS = ("token", "secret", "password")
# Secrets that can also appear inside other strings: full API keys (16-character identifier + 32-
# character token), websocket JWTs and signed-URL query parameters.
SECRET_PATTERN = re.compile(
    r"p(?:app|acc)_[A-Za-z0-9]{43,}|eyJ[\w-]+\.[\w-]+\.[\w-]+|(?<=[?&])(?:signature|token)=[^&\s\"']+"
)


def _key(name: str) -> str:
    return (SECRETS / f"{name}.key").read_text().strip()


def _is_secret_field(name: str) -> bool:
    name = name.lower()
    return name in REDACT_KEYS or any(part in name for part in REDACT_KEY_PARTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("<redacted>" if _is_secret_field(k) and isinstance(v, str) else _redact(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str):
        return SECRET_PATTERN.sub("<redacted>", value)
    return value


def record(experiment: str, entry: dict[str, Any]) -> None:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "experiment": experiment, **entry}
    with EVIDENCE.open("a") as fh:
        fh.write(json.dumps(_redact(entry)) + "\n")


class Api:
    """One credential against one API surface ("application" or "client")."""

    def __init__(self, surface: str, key_name: str, experiment: str = "adhoc") -> None:
        self.surface = surface
        self.key_name = key_name
        self.experiment = experiment
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {_key(key_name)}", "Accept": "application/json"})

    def call(self, method: str, path: str, *, json_body: Any = None, params: dict | None = None,
             data: bytes | str | None = None, headers: dict | None = None, quiet: bool = False,
             timeout: float = 60) -> requests.Response:
        url = f"{PANEL}/api/{self.surface}/{path.lstrip('/')}"
        started = time.monotonic()
        resp = self.session.request(method, url, json=json_body, params=params, data=data,
                                    headers=headers, timeout=timeout)
        elapsed = round((time.monotonic() - started) * 1000)
        try:
            body: Any = resp.json()
        except ValueError:
            body = resp.text[:400]
        record(self.experiment, {
            "surface": self.surface, "credential": self.key_name, "method": method,
            "path": f"/api/{self.surface}/{path.lstrip('/')}", "params": params,
            "request": json_body if json_body is not None else (None if data is None else f"<{len(data)} bytes>"),
            "status": resp.status_code, "ms": elapsed, "response": body if not quiet else "<omitted>",
        })
        return resp

    def get(self, path: str, **kw: Any) -> requests.Response:
        return self.call("GET", path, **kw)

    def post(self, path: str, body: Any = None, **kw: Any) -> requests.Response:
        return self.call("POST", path, json_body=body, **kw)


def wait_for(predicate, timeout: float, interval: float = 1.0, what: str = "condition") -> float:
    """Polls predicate() until truthy; returns seconds waited or raises TimeoutError."""
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if predicate():
            return round(time.monotonic() - started, 2)
        time.sleep(interval)
    raise TimeoutError(f"timed out after {timeout}s waiting for {what}")


class Console:
    """Pelican server websocket (console/status/stats) via the Client API's signed credentials."""

    def __init__(self, client: Api, server: str) -> None:
        creds = client.get(f"servers/{server}/websocket").json()["data"]
        self.ws = websocket.create_connection(creds["socket"], origin=PANEL, timeout=5,
                                              sslopt={"cert_reqs": ssl.CERT_NONE})
        self.ws.send(json.dumps({"event": "auth", "args": [creds["token"]]}))
        self.events: list[dict[str, Any]] = []

    def pump(self, seconds: float) -> list[dict[str, Any]]:
        deadline = time.monotonic() + seconds
        fresh: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            try:
                msg = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            msg["_t"] = time.time()
            fresh.append(msg)
        self.events.extend(fresh)
        return fresh

    def until(self, predicate, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                msg = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            msg["_t"] = time.time()
            self.events.append(msg)
            if predicate(msg):
                return msg
        raise TimeoutError("websocket condition not met")

    def send(self, event: str, *args: str) -> None:
        self.ws.send(json.dumps({"event": event, "args": list(args)}))

    def close(self) -> None:
        self.ws.close()
