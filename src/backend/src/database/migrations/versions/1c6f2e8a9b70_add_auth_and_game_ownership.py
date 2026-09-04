"""add auth tables and game ownership

Revision ID: 1c6f2e8a9b70
Revises: 0284d11effb1
Create Date: 2026-09-02

"""

import time
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from src.core.auth import hash_password, validate_password
from src.core.config import settings

revision: str = "1c6f2e8a9b70"
down_revision: Union[str, None] = "0284d11effb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    connection = op.get_bind()
    username = settings.PRIMARY_USER_USERNAME.strip()
    email = settings.PRIMARY_USER_EMAIL.strip().lower()
    validate_password(settings.PRIMARY_USER_PASSWORD)
    primary_user_id = connection.execute(
        sa.text("SELECT id FROM users WHERE username = :username OR email = :email LIMIT 1"),
        {"username": username, "email": email},
    ).scalar_one_or_none()

    if primary_user_id is None:
        primary_user_id = uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO users (id, username, email, password_hash, is_active, is_admin, created_at, updated_at)
                VALUES (:id, :username, :email, :password_hash, true, true, :created_at, :updated_at)
                """
            ),
            {
                "id": primary_user_id,
                "username": username,
                "email": email,
                "password_hash": hash_password(settings.PRIMARY_USER_PASSWORD),
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            },
        )
    else:
        connection.execute(
            sa.text("UPDATE users SET is_admin = true WHERE id = :id"),
            {"id": primary_user_id},
        )

    op.add_column("games", sa.Column("user_id", sa.UUID(), nullable=True))
    connection.execute(
        sa.text("UPDATE games SET user_id = :user_id WHERE user_id IS NULL"),
        {"user_id": primary_user_id},
    )
    op.alter_column("games", "user_id", nullable=False)
    op.create_index("ix_games_user_id", "games", ["user_id"])
    op.create_foreign_key(
        "fk_games_user_id_users",
        "games",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("revoked_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_user_api_keys_user_id", "user_api_keys", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_api_keys_user_id", table_name="user_api_keys")
    op.drop_table("user_api_keys")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_constraint("fk_games_user_id_users", "games", type_="foreignkey")
    op.drop_index("ix_games_user_id", table_name="games")
    op.drop_column("games", "user_id")
    op.drop_column("users", "is_admin")
