"""Library status columns remain importable and preserve their enum contract."""

import pytest
from sqlalchemy import Enum as SQLAlchemyEnum

from src.database.models.movies import Movie, MovieStatus
from src.database.models.tv_show import TVSeason, TVShow, TVShowStatus


@pytest.mark.parametrize(
    ("model", "status_type"),
    [(Movie, MovieStatus), (TVShow, TVShowStatus), (TVSeason, TVShowStatus)],
)
def test_library_status_column_uses_the_library_enum(model, status_type):
    column = model.__table__.c.status
    assert isinstance(column.type, SQLAlchemyEnum)
    assert column.type.enum_class is status_type
    assert column.type.native_enum is False
    assert column.type.length == 30
    assert column.default.arg is status_type.WISHLIST
