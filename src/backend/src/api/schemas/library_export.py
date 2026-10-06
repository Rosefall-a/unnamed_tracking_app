"""The portable library snapshot shared by manual exports and backups."""

from pydantic import BaseModel

from src.api.schemas.anime import AnimeRead
from src.api.schemas.game import GameRead
from src.api.schemas.movie import MovieRead
from src.api.schemas.tv_show import TVShowRead


class LibraryExport(BaseModel):
    format_version: int = 2
    exported_at: int
    game_count: int
    games: list[GameRead]
    movies: list[MovieRead] = []
    tv_shows: list[TVShowRead] = []
    anime: list[AnimeRead] = []
