from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession
import contextlib
from contextlib import asynccontextmanager # <-- This is the crucial import

# Assuming get_db is imported from an established session utility location


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Every model that inherits from Base is included
    in SQLAlchemy's metadata.
    """

    pass


@asynccontextmanager # <-- The decorator is sufficient here
async def transaction_scope(session: AsyncSession):
    """Asynchronous context manager for handling database transactions."""
    try:
        # Start a new transaction block (if not already started by the session)
        await session.begin()
        yield session
        # If we reach here, nothing failed, so commit everything
        await session.commit()
    except Exception as e:
        # An exception occurred anywhere in the block, rollback and raise the original error
        print(f"Transaction failed, rolling back due to: {e}")
        await session.rollback()
        raise # Re-raise the exception so calling code knows it failed

async def run_transaction(session_factory): # <-- CRITICAL FIX: Removed return type hint entirely
    """
    A wrapper factory for creating a transaction scope manager using a provided session factory (like get_db).
    This should be used as an async with statement: `async with transaction_scope(...) as session:`
    """
    return transaction_scope(session_factory)
