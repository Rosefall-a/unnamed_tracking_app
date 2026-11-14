from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import quote, urlsplit

import requests

API_PREFIX = "/api/v2"
# Atlas caps a search page at 100; the app never needs more than a few
MAX_SEARCH_LIMIT = 50
_ATLAS_ID_PREFIX = "atlas:"
# Cloud metadata endpoints that are not link-local addresses but are just as
# dangerous to reach from a server-side request
_BLOCKED_HOSTS = {"metadata.google.internal", "metadata.goog"}


class AtlasError(RuntimeError):
    """Raised when an Atlas node cannot be reached or rejects the request."""


def _address_is_blocked(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    return ip.is_link_local or ip.is_unspecified or ip.is_multicast


def normalize_base_url(raw: str) -> str:
    """The server root of an Atlas node (an http(s) origin plus an optional
    path prefix), without a trailing slash or a pasted `/api/v2`.

    Atlas is self-hosted, so a LAN or loopback address is allowed. Link-local
    addresses (including 169.254.169.254, where clouds serve instance
    credentials) and the cloud metadata hostnames are refused, as is a name
    that resolves to one.
    """
    value = (raw or "").strip().rstrip("/")
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise AtlasError("The Atlas address must be a plain http:// or https:// URL.")

    host = parts.hostname.lower()
    if host in _BLOCKED_HOSTS or _address_is_blocked(host):
        raise AtlasError("That Atlas address is not allowed.")
    try:
        infos = socket.getaddrinfo(host, parts.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        infos = []  # an unresolvable name fails later, with the network's own error
    if any(_address_is_blocked(str(info[4][0])) for info in infos):
        raise AtlasError("That Atlas address is not allowed.")

    if value.endswith(API_PREFIX):
        value = value[: -len(API_PREFIX)].rstrip("/")
    return value


def _error_detail(response: requests.Response) -> str | None:
    """Atlas answers with `{"error": {"message"}}` for its own errors and
    `{"detail": ...}` for HTTP ones; either may be absent."""
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    detail = body.get("detail")
    return detail if isinstance(detail, str) else None


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class AtlasClient:
    """Minimal read-only client for an Atlas metadata node — a self-hosted
    game database. Needs a token with the `read` scope."""

    def __init__(
        self, base_url: str, token: str, *, session: requests.Session | None = None
    ) -> None:
        if not base_url or not token:
            raise AtlasError("An Atlas address and token are both required.")
        self.base_url = normalize_base_url(base_url)
        self.token = token
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "unnamed-tracking-app/1.0")

    def _get(self, path: str, *, authenticated: bool = True, **params: Any) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = self.session.get(
                f"{self.base_url}{API_PREFIX}{path}",
                params=params or None,
                headers=headers,
                timeout=15,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise AtlasError(f"Could not reach Atlas: {exc}") from exc

        if response.status_code == 401:
            raise AtlasError("Atlas rejected the token.")
        if response.status_code == 403:
            raise AtlasError("The Atlas token needs the read scope.")
        if response.status_code == 429:
            retry = response.headers.get("Retry-After")
            raise AtlasError(
                f"Atlas is rate limiting requests; try again in {retry}s."
                if retry
                else "Atlas is rate limiting requests."
            )
        if response.status_code >= 400:
            detail = _error_detail(response)
            raise AtlasError(
                f"Atlas request failed ({response.status_code})" + (f": {detail}" if detail else ".")
            )
        if response.is_redirect:
            raise AtlasError("Atlas answered with a redirect; use the server's final address.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise AtlasError("Atlas returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise AtlasError("Atlas returned an unexpected response.")
        return payload

    def validate(self) -> dict[str, Any]:
        """Checks the address (the public /site document) and then the token
        (a one-result search, which needs the read scope)."""
        site = self._get("/site", authenticated=False)
        self._get("/games", q="a", limit=1, type="game")
        name = site.get("name")
        return {"validated": True, "node_name": name if isinstance(name, str) else None}

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        payload = self._get(
            "/games", q=query, limit=max(1, min(limit, MAX_SEARCH_LIMIT)), type="game"
        )
        records = payload.get("results")
        if not isinstance(records, list):
            return []

        games: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            identity, title = record.get("id"), record.get("title")
            if not isinstance(identity, str) or not isinstance(title, str) or not title.strip():
                continue
            if record.get("media_type", "game") != "game":
                continue
            games.append(
                {
                    "id": identity,
                    "title": title.strip(),
                    "description": record.get("description")
                    if isinstance(record.get("description"), str)
                    else None,
                    "release_date": record.get("release_date")
                    if isinstance(record.get("release_date"), str)
                    else None,
                    "developer": record.get("developer")
                    if isinstance(record.get("developer"), str)
                    else None,
                    "publisher": record.get("publisher")
                    if isinstance(record.get("publisher"), str)
                    else None,
                    "series": record.get("series") if isinstance(record.get("series"), str) else None,
                    "age_rating": record.get("age_rating")
                    if isinstance(record.get("age_rating"), str)
                    else None,
                    "genres": _text_list(record.get("genres")),
                    "tags": _text_list(record.get("tags")) + _text_list(record.get("themes")),
                    "features": _text_list(record.get("features")),
                    "url": self.record_url(identity),
                }
            )
        return games

    def record_url(self, identity: str) -> str | None:
        """The record's page on the node, when the id has the expected shape."""
        if not identity.startswith(_ATLAS_ID_PREFIX):
            return None
        return f"{self.base_url}/game/{quote(identity, safe=':')}"
