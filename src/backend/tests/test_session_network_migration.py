"""Reconciled session metadata upgrades preserve existing columns and data."""

from importlib import import_module

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

network_migration = import_module(
    "src.database.migrations.versions.f2a8c9d0e1b2_session_geo_network"
)


@pytest.mark.parametrize("existing", [False, True])
def test_session_network_upgrade_is_safe_with_either_predecessor_schema(existing):
    metadata = sa.MetaData()
    columns = [sa.Column("id", sa.Integer(), primary_key=True)]
    if existing:
        columns.extend(
            [
                sa.Column("geo_network_number", sa.BigInteger()),
                sa.Column("geo_network_organization", sa.String(256)),
            ]
        )
    sessions = sa.Table("user_sessions", metadata, *columns)
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            metadata.create_all(connection)
            values = {"id": 1}
            if existing:
                values.update(geo_network_number=123, geo_network_organization="Existing owner")
            connection.execute(sessions.insert().values(**values))
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                network_migration.upgrade()
                network_migration.upgrade()
                network_migration.downgrade()
            fields = {
                column["name"] for column in sa.inspect(connection).get_columns("user_sessions")
            }
            assert {"geo_network_number", "geo_network_organization"} <= fields
            row = connection.execute(sa.text("SELECT * FROM user_sessions")).mappings().one()
            assert row["id"] == 1
            if existing:
                assert row["geo_network_number"] == 123
                assert row["geo_network_organization"] == "Existing owner"
    finally:
        engine.dispose()
