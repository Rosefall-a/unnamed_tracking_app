"""An imported score becomes a rating only when it is a real number from 0 to 10.

A file can hold anything in a score cell: NaN or Infinity (which the database
accepts and then breaks every list and stat that reads it), or a number far
outside the scale (which overflows the column and, in an import that commits
once, aborts the whole file). Those become "no rating" or the nearest end of the
scale; the title itself is still imported."""

from decimal import Decimal

_TOP = Decimal(10)
_PLACES = Decimal("0.01")


def clean_rating(value: Decimal | None) -> Decimal | None:
    if value is None or not value.is_finite():
        return None
    return min(max(value, Decimal(0)), _TOP).quantize(_PLACES)
