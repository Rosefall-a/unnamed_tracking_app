"""Epic Games Store account client: sign-in, owned library, playtime, catalog.

Epic has no public API for a player's library. This uses the same OAuth flow
and services as the open-source launchers Legendary, Heroic and Playnite's Epic
plugin: the player signs in on epicgames.com, which shows a one-time
authorization code; that code is traded for a token pair with the Epic
launcher's public client credentials (shipped in every copy of the launcher,
not a secret of anyone's account). Unsupported by Epic and can break without
notice if they change the flow.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from src.helpers.save_game_asset import AssetKind

_CLIENT_ID = "34a02cf8f4414e29b15921876da36f9a"
_CLIENT_SECRET = "daafbccc737745039dffe53d94fc76cf"
_TOKEN_URL = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token"
_LIBRARY_URL = "https://library-service.live.use1a.on.epicgames.com/library/api/public/items"
_PLAYTIME_URL = (
    "https://library-service.live.use1a.on.epicgames.com/library/api/public/playtime/account/"
    "{account_id}/all"
)
_CATALOG_URL = (
    "https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/"
    "{namespace}/bulk/items"
)
# signs in (if needed) and then shows a small JSON page with the code to paste
LOGIN_URL = (
    "https://www.epicgames.com/id/login?redirectUrl=https%3A%2F%2Fwww.epicgames.com%2Fid%2Fapi"
    f"%2Fredirect%3FclientId%3D{_CLIENT_ID}%26responseType%3Dcode"
)
_USER_AGENT = "UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit"
_TIMEOUT = 20
_CATALOG_CONCURRENCY = 8
# Unreal Engine marketplace assets share the library with games
_SKIPPED_NAMESPACES = frozenset({"ue"})
# catalog categories (first part of the path, as in "addons/durable") of
# things that are not a game to track
_NON_GAME_CATEGORIES = frozenset({"addons", "digitalextras", "plugins", "engines"})
_CODE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


class EpicError(RuntimeError):
    """Raised when Epic rejects a sign-in or library request, or is unreachable."""


class EpicSignInExpired(EpicError):
    """The saved sign-in no longer works: the player has to connect again."""


@dataclass(frozen=True)
class EpicSession:
    """A signed-in Epic account: the access token and the refresh token that
    replaces it, whose account it is, and when the access token runs out."""

    access_token: str
    refresh_token: str
    account_id: str
    display_name: str | None
    # unix seconds; the access token is good until then
    expires_at: float


def extract_authorization_code(raw: str) -> str:
    """The code from whatever was copied off Epic's code page: the bare code,
    the whole JSON page (`{"authorizationCode": "...", ...}`), or the
    `redirectUrl` it lists (`...?code=...`)."""
    value = raw.strip().strip("'\"").strip()
    if value.startswith("{"):
        try:
            parsed = json.loads(value)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            code = parsed.get("authorizationCode")
            if isinstance(code, str) and code:
                return code.strip()
            value = str(parsed.get("redirectUrl") or "")
    if "code=" in value:
        codes = parse_qs(urlparse(value).query).get("code")
        if codes:
            return codes[0].strip()
    if not _CODE.fullmatch(value):
        raise EpicError(
            "That doesn't look like an Epic authorization code: copy the "
            "authorizationCode value (32 letters and digits) from Epic's page."
        )
    return value


class EpicClient:
    """Calls Epic's account, library and catalog services."""

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})

    # ------------------------------------------------------------ sign-in
    def _token(self, form: dict[str, str]) -> EpicSession:
        try:
            resp = self.session.post(
                _TOKEN_URL,
                data={**form, "token_type": "eg1"},
                auth=(_CLIENT_ID, _CLIENT_SECRET),
                timeout=_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise EpicError(f"Could not reach Epic Games: {exc}") from exc
        try:
            payload: dict[str, Any] = resp.json()
        except ValueError as exc:
            raise EpicError(
                f"Epic Games returned an unreadable answer ({resp.status_code})."
            ) from exc
        if resp.status_code >= 500:
            raise EpicError(f"Epic Games is having trouble ({resp.status_code}): try again later.")
        if payload.get("errorCode") or resp.status_code >= 400:
            raise _sign_in_error(payload, form["grant_type"])
        try:
            return EpicSession(
                access_token=payload["access_token"],
                refresh_token=payload["refresh_token"],
                account_id=payload["account_id"],
                display_name=payload.get("displayName"),
                expires_at=time.time() + float(payload.get("expires_in") or 0),
            )
        except KeyError as exc:
            raise EpicError("Epic Games did not return a sign-in.") from exc

    def sign_in(self, authorization_code: str) -> EpicSession:
        """Trade the one-time code from Epic's page for a token pair."""
        code = extract_authorization_code(authorization_code)
        return self._token({"grant_type": "authorization_code", "code": code})

    def refresh(self, refresh_token: str) -> EpicSession:
        """A fresh token pair from the saved refresh token. Epic replaces the
        refresh token each time, so the caller must save the new one."""
        return self._token({"grant_type": "refresh_token", "refresh_token": refresh_token})

    # ------------------------------------------------------------ library
    def _get(self, url: str, access_token: str, params: dict[str, str] | None = None) -> Any:
        try:
            resp = self.session.get(
                url,
                params=params,
                headers={"Authorization": f"bearer {access_token}"},
                timeout=_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise EpicError(f"Could not reach Epic Games: {exc}") from exc
        if resp.status_code == 401:
            raise EpicSignInExpired("Epic Games no longer accepts this sign-in: connect again.")
        if resp.status_code >= 400:
            raise EpicError(f"Epic Games refused the request ({resp.status_code}).")
        try:
            return resp.json()
        except ValueError as exc:
            raise EpicError("Epic Games returned an unreadable answer.") from exc

    def get_library_items(self, access_token: str) -> list[dict]:
        """Every entitlement in the library (games, their DLC, engine assets):
        namespace, catalogItemId and appName, but no titles. Paged by cursor."""
        records: list[dict] = []
        params = {"includeMetadata": "true"}
        for _ in range(200):  # a page is hundreds of records: this is a runaway guard
            page = self._get(_LIBRARY_URL, access_token, params)
            records.extend(page.get("records") or [])
            cursor = (page.get("responseMetadata") or {}).get("nextCursor")
            if not cursor:
                break
            params = {"includeMetadata": "true", "cursor": cursor}
        return [
            r
            for r in records
            if r.get("catalogItemId")
            and r.get("namespace")
            and r.get("appName")
            and r["namespace"] not in _SKIPPED_NAMESPACES
            and r.get("sandboxType") != "PRIVATE"
        ]

    def get_playtime(self, access_token: str, account_id: str) -> dict[str, int] | None:
        """Seconds played per appName. None when Epic won't say: playtime is an
        extra, not worth failing a sync over."""
        try:
            rows = self._get(_PLAYTIME_URL.format(account_id=account_id), access_token)
        except EpicSignInExpired:
            raise
        except EpicError:
            return None
        played: dict[str, int] = {}
        for row in rows if isinstance(rows, list) else []:
            try:
                played[str(row["artifactId"])] = int(row["totalTime"])
            except (KeyError, TypeError, ValueError):
                continue
        return played

    def get_catalog_items(
        self, access_token: str, namespace: str, ids: list[str]
    ) -> dict[str, dict]:
        """Catalog details (title, description, developer, artwork, categories)
        of some items in one namespace, keyed by catalog item id."""
        params: list[tuple[str, str]] = [("id", i) for i in ids]
        params += [
            ("includeDLCDetails", "true"),
            ("includeMainGameDetails", "true"),
            ("country", "US"),
            ("locale", "en-US"),
        ]
        try:
            resp = self.session.get(
                _CATALOG_URL.format(namespace=namespace),
                params=params,
                headers={"Authorization": f"bearer {access_token}"},
                timeout=_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise EpicError(f"Could not reach Epic Games: {exc}") from exc
        if resp.status_code >= 400:
            return {}
        try:
            payload = resp.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def get_catalog(self, access_token: str, items: list[tuple[str, str]]) -> dict[str, dict]:
        """Catalog details for (namespace, catalog item id) pairs, one request
        per namespace (a game and its DLC share one), several at a time."""
        by_namespace: dict[str, list[str]] = {}
        for namespace, item_id in items:
            by_namespace.setdefault(namespace, []).append(item_id)
        found: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=_CATALOG_CONCURRENCY) as pool:
            for result in pool.map(
                lambda entry: self.get_catalog_items(access_token, entry[0], entry[1]),
                by_namespace.items(),
            ):
                found.update(result)
        return found


def _sign_in_error(payload: dict[str, Any], grant_type: str) -> EpicError:
    code = str(payload.get("errorCode") or "")
    if code.endswith("corrective_action_required"):
        return EpicError(
            "Epic Games needs you to do something on your account first (accept new terms, "
            f"say). Open {payload.get('continuationUrl') or 'epicgames.com'}, then connect again."
        )
    if grant_type == "authorization_code":
        return EpicError(
            "Epic Games did not accept that code. Codes work once and only for a few "
            "minutes: open the sign-in page again and paste the new code right away."
        )
    return EpicSignInExpired("Your Epic Games sign-in has expired: connect Epic Games again.")


def is_game(item: dict) -> bool:
    """Whether a catalog item is a game to track, not DLC, an add-on or an
    engine asset."""
    if item.get("mainGameItem"):
        return False
    categories = {
        str(c.get("path") or "").lower().split("/", 1)[0] for c in item.get("categories") or []
    }
    return not categories & _NON_GAME_CATEGORIES


def art_urls(item: dict) -> dict[AssetKind, str]:
    """The catalog's artwork by the slot it fills: portrait box art for the
    cover, the wide box art for the banner, and the logo."""
    images = {
        str(i.get("type")): str(i.get("url"))
        for i in item.get("keyImages") or []
        if i.get("type") and i.get("url")
    }
    picks: dict[AssetKind, tuple[str, ...]] = {
        "key_art": ("DieselGameBoxTall", "OfferImageTall", "Thumbnail"),
        "banner": ("DieselGameBox", "OfferImageWide", "DieselStoreFrontWide"),
        "logo": ("DieselGameBoxLogo",),
    }
    return {
        slot: next(images[n] for n in names if n in images)
        for slot, names in picks.items()
        if any(n in images for n in names)
    }
