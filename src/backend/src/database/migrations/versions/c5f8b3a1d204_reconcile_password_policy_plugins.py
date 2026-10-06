"""Join password policy and plugin-manager upgrade paths without changing data."""

revision = "c5f8b3a1d204"
down_revision = ("b8c7d6e5f403", "c4f7a1d2e6b8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply either missing predecessor before reaching the single successor."""


def downgrade() -> None:
    """Retain predecessor schemas when separating the revision branches."""
