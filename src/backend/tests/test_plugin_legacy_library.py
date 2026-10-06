"""Retired records remain private, bounded and recoverable after core removal."""

import asyncio
import base64
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import Column, MetaData, String, Table, Uuid

from src.plugin_api import gateway, legacy_library
from src.plugin_api.capabilities import capability_definition, capability_implies
from src.plugin_api.game_library import game_details


class ExportDb:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def connection(self):
        return self

    async def run_sync(self, function, *args):
        return function(None, *args)

    async def execute(self, statement):
        self.statements.append(statement)
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: self.rows))


@pytest.fixture
def reflected(monkeypatch):
    metadata = MetaData()
    tables = {}
    for name in legacy_library.LEGACY_TABLES:
        ownership = (
            "user_id"
            if name in {"cards", "sets", "bounties", "bounty_point_transactions"}
            else "bounty_id"
        )
        tables[name] = Table(
            name,
            metadata,
            Column("id", Uuid, primary_key=True),
            Column(ownership, Uuid),
            Column("title", String),
        )
    monkeypatch.setattr(legacy_library, "_reflect", lambda _connection, name: tables.get(name))
    return tables


@pytest.mark.parametrize("table", sorted(legacy_library.LEGACY_TABLES))
def test_legacy_export_scopes_root_and_child_tables(reflected, table):
    user, record = uuid4(), uuid4()
    db = ExportDb([{"id": record, "user_id": user, "title": "Keep this"}])
    result = asyncio.run(
        legacy_library.export_legacy_records(db, user_id=user, payload={"table": table})
    )
    assert result["records"] == [{"id": str(record), "title": "Keep this"}]
    assert result["complete"] is True
    statement = db.statements[0]
    assert user in statement.compile().params.values()
    sql = str(statement)
    if "user_id" in reflected[table].c:
        assert f"{table}.user_id" in sql
    else:
        assert f"{table}.bounty_id IN (SELECT bounties.id" in sql
        assert "bounties.user_id" in sql
    assert "ORDER BY" in sql and "LIMIT" in sql


def test_legacy_export_bounded_pages_retry_without_skipping(reflected):
    rows = [{"id": uuid4(), "title": "x" * 90_000} for _ in range(4)]
    db = ExportDb(rows)
    result = asyncio.run(
        legacy_library.export_legacy_records(
            db, user_id=uuid4(), payload={"table": "cards", "offset": 12, "limit": 3}
        )
    )
    assert len(result["records"]) == 2
    assert result["next_offset"] == 14 and result["complete"] is False
    assert 12 in db.statements[0].compile().params.values()


def test_large_artwork_exports_without_loss_or_skipping(reflected):
    record = {"id": str(uuid4()), "title": "🎮" * 80_000}
    db = ExportDb([record])
    chunks, chunk_offset, digest = [], 0, None
    while True:
        page = asyncio.run(
            legacy_library.export_legacy_records(
                db,
                user_id=uuid4(),
                payload={
                    "table": "cards",
                    "offset": 3,
                    "chunk_offset": chunk_offset,
                    "sha256": digest,
                },
            )
        )
        chunk = page["chunk"]
        assert len(json.dumps(page).encode()) < legacy_library.MAX_PAGE_BYTES
        chunks.append(base64.b64decode(chunk["base64"], validate=True))
        digest = chunk["sha256"]
        if chunk["next_offset"] is None:
            assert page["complete"] and page["next_offset"] == 4
            break
        assert page["next_offset"] == 3 and not page["complete"]
        chunk_offset = chunk["next_offset"]
    encoded = b"".join(chunks)
    assert hashlib.sha256(encoded).hexdigest() == digest
    assert json.loads(encoded) == record
    with pytest.raises(ValueError, match="changed"):
        asyncio.run(
            legacy_library.export_legacy_records(
                db, user_id=uuid4(), payload={"table": "cards", "sha256": "outdated"}
            )
        )


def test_legacy_export_handles_new_servers_and_rejects_arbitrary_tables(monkeypatch):
    monkeypatch.setattr(legacy_library, "_reflect", lambda *_args: None)
    db = ExportDb([])
    assert (
        asyncio.run(
            legacy_library.export_legacy_records(db, user_id=uuid4(), payload={"table": "cards"})
        )["complete"]
        is True
    )
    assert not db.statements
    for table in ("users", "auth_sessions", "cards; DROP TABLE users"):
        with pytest.raises(ValueError, match="unsupported legacy"):
            asyncio.run(
                legacy_library.export_legacy_records(db, user_id=uuid4(), payload={"table": table})
            )


def test_legacy_import_permission_is_separate_and_withdrawable(monkeypatch):
    assert not capability_implies("games.read", "library.legacy.read")
    assert capability_definition("library.legacy.read").category == "User data"

    async def denied(*_args, **_kwargs):
        return False

    monkeypatch.setattr(gateway, "has_capability_grant", denied)
    with pytest.raises(PermissionError, match="has not been granted"):
        asyncio.run(
            gateway.dispatch_gateway_request(
                ExportDb([]),
                plugin_id="official.collectors",
                installation_id=uuid4(),
                user_id=uuid4(),
                method="library.legacy.export",
                capability="library.legacy.read",
                payload={"table": "cards"},
            )
        )


def test_public_game_details_never_include_private_filesystem_or_user_fields():
    from src.plugin_api.game_library import _PUBLIC_FIELDS

    values = {key: None for key in _PUBLIC_FIELDS}
    values.update(
        id=uuid4(), title="The Recovered Quest", status="MASTERED", tags=[], collections=[]
    )
    game = SimpleNamespace(
        **values, folder_location="/private/server/path", user_id=uuid4(), password="private"
    )
    result = game_details(game, total=20, unlocked=20)
    assert result["achievement_total"] == 20
    assert result["achievement_unlocked"] == 20
    assert result["assets"]["key_art"] == f"/api/game/{game.id}/assets/key_art"
    assert all(key not in result for key in ("user_id", "folder_location", "password"))
