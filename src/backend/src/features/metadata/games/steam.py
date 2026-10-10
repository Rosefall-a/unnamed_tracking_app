"""
Steam Storefront API client.

The Steam Storefront API is unofficial/undocumented but widely used.
No API key is required. Docs (community-maintained):
https://wiki.teamfortress.com/wiki/User:RJackson/StorefrontAPI

Endpoints used here:
- App details:  https://store.steampowered.com/api/appdetails
- App list:     https://api.steampowered.com/ISteamApps/GetAppList/v2/
- Featured:     https://store.steampowered.com/api/featuredcategories
- Search:       https://store.steampowered.com/api/storesearch
"""

import html
import re
import threading
import time

import requests

# a Steam Web API key is always exactly 32 hex characters — distinct enough
# from a profile URL/vanity name/SteamID64 to tell the two apart
# automatically, so the two credential fields don't need to be entered in
# any particular order
_API_KEY_PATTERN = re.compile(r"^[0-9A-Fa-f]{32}$")


def looks_like_api_key(value: str) -> bool:
    return bool(_API_KEY_PATTERN.fullmatch(value.strip()))


BASE_URL = "https://store.steampowered.com/api"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SteamDataFetcher/1.0)"})

# official Steam Web API — needs a per-user API key + SteamID64
# (developer.steamcommunity.com/apikey), separate from the unauthenticated
# Storefront endpoints above
_WEB_API_BASE = "https://api.steampowered.com"


class SteamLibraryError(RuntimeError):
    """Raised when the Steam Web API rejects a library-sync call."""


_PRIVATE_DETAILS = (
    "Steam is not sharing this account's game details. In Steam, set Profile > "
    "Privacy Settings > Game details to Public, then refresh."
)
_PRIVATE_LIBRARY = (
    "Steam did not share this account's games. In Steam, set Profile > Privacy "
    "Settings > Game details to Public, check that the profile ID is your own "
    "account, then try again."
)


# SteamID64 = this base + the 32-bit account number that SteamID2
# ("STEAM_0:Y:Z", account = Z*2+Y) and SteamID3 ("[U:1:N]") spell differently
_STEAMID64_BASE = 76561197960265728
_PROFILE_LINK = re.compile(r"steamcommunity\.com/(id|profiles)/([^/?#\s]+)", re.IGNORECASE)
_STEAMID2 = re.compile(r"^STEAM_[0-5]:([01]):(\d+)$", re.IGNORECASE)
_STEAMID3 = re.compile(r"^\[?U:1:(\d+)\]?$", re.IGNORECASE)


def parse_steam_identifier(identifier: str) -> str:
    """What people paste as their Steam profile, reduced to a SteamID64 when it
    already says which account it is, else to the vanity name to look up: a
    full profile link (steamcommunity.com/id/name or /profiles/7656...), a
    SteamID2 or SteamID3 as shown by sites like steamid.io, a bare SteamID64,
    or a bare vanity name."""
    value = identifier.strip()
    link = _PROFILE_LINK.search(value)
    if link:
        value = link.group(2)
    steamid2 = _STEAMID2.match(value)
    if steamid2:
        return str(_STEAMID64_BASE + int(steamid2.group(2)) * 2 + int(steamid2.group(1)))
    steamid3 = _STEAMID3.match(value)
    if steamid3:
        return str(_STEAMID64_BASE + int(steamid3.group(1)))
    return value


