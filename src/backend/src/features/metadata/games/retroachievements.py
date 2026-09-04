from __future__ import annotations

from typing import Any

import requests


class RetroAchievementsError(RuntimeError):
    """Raised when the RetroAchievements API responds unsuccessfully."""


class RetroAchievementsClient:
    """Minimal client for the RetroAchievements API — retro/console game
    metadata, keyed by a free per-user API key (retroachievements.org
    account settings)."""

    BASE_URL = "https://retroachievements.org/API"

    def __init__(self, api_key: str, *, session: requests.Session | None = None) -> None:
        if not api_key:
            raise RetroAchievementsError("No RetroAchievements API key provided.")
        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, endpoint: str, **params: Any) -> Any:
        params = {**params, "y": self.api_key}
        try:
            response = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=15)
        except requests.RequestException as exc:
            raise RetroAchievementsError(f"Could not reach RetroAchievements: {exc}") from exc

        if response.status_code == 401 or response.status_code == 403:
            raise RetroAchievementsError("RetroAchievements rejected the API key.")
        if response.status_code >= 400:
            raise RetroAchievementsError(f"RetroAchievements request failed ({response.status_code}).")

        try:
            return response.json()
        except ValueError as exc:
            raise RetroAchievementsError("RetroAchievements returned invalid JSON.") from exc

    def validate(self) -> dict[str, Any]:
        """A cheap call used purely to confirm the API key works."""
        payload = self._get("API_GetConsoleIDs.php")
        if not isinstance(payload, list):
            raise RetroAchievementsError("Unexpected response validating the API key.")
        return {"validated": True}

    def search_games(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """RetroAchievements has no free-text game search endpoint — the
        practical approach used by community tools is to pull each
        console's game list and filter client-side. To keep this fast we
        only search a small set of the most common consoles rather than
        all ~100, since scanning every console per query would be slow."""
        if not query.strip():
            return []
        # a representative slice of the most commonly tracked consoles
        console_ids = [1, 2, 3, 4, 7, 8, 11, 12, 15, 18, 21]
        query_lower = query.strip().lower()
        matches: list[dict[str, Any]] = []
        for console_id in console_ids:
            if len(matches) >= limit:
                break
            try:
                games = self._get("API_GetGameList.php", i=console_id)
            except RetroAchievementsError:
                continue
            if not isinstance(games, list):
                continue
            for game in games:
                title = game.get("Title") or ""
                if query_lower not in title.lower():
                    continue
                matches.append(
                    {
                        "id": game.get("ID"),
                        "title": title,
                        "console": game.get("ConsoleName"),
                        "image_icon_url": (
                            f"https://media.retroachievements.org{game['ImageIcon']}"
                            if game.get("ImageIcon")
                            else None
                        ),
                        "url": f"https://retroachievements.org/game/{game['ID']}" if game.get("ID") else None,
                    }
                )
                if len(matches) >= limit:
                    break
        return matches
