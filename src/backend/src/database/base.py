import time

from sqlalchemy.orm import DeclarativeBase


def unix_timestamp() -> int:
    """Generate integer seconds for BigInteger model defaults and API responses."""
    return int(time.time())


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Every model that inherits from Base is included
    in SQLAlchemy's metadata.
    """