def resolve_steam_id(identifier: str, api_key: str) -> str:
    """Every Steam Web API library call needs a numeric SteamID64 — the API
    key alone only identifies the calling app, not whose library to fetch.
    Takes the profile link, a vanity name (the part after
    steamcommunity.com/id/), or a SteamID in any of its usual spellings."""
    vanity = parse_steam_identifier(identifier)
    if vanity.isdigit() and len(vanity) == 17:
        return vanity
    if not vanity:
        raise SteamLibraryError("Enter your Steam profile ID or SteamID64.")
    try:
        resp = SESSION.get(
            f"{_WEB_API_BASE}/ISteamUser/ResolveVanityURL/v1/",
            params={"key": api_key, "vanityurl": vanity},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise SteamLibraryError(f"Could not reach Steam: {exc}") from exc
    if resp.status_code >= 400:
        raise SteamLibraryError(f"Steam rejected the profile lookup ({resp.status_code}).")
    try:
        payload = resp.json().get("response", {})
    except ValueError as exc:
        raise SteamLibraryError("Steam returned invalid JSON.") from exc
    if payload.get("success") != 1 or not payload.get("steamid"):
        raise SteamLibraryError("Could not resolve that Steam profile URL/vanity name/ID.")
    return str(payload["steamid"])


def get_owned_games(steam_id: str, api_key: str) -> list[dict]:
    """The caller's owned-games library. It needs the profile's game details
    to be public: Steam then answers with an empty `response` (no game count,
    no games) instead of an error, which is reported here rather than read as
    an empty library."""
    try:
        resp = SESSION.get(
            f"{_WEB_API_BASE}/IPlayerService/GetOwnedGames/v1/",
            params={
                "key": api_key,
                "steamid": steam_id,
                "include_appinfo": "1",
                "include_played_free_games": "1",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        raise SteamLibraryError(f"Could not reach Steam: {exc}") from exc
    if resp.status_code in (401, 403):
        raise SteamLibraryError("Steam rejected the API key.")
    if resp.status_code >= 400:
        raise SteamLibraryError(f"Steam library request failed ({resp.status_code}).")
    try:
        payload = resp.json().get("response", {})
    except ValueError as exc:
        raise SteamLibraryError("Steam returned invalid JSON.") from exc
    if "games" not in payload and "game_count" not in payload:
        raise SteamLibraryError(_PRIVATE_LIBRARY)
    return payload.get("games", [])


def get_player_summary(steam_id: str, api_key: str) -> dict:
    """The account's public persona name + avatar, shown in Settings so a
    connected Steam account reads as "who", not just a green dot. Best-effort
    — a private profile can return an empty player list rather than erroring."""
    try:
        resp = SESSION.get(
            f"{_WEB_API_BASE}/ISteamUser/GetPlayerSummaries/v2/",
            params={"key": api_key, "steamids": steam_id},
            timeout=15,
        )
    except requests.RequestException:
        return {}
    if resp.status_code >= 400:
        return {}
    try:
        players = resp.json().get("response", {}).get("players", [])
    except ValueError:
        return {}
    return players[0] if players else {}


_BUSY = frozenset({429, 500, 502, 503, 504})
_TRIES = 3


def _web_api_get(url: str, params: dict[str, str]) -> requests.Response:
    """GET that tries again, a little later each time, when Steam says it is
    busy. A big library makes over a thousand of these calls, and Steam answers
    a burst of them with 429; treating that as a real answer is how a game ends
    up with every achievement locked."""
    resp = SESSION.get(url, params=params, timeout=20)
    for attempt in range(1, _TRIES):
        if resp.status_code not in _BUSY:
            break
        try:
            delay = float(resp.headers.get("Retry-After", ""))
        except ValueError:
            delay = 2.0**attempt
        time.sleep(min(delay, 8.0))
        resp = SESSION.get(url, params=params, timeout=20)
    return resp


def get_schema_for_game(api_key: str, app_id: int) -> dict[str, dict]:
    """Achievement definitions (display name/description/icons) for one
    app, keyed by their internal `apiname` — `GetPlayerAchievements` below
    only returns which ones are unlocked, not what they mean."""
    try:
        resp = _web_api_get(
            f"{_WEB_API_BASE}/ISteamUserStats/GetSchemaForGame/v2/",
            {"key": api_key, "appid": str(app_id)},
        )
    except requests.RequestException as exc:
        raise SteamLibraryError(f"Could not reach Steam: {exc}") from exc
    if resp.status_code >= 400:
        raise SteamLibraryError(f"Steam schema request failed ({resp.status_code}).")
    try:
        achievements = (
            resp.json().get("game", {}).get("availableGameStats", {}).get("achievements", [])
        )
    except ValueError as exc:
        raise SteamLibraryError("Steam returned invalid JSON.") from exc
    return {entry["name"]: entry for entry in achievements if entry.get("name")}


def _xml_text(tag: str, block: str) -> str | None:
    match = re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", block, re.S)
    return html.unescape(match.group(1)).strip() if match else None


# Steam rate-limits its community pages, and a refresh asks for one per game
# with several in flight at once, so requests to it are spaced out through one
# lock and retried when Steam says to slow down. Without this most of a big
# library's requests were refused, and a refusal looks like "no descriptions".
_COMMUNITY_LOCK = threading.Lock()
_COMMUNITY_MIN_GAP = 0.6  # seconds between requests
_COMMUNITY_RETRIES = 4
_community_last_request = 0.0


def _community_get(url: str, params: dict[str, str]) -> requests.Response:
    global _community_last_request  # pylint: disable=global-statement
    resp = None
    for attempt in range(_COMMUNITY_RETRIES):
        with _COMMUNITY_LOCK:
            wait = _COMMUNITY_MIN_GAP - (time.monotonic() - _community_last_request)
            if wait > 0:
                time.sleep(wait)
            _community_last_request = time.monotonic()
            resp = SESSION.get(url, params=params, timeout=20)
        if resp.status_code not in (429, 503) or attempt == _COMMUNITY_RETRIES - 1:
            break
        try:
            delay = float(resp.headers.get("Retry-After", ""))
        except ValueError:
            delay = 2.0 ** (attempt + 1)
        time.sleep(min(delay, 30.0))
    assert resp is not None
    return resp


def get_community_descriptions(steam_id: str, app_id: int) -> dict[str, str]:
    """Each achievement's description, keyed by its internal `apiname` in
    lowercase (the feed and the schema don't agree on case: `ach00` against
    `ACH00`, so look it up with `.lower()`), from
    Steam's public community stats feed for this player. The Web API leaves out
    the description of a hidden achievement, but this feed (what Steam's own
    profile page shows) has it. It needs the player's game details to be
    public; when they aren't, or on any failure, the result is just empty: the
    descriptions are an extra, not worth failing a refresh over."""
    try:
        resp = _community_get(
            f"https://steamcommunity.com/profiles/{steam_id}/stats/{app_id}/",
            {"xml": "1", "l": "english"},
        )
        if resp.status_code >= 400 or len(resp.content) > 2_000_000:
            return {}
        body = resp.text
    except requests.RequestException:
        return {}
    descriptions: dict[str, str] = {}
    for block in re.findall(r'<achievement closed="\d">(.*?)</achievement>', body, re.S):
        api_name = _xml_text("apiname", block)
        description = _xml_text("description", block)
        if api_name and description:
            descriptions[api_name.lower()] = description
    if not descriptions and "<achievement" not in body:
        # Some games get the profile web page here instead of the XML. It has
        # no internal names, so each description is keyed by the display name
        # ("name:" + lowercase). It lists every achievement you have unlocked,
        # hidden ones included, but only a "+N hidden" count for the locked
        # ones: Steam does not reveal those anywhere until you unlock them.
        for title, description in re.findall(
            r"<h3[^>]*>(.*?)</h3>\s*<h5[^>]*>(.*?)</h5>", body, re.S
        ):
            title, description = html.unescape(title).strip(), html.unescape(description).strip()
            if title and description:
                descriptions[f"name:{title.lower()}"] = description
    return descriptions


def get_global_percentages(app_id: int) -> dict[str, float]:
    """The share of all players who have each achievement, keyed by its
    internal `apiname`. A public call (no key needed); an app without
    achievements, or any failure, is just an empty result: the percentages are
    an extra, not worth failing a refresh over."""
    try:
        resp = SESSION.get(
            f"{_WEB_API_BASE}/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/",
            params={"gameid": str(app_id)},
            timeout=20,
        )
        if resp.status_code >= 400:
            return {}
        entries = resp.json().get("achievementpercentages", {}).get("achievements", [])
    except (requests.RequestException, ValueError):
        return {}
    percentages: dict[str, float] = {}
    for entry in entries:
        try:
            percentages[entry["name"]] = round(float(entry["percent"]), 2)
        except (KeyError, TypeError, ValueError):
            continue
    return percentages


def get_player_achievements(
    steam_id: str, api_key: str, app_id: int, strict: bool = False
) -> list[dict] | None:
    """Which achievements this player has unlocked for one app. Many games
    have no achievement schema at all — that's a normal empty result, not
    an error. None means Steam did not answer (busy, or access refused), which
    is not the same as nothing being unlocked."""
    try:
        resp = _web_api_get(
            f"{_WEB_API_BASE}/ISteamUserStats/GetPlayerAchievements/v1/",
            # `l` makes Steam include each achievement's name and description,
            # which for a hidden one you've unlocked is the only place the
            # description shows up: the schema leaves it out
            {"key": api_key, "steamid": steam_id, "appid": str(app_id), "l": "english"},
        )
    except requests.RequestException as exc:
        raise SteamLibraryError(f"Could not reach Steam: {exc}") from exc
    try:
        payload = resp.json().get("playerstats", {})
    except ValueError:
        payload = {}
    # a private profile says so in its answer; without this it reads as "this
    # player has unlocked nothing". A bad key or an app without achievements
    # also fails, with no such message, and stays an empty result.
    if strict and "not public" in str(payload.get("error", "")).lower():
        raise SteamLibraryError(_PRIVATE_DETAILS)
    if resp.status_code in _BUSY or resp.status_code in (401, 403):
        return None
    if resp.status_code >= 400 or not payload.get("success"):
        return []
    return payload.get("achievements", [])


def get_app_details(app_id: int, country: str = "us", currency: str = "USD") -> dict | None:
    """
    Fetch full details for a single app (game/DLC/etc) by its Steam AppID.
    Returns the 'data' dict on success, or None if the app has no store page.
    """
    params: dict[str, str | int] = {"appids": app_id, "cc": country, "l": "en"}
    resp = SESSION.get(f"{BASE_URL}/appdetails", params=params, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    app_data = payload.get(str(app_id))
    if not app_data or not app_data.get("success"):
        return None
    return app_data["data"]


def get_app_details_bulk(app_ids: list[int], delay: float = 1.0) -> dict[int, dict]:
    """
    Fetch details for multiple AppIDs one at a time (the endpoint only
    reliably supports a single appid per request). `delay` avoids
    rate-limiting/soft bans from Steam.
    """
    results = {}
    for app_id in app_ids:
        data = get_app_details(app_id)
        if data:
            results[app_id] = data
        time.sleep(delay)
    return results


def search_store(term: str, country: str = "us") -> list[dict]:
    """Search the Steam store by keyword."""
    params = {"term": term, "cc": country, "l": "en"}
    resp = SESSION.get(f"{BASE_URL}/storesearch", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])
