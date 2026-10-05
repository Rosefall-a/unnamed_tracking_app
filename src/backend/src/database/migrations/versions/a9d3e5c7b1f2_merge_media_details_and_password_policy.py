"""Join the media details and password policy migrations.

Both branched from a3f1c7e9d2b4: the games work (hidden achievements, media
titles and dates, file details) and main's password policy. Neither touches
the other's tables, so this only joins the two histories into one head.

revision: a9d3e5c7b1f2
down_revision: c4f7a1d2e6b8, f3b8d5a1c7e2
"""

from collections.abc import Sequence

revision: str = "a9d3e5c7b1f2"
down_revision: str | Sequence[str] | None = ("c4f7a1d2e6b8", "f3b8d5a1c7e2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
