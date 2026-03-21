"""Async SQLAlchemy engine, session factory, and database initialisation.

Uses aiosqlite driver for SQLite. Session lifecycle is managed via
async context manager — always use get_session() in application code.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Declarative base — shared by all ORM models in db/models.py
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all TerraBot ORM models."""
    pass


# Module-level singletons; initialised by init_db()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _session_factory


def _migrate_jobs_is_hidden(connection) -> None:
    """Add is_hidden column to jobs table if it doesn't exist (no Alembic)."""
    from sqlalchemy import inspect, text
    inspector = inspect(connection)
    columns = [c["name"] for c in inspector.get_columns("jobs")]
    if "is_hidden" not in columns:
        connection.execute(
            text("ALTER TABLE jobs ADD COLUMN is_hidden BOOLEAN DEFAULT 0 NOT NULL")
        )
        logger.info("Migration: added is_hidden column to jobs table.")


async def init_db(db_url: str | None = None) -> AsyncEngine:
    """Create the async engine, session factory, and all tables.

    Safe to call multiple times — subsequent calls are no-ops if the engine
    is already initialised with the same URL.

    Args:
        db_url: SQLAlchemy connection string. Defaults to Settings.db_url.

    Returns:
        The initialised AsyncEngine instance.
    """
    global _engine, _session_factory

    if db_url is None:
        from backend.core.config import get_settings
        db_url = get_settings().db_url

    if _engine is not None:
        logger.debug("Database already initialised, skipping init_db()")
        return _engine

    logger.info("Initialising database: %s", db_url)

    _engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # Import models to ensure they are registered with Base.metadata
    import backend.db.models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migration: add is_hidden column if missing on existing DBs
        await conn.run_sync(_migrate_jobs_is_hidden)

    logger.info("Database tables created/verified.")
    return _engine


async def close_db() -> None:
    """Dispose the engine connection pool. Call on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection pool closed.")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a transactional database session.

    Commits on clean exit, rolls back on exception.

    Usage::

        async with get_session() as session:
            session.add(job)
            # auto-commit on exit
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
