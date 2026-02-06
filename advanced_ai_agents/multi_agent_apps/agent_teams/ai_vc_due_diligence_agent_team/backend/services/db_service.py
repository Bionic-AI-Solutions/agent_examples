"""Database Service - Manages PostgreSQL connection pool"""

import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from loguru import logger

# Global engine and session factory
_engine = None
_async_session = None


async def initialize_db_pool():
    """Initialize database connection pool"""
    global _engine, _async_session

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set - database features disabled")
        return

    # Railway provides postgresql:// but SQLAlchemy async needs postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info("Initializing database connection pool")

    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
    )

    _async_session = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Database connection pool initialized successfully")


async def close_db_pool():
    """Close database connection pool"""
    global _engine

    if _engine:
        logger.info("Closing database connection pool")
        await _engine.dispose()
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_session():
    """
    Get database session context manager.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)
    """
    if _async_session is None:
        raise RuntimeError(
            "Database not initialized. Call initialize_db_pool() first"
        )

    async with _async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_engine():
    """Get the database engine (for migrations, etc.)"""
    if _engine is None:
        raise RuntimeError(
            "Database not initialized. Call initialize_db_pool() first"
        )
    return _engine
