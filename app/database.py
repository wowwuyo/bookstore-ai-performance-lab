"""Async SQLAlchemy engine, sessions, and schema initialization."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models import Base
from app.repositories.seed import seed_initial_data


def _ensure_database_parent(database_url: str) -> None:
    parsed_url = make_url(database_url)
    database = parsed_url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return
    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite_connection(
    dbapi_connection: Any,
    connection_record: Any,
) -> None:
    del connection_record
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
    finally:
        cursor.close()


def create_database_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLite engine with the required connection PRAGMAs."""
    _ensure_database_parent(database_url)
    database_engine = create_async_engine(database_url)
    event.listen(database_engine.sync_engine, "connect", _configure_sqlite_connection)
    return database_engine


engine = create_database_engine(settings.database_url)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped async database session."""
    async with async_session_factory() as session:
        yield session


async def create_database_tables(database_engine: AsyncEngine) -> None:
    """Create all currently missing Code First tables and indexes."""
    async with database_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def init_database() -> None:
    """Create the SQLite file and any missing ORM-defined tables."""
    await create_database_tables(engine)
    async with async_session_factory() as session:
        await seed_initial_data(session)


async def dispose_database() -> None:
    """Close all pooled database connections."""
    await engine.dispose()
