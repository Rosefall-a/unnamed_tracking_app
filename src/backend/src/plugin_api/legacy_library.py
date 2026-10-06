"""Bounded, read-only exports of retired personal library records.

The old migrations deliberately retain these tables. Reflection lets upgrades
recover records without keeping the retired ORM models or application routes.
Only this fixed allowlist is exposed, always scoped to the live gateway actor.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import MetaData, Table, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

LEGACY_TABLES = frozenset(
    {
        "cards",
        "sets",
        "bounties",
        "bounty_objectives",
        "bounty_evidence",
        "bounty_journal_entries",
        "bounty_point_transactions",
    }
)
MAX_PAGE_BYTES = 200_000
CHUNK_BYTES = 32_000


def _reflect(connection: Connection, name: str) -> Table | None:
    if not inspect(connection).has_table(name):
        return None
    return Table(name, MetaData(), autoload_with=connection, resolve_fks=False)


async def export_legacy_records(
    db: AsyncSession, *, user_id: UUID, payload: dict[str, Any]
) -> dict[str, Any]:
    """Export one deterministic page; never update or delete legacy records."""
    name = str(payload.get("table", ""))
    if name not in LEGACY_TABLES:
        raise ValueError("unsupported legacy library table")
    offset = max(0, int(payload.get("offset", 0)))
    limit = max(1, min(int(payload.get("limit", 25)), 50))
    connection = await db.connection()
    source = await connection.run_sync(_reflect, name)
    rows = []
    if source is not None:
        if "user_id" in source.c:
            owned = source.c.user_id == user_id
        else:
            parent = await connection.run_sync(_reflect, "bounties")
            if parent is None:
                raise ValueError("legacy bounty ownership records are missing")
            owned = source.c.bounty_id.in_(select(parent.c.id).where(parent.c.user_id == user_id))
        statement = (
            select(source).where(owned).order_by(source.c.id).offset(offset).limit(limit + 1)
        )
        rows = list((await db.execute(statement)).mappings().all())
    records: list[dict[str, Any]] = []
    page_bytes = 0
    for row in rows[:limit]:
        record = jsonable_encoder({key: value for key, value in row.items() if key != "user_id"})
        encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        size = len(encoded)
        if size > MAX_PAGE_BYTES:
            if records:
                break
            chunk_offset = int(payload.get("chunk_offset", 0))
            if chunk_offset < 0 or chunk_offset >= size:
                raise ValueError("invalid legacy record chunk offset")
            digest = hashlib.sha256(encoded).hexdigest()
            if payload.get("sha256") not in (None, digest):
                raise ValueError("legacy record changed during import; restart this record")
            end = min(size, chunk_offset + CHUNK_BYTES)
            return {
                "format_version": 1,
                "table": name,
                "records": [],
                "chunk": {
                    "record_id": str(record["id"]),
                    "sha256": digest,
                    "offset": chunk_offset,
                    "next_offset": end if end < size else None,
                    "total_bytes": size,
                    "base64": base64.b64encode(encoded[chunk_offset:end]).decode("ascii"),
                },
                "next_offset": offset + (end == size),
                "complete": end == size and len(rows) == 1,
            }
        if page_bytes + size > MAX_PAGE_BYTES:
            break
        records.append(record)
        page_bytes += size
    return {
        "format_version": 1,
        "table": name,
        "records": records,
        "next_offset": offset + len(records),
        "complete": len(rows) <= len(records),
    }
