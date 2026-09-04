from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Literal

from src.core.config import settings
from src.core.crypto import decrypt_secret
from src.features.metadata.games import steam
from src.features.metadata.games.giant_bomb import GiantBombClient, GiantBombError
from src.features.metadata.games.hltb import HLTBClient, HLTBError
from src.features.metadata.games.igdb import IGDBClient, IGDBError
from src.features.metadata.games.retroachievements import RetroAchievementsClient, RetroAchievementsError
from src.features.metadata.games.screenscraper import ScreenScraperClient, ScreenScraperError
from src.features.metadata.games.steam_grid_db import SteamGridDBClient, SteamGridDBError

if TYPE_CHECKING:
    from src.database.models.user import User


def _parse_release_date(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    for date_format in ("%d %b, %Y", "%b %d, %Y", "%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _blank_result(provider: str, provider_id: str, title: str) -> dict[str, Any]:
    """A normalized result dict with every field present — providers fill
    in what they know and leave the rest at these defaults."""
    return {
        "provider": provider,
        "provider_id": provider_id,
        "title": title,
        "description": None,
        "release_date": None,
        "developer": None,
        "publisher": None,
        "age_rating": None,
        "tags": [],
        "features": [],
        "links": [],
        "key_art_url": None,
        "key_art_urls": [],
        "banner_url": None,
        "banner_urls": [],
        "logo_url": None,
        "logo_urls": [],
        "icon_url": None,
        "icon_urls": [],
        "time_to_beat_hours": None,
    }


def _steam_result(item: dict[str, Any], details: dict[str, Any] | None) -> dict[str, Any]:
    details = details or {}
    app_id = int(str(item.get("id") or details.get("steam_appid")))
    title = details.get("name") or item.get("name") or ""
    genres = [entry["description"] for entry in details.get("genres", []) if entry.get("description")]
    features = [entry["description"] for entry in details.get("categories", []) if entry.get("description")]
    required_age = details.get("required_age")
    result = _blank_result("Steam", str(app_id), title)
    result.update(
        {
            # "About This Game" (rich HTML, keeps the dev's screenshots/gifs) over
            # the plain-text short_description used for search-result blurbs
            "description": details.get("about_the_game") or details.get("detailed_description")
            or details.get("short_description") or None,
            "release_date": _parse_release_date(details.get("release_date", {}).get("date")),
            "developer": ", ".join(details.get("developers", [])) or None,
            "publisher": ", ".join(details.get("publishers", [])) or None,
            "age_rating": f"{required_age}+" if required_age else None,
            "tags": genres,
            "features": features,
            "links": [{"label": "Steam Store", "url": f"https://store.steampowered.com/app/{app_id}/"}],
            "key_art_url": details.get("header_image") or item.get("tiny_image"),
            "banner_url": details.get("background_raw") or details.get("header_image"),
        }
    )
    return result


def _titles_match(a: str, b: str) -> bool:
    normalize = lambda s: "".join(ch.lower() for ch in s if ch.isalnum())  # noqa: E731
    return normalize(a) == normalize(b) and bool(normalize(a))


def _merge_or_append(results: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    """Primary providers can turn up a game already found by an earlier
    provider (e.g. RetroAchievements finding the same title Steam did) —
    merge onto the existing entry (filling only blanks) instead of creating
    a visually duplicate second result."""
    for existing in results:
        if _titles_match(existing["title"], candidate["title"]):
            for key, value in candidate.items():
                if key in ("provider", "provider_id", "title", "links"):
                    continue
                if not existing.get(key) and value:
                    existing[key] = value
            existing["links"].extend(candidate.get("links", []))
            return
    results.append(candidate)


# ---------------------------------------------------------------------------
# Provider registry — each provider is a small `run()` function with the
# same signature, registered once below. `search_game_metadata` just walks
# `preferences["provider_order"]` and calls whichever ones are available;
# adding a provider means adding one client module + one entry here, not
# touching the orchestration loop.
# ---------------------------------------------------------------------------


@dataclass
class ProviderContext:
    user: "User | None"
    steamgriddb_api_key: str | None


ProviderRun = Callable[[str, int, ProviderContext, list[dict[str, Any]]], list[dict[str, Any]] | None]

# hard wall-clock cap per enrichment provider — independent of whatever
# timeout the provider's own HTTP client sets internally, since that can't
# always be trusted to fire (see search_game_metadata's enrichment loop)
ENRICHMENT_TIMEOUT_SECONDS = 20


@dataclass
class ProviderSpec:
    name: str
    kind: Literal["primary", "enrichment"]
    available: Callable[[ProviderContext], bool]
    run: ProviderRun


def _run_steam(query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    del ctx, existing
    found: list[dict[str, Any]] = []
    for item in steam.search_store(query)[:limit]:
        app_id = item.get("id")
        if app_id is None:
            continue
        details = steam.get_app_details(int(app_id)) if app_id else None
        if details and details.get("type") not in (None, "game"):
            continue
        found.append(_steam_result(item, details))
    return found


def _run_steamgriddb(query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]) -> None:
    del query, limit
    assert ctx.steamgriddb_api_key  # guarded by `available`
    client = SteamGridDBClient(api_key=ctx.steamgriddb_api_key)
    for result in existing:
        try:
            _add_steamgriddb_art(result, client)
        except (SteamGridDBError, TypeError, ValueError):
            continue


def _add_steamgriddb_art(result: dict[str, Any], client: SteamGridDBClient) -> None:
    # prefer an exact Steam-app-ID lookup over a fuzzy name search — a
    # name match for "Baldur's Gate 3" can just as easily land on a fan
    # toolkit or DLC bundle that happens to rank first on SteamGridDB
    match: dict[str, Any] | None = None
    if result.get("provider") == "Steam" and result.get("provider_id"):
        try:
            match = client.get_game_by_steam_appid(int(result["provider_id"]))
        except (SteamGridDBError, TypeError, ValueError):
            match = None
    if not match:
        match = client.get_game_by_name(result["title"])
    if not match:
        return
    game_id = match.get("id") or match.get("game_id")
    if game_id is None:
        return
    result["links"].append({"label": "SteamGridDB", "url": f"https://www.steamgriddb.com/game/{game_id}"})
    # grids are filtered to portrait card styles only — 600x900 is Steam's
    # own vertical capsule, 660x930 is GOG Galaxy 2.0's cover size. Without
    # this filter SteamGridDB can just as easily return a 460x215 landscape
    # grid, which looks wrong in a vertical cover slot.
    image_fields: dict[str, tuple[str, str, str | None]] = {
        "grids": ("key_art_urls", "key_art_url", "600x900,660x930"),
        "heroes": ("banner_urls", "banner_url", None),
        "logos": ("logo_urls", "logo_url", None),
        "icons": ("icon_urls", "icon_url", None),
    }

    def _fetch_images(image_type: str, dimensions: str | None) -> list[Any]:
        return client.get_game_images(game_id, image_type=image_type, dimensions=dimensions, limit=10)

    # 4 independent image-type lookups — run concurrently rather than one
    # HTTP round-trip after another, since each is its own request with no
    # shared state until results are assembled below
    with ThreadPoolExecutor(max_workers=len(image_fields)) as image_executor:
        image_results = {
            image_type: future.result()
            for image_type, future in {
                image_type: image_executor.submit(_fetch_images, image_type, dimensions)
                for image_type, (_, _, dimensions) in image_fields.items()
            }.items()
        }
    for image_type, (list_field, default_field, dimensions) in image_fields.items():
        images = image_results[image_type]
        # highest community score first, so the default pick (urls[0]) is
        # the best-rated option rather than whatever order the API sent
        images.sort(key=lambda img: img.score if img.score is not None else -1, reverse=True)
        urls = [image.url for image in images if image.url][:10]
        result[list_field] = urls
        if urls:
            result[default_field] = urls[0]


def _run_igdb(query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    del ctx, existing
    client = IGDBClient(client_id=settings.IGDB_CLIENT_ID, client_secret=settings.IGDB_CLIENT_SECRET)
    found: list[dict[str, Any]] = []
    for game in client.search(query, limit=limit):
        result = _blank_result("IGDB", str(game.get("id", "")), game.get("name", ""))
        result.update(
            {
                "description": game.get("summary"),
                "release_date": _parse_release_date(game.get("release_date")),
                "developer": game.get("developer"),
                "publisher": game.get("publisher"),
                "tags": game.get("genres") or [],
                "key_art_url": game.get("cover_url"),
                "links": [{"label": "IGDB", "url": game["url"]}] if game.get("url") else [],
            }
        )
        found.append(result)
    return found


def _run_retroachievements(
    query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    del existing
    assert ctx.user and ctx.user.retroachievements_api_key
    client = RetroAchievementsClient(api_key=ctx.user.retroachievements_api_key)
    found: list[dict[str, Any]] = []
    for game in client.search_games(query, limit=limit):
        result = _blank_result("RetroAchievements", str(game.get("id", "")), game.get("title", ""))
        result.update(
            {
                "tags": [game["console"]] if game.get("console") else [],
                "key_art_url": game.get("image_icon_url"),
                "links": [{"label": "RetroAchievements", "url": game["url"]}] if game.get("url") else [],
            }
        )
        found.append(result)
    return found


def _run_giant_bomb(
    query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    del ctx, existing
    assert ctx.user and ctx.user.giantbomb_api_key
    client = GiantBombClient(api_key=ctx.user.giantbomb_api_key)
    found: list[dict[str, Any]] = []
    for game in client.search(query, limit=limit):
        result = _blank_result("GiantBomb", str(game.get("id", "")), game.get("name", ""))
        result.update(
            {
                "description": game.get("deck"),
                "release_date": _parse_release_date(game.get("original_release_date")),
                "key_art_url": game.get("image_url"),
                "links": [{"label": "Giant Bomb", "url": game["url"]}] if game.get("url") else [],
            }
        )
        found.append(result)
    return found


def _run_screenscraper(query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]) -> None:
    del query, limit
    assert ctx.user and ctx.user.screenscraper_ssid and ctx.user.screenscraper_sspassword
    assert settings.SCREENSCRAPER_DEVID and settings.SCREENSCRAPER_DEVPASSWORD
    client = ScreenScraperClient(
        devid=settings.SCREENSCRAPER_DEVID,
        devpassword=settings.SCREENSCRAPER_DEVPASSWORD,
        ssid=ctx.user.screenscraper_ssid,
        sspassword=decrypt_secret(ctx.user.screenscraper_sspassword),
    )
    for result in existing:
        try:
            art = client.find_art(result["title"])
        except (ScreenScraperError, TypeError, ValueError):
            continue
        if art is None:
            continue
        if art.get("box_art_url") and not result.get("key_art_url"):
            result["key_art_url"] = art["box_art_url"]
        if art.get("screenshot_url") and not result.get("banner_url"):
            result["banner_url"] = art["screenshot_url"]


def _run_hltb(query: str, limit: int, ctx: ProviderContext, existing: list[dict[str, Any]]) -> None:
    del query, limit, ctx
    client = HLTBClient()
    for result in existing:
        if result.get("time_to_beat_hours") is not None:
            continue
        try:
            hours = client.find_time_to_beat(result["title"])
        except (HLTBError, TypeError, ValueError):
            continue
        if hours is not None:
            result["time_to_beat_hours"] = hours


PROVIDERS: dict[str, ProviderSpec] = {
    "Steam": ProviderSpec("Steam", "primary", lambda ctx: True, _run_steam),
    "SteamGridDB": ProviderSpec(
        "SteamGridDB", "enrichment", lambda ctx: bool(ctx.steamgriddb_api_key), _run_steamgriddb
    ),
    "IGDB": ProviderSpec(
        "IGDB", "primary", lambda ctx: bool(settings.IGDB_CLIENT_ID and settings.IGDB_CLIENT_SECRET), _run_igdb
    ),
    "RetroAchievements": ProviderSpec(
        "RetroAchievements",
        "primary",
        lambda ctx: bool(ctx.user and ctx.user.retroachievements_api_key),
        _run_retroachievements,
    ),
    "GiantBomb": ProviderSpec(
        "GiantBomb", "primary", lambda ctx: bool(ctx.user and ctx.user.giantbomb_api_key), _run_giant_bomb
    ),
    "ScreenScraper": ProviderSpec(
        "ScreenScraper",
        "enrichment",
        lambda ctx: bool(
            settings.SCREENSCRAPER_DEVID
            and settings.SCREENSCRAPER_DEVPASSWORD
            and ctx.user
            and ctx.user.screenscraper_ssid
            and ctx.user.screenscraper_sspassword
        ),
        _run_screenscraper,
    ),
    "HowLongToBeat": ProviderSpec("HowLongToBeat", "enrichment", lambda ctx: True, _run_hltb),
}

# fields a user can opt out of saving from a metadata search result — the
# `save_<field>` name is how they're keyed in UserScanSettings/the API
_GATED_FIELDS: dict[str, tuple[str, Any]] = {
    "developer": ("save_developer", None),
    "publisher": ("save_publisher", None),
    "series": ("save_series", None),
    "tags": ("save_tags", []),
    "features": ("save_features", []),
    "description": ("save_description", None),
    "age_rating": ("save_age_rating", None),
    "release_date": ("save_release_date", None),
    "time_to_beat_hours": ("save_time_to_beat", None),
}
DEFAULT_PROVIDER_ORDER = [
    "Steam",
    "IGDB",
    "GiantBomb",
    "RetroAchievements",
    "SteamGridDB",
    "ScreenScraper",
    "HowLongToBeat",
]
DEFAULT_PREFERENCES: dict[str, Any] = {
    "provider_order": DEFAULT_PROVIDER_ORDER,
    **{flag: True for flag, _ in _GATED_FIELDS.values()},
}


def _strip_unsaved_fields(results: list[dict[str, Any]], preferences: dict[str, Any]) -> None:
    for result in results:
        for field, (flag, cleared_value) in _GATED_FIELDS.items():
            if not preferences.get(flag, True):
                result[field] = cleared_value


def search_game_metadata(
    query: str,
    limit: int = 8,
    steamgriddb_api_key: str | None = None,
    preferences: dict[str, Any] | None = None,
    user: "User | None" = None,
) -> dict[str, Any]:
    """Search configured providers and return normalized creation-form data.

    `preferences` (from UserScanSettings) drives which providers run and in
    what order (`provider_order`), and which normalized fields survive into
    the result (`save_<field>` toggles). Each provider in `PROVIDERS` is
    either "primary" (produces base results, merged by title into existing
    ones) or "enrichment" (layers data — usually art — onto results already
    found, a no-op if nothing exists yet to enrich). A provider missing its
    credentials is silently skipped, not an error — `steamgriddb_configured`
    stays as the one explicit flag the frontend already depends on for its
    "add a key" prompt; new providers surface their configured-ness via
    `GET /api/settings/provider-credentials` instead.
    """
    preferences = preferences or DEFAULT_PREFERENCES
    provider_order = preferences.get("provider_order") or DEFAULT_PROVIDER_ORDER
    ctx = ProviderContext(user=user, steamgriddb_api_key=steamgriddb_api_key)

    results: list[dict[str, Any]] = []
    provider_errors: list[str] = []
    providers_used: list[str] = []

    available_specs = [
        PROVIDERS[name] for name in provider_order if PROVIDERS.get(name) and PROVIDERS[name].available(ctx)
    ]
    primary_specs = [spec for spec in available_specs if spec.kind == "primary"]
    enrichment_specs = [spec for spec in available_specs if spec.kind == "enrichment"]

    # Primary providers are independent of each other (none reads another's
    # results), so they're the real bottleneck when run one at a time —
    # these are all sync `requests` clients, hence a thread pool rather than
    # asyncio. Enrichment providers run after, sequentially, since they need
    # the merged primary results to already exist (e.g. SteamGridDB matching
    # against a title Steam just found).
    def _call_primary(spec: ProviderSpec) -> tuple[ProviderSpec, list[dict[str, Any]] | None, str | None]:
        try:
            return spec, spec.run(query, limit, ctx, results), None
        except Exception as exc:  # noqa: BLE001 — one provider's failure shouldn't sink the search
            return spec, None, str(exc)

    if primary_specs:
        with ThreadPoolExecutor(max_workers=len(primary_specs)) as executor:
            for spec, outcome, error in executor.map(_call_primary, primary_specs):
                if error is not None:
                    provider_errors.append(f"{spec.name}: {error}")
                    continue
                if outcome:
                    for candidate in outcome:
                        _merge_or_append(results, candidate)
                providers_used.append(spec.name)

    # Enrichment providers (SteamGridDB art, ScreenScraper art, HLTB time-to-
    # beat) are independent of each other — none reads another's output — so
    # there's no reason to run them one after another. SteamGridDB and
    # ScreenScraper can both write art fields on the same result if a result
    # doesn't have art yet; running concurrently means whichever finishes
    # first "wins" that field instead of provider_order deciding it
    # deterministically — an acceptable tradeoff since it only matters when
    # both are configured for the same account, which is rare in practice.
    # Each provider also hits a
    # third-party unofficial endpoint whose own `requests` timeout can't
    # always be trusted to fire (a stalled TCP connection some environments
    # hang on regardless), so each still gets its own thread + hard
    # wall-clock deadline; a timed-out provider's thread is left to finish
    # (or hang) on its own, unwaited (`wait=False`) rather than blocking
    # `ThreadPoolExecutor.__exit__`'s default `shutdown(wait=True)`.
    if enrichment_specs:
        executor = ThreadPoolExecutor(max_workers=len(enrichment_specs))
        futures = {executor.submit(spec.run, query, limit, ctx, results): spec for spec in enrichment_specs}
        for future, spec in futures.items():
            try:
                future.result(timeout=ENRICHMENT_TIMEOUT_SECONDS)
            except FutureTimeoutError:
                provider_errors.append(f"{spec.name}: timed out after {ENRICHMENT_TIMEOUT_SECONDS}s")
                continue
            except Exception as exc:  # noqa: BLE001 — one provider's failure shouldn't sink the search
                provider_errors.append(f"{spec.name}: {exc}")
                continue
            providers_used.append(spec.name)
        executor.shutdown(wait=False)

    _strip_unsaved_fields(results, preferences)

    return {
        "query": query,
        "providers": providers_used,
        "steamgriddb_configured": bool(steamgriddb_api_key),
        "provider_errors": provider_errors,
        "results": results,
    }
