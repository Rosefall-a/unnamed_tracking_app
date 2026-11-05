"""Filling in how long a game takes, for a game already in someone's library.

HowLongToBeat is unofficial and can stop answering at any time, so nothing here
ever clears a time that is already saved. While it is down, IGDB's play times
are used when its keys are saved, and `hltb_error` says what went wrong so the
caller can report it and try the game again on a later run."""

from __future__ import annotations

import asyncio

from src.core.config import settings
from src.database.models.game import Game
from src.features.metadata.games.hltb import TIME_FIELDS, HLTBClient, HLTBError
from src.features.metadata.games.igdb import IGDBClient, IGDBError


class TimesLookup:
    """One per batch of games: it keeps HowLongToBeat's token, and stops asking
    the site for the rest of the batch once it has failed."""

    def __init__(self, igdb_client_id: str | None, igdb_client_secret: str | None) -> None:
        client_id = igdb_client_id or settings.IGDB_CLIENT_ID
        client_secret = igdb_client_secret or settings.IGDB_CLIENT_SECRET
        self._hltb = HLTBClient()
        self._igdb = (
            IGDBClient(client_id=client_id, client_secret=client_secret)
            if client_id and client_secret
            else None
        )
        self.hltb_error: str | None = None

    def find(self, title: str) -> dict[str, float]:
        times: dict[str, float] = {}
        if self.hltb_error is None:
            try:
                # a saved number has to be this game's: a near match is left blank
                times = self._hltb.find_times(title, exact=True)
            except HLTBError as exc:
                self.hltb_error = str(exc)
            except (TypeError, ValueError):
                pass
        if not times and self.hltb_error is not None and self._igdb is not None:
            try:
                times = self._igdb.play_times(title)
            except (IGDBError, TypeError, ValueError):
                pass
        return times


async def fill_times(game: Game, lookup: TimesLookup) -> int:
    """Saves the figures this game has none of, except locked ones. Returns how
    many were saved."""
    if all(getattr(game, field) is not None for field in TIME_FIELDS):
        return 0
    times = await asyncio.to_thread(lookup.find, game.title)
    saved = 0
    for field, value in times.items():
        if getattr(game, field) is None and field not in (game.locked_fields or []):
            setattr(game, field, value)
            saved += 1
    return saved
