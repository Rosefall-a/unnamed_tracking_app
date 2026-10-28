"""A score in an imported file becomes a rating only when it is a real number
from 0 to 10; the title is imported either way."""

from decimal import Decimal

import pytest

from src.features.imports.ratings import clean_rating
from src.features.imports.yamtrack import _score


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), Decimal("sNaN")])
def test_a_number_that_is_not_a_number_is_no_rating(bad) -> None:
    assert clean_rating(bad) is None


def test_a_score_outside_the_scale_goes_to_the_nearest_end() -> None:
    assert clean_rating(Decimal("50")) == Decimal("10.00")
    assert clean_rating(Decimal("-3")) == Decimal("0.00")


def test_a_normal_score_is_kept() -> None:
    assert clean_rating(Decimal("7.5")) == Decimal("7.50")
    assert clean_rating(None) is None


@pytest.mark.parametrize("cell", ["NaN", "Infinity", "-inf", "abc", ""])
def test_yamtrack_scores_that_are_not_numbers_are_dropped(cell) -> None:
    assert _score(cell) is None


def test_a_yamtrack_score_far_off_the_scale_is_clamped() -> None:
    assert _score("9999") == Decimal("10.00")
