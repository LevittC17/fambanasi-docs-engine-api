"""
Database session management and connection handling.

Provides async database session factory and dependency injection
for FastAPI endpoints to access the database.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create async engine with connection pooling
def _ensure_async_driver(url: str) -> str:
    """Ensure the database URL uses an async driver (asyncpg) for async engine.

    If the provided URL is a sync 'postgresql://' or 'postgres://' URL, convert
    it to 'postgresql+asyncpg://'. If the URL already specifies a driver
    (contains '+'), return unchanged.
    """
    if "+" in url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _ensure_async_driver(str(settings.DATABASE_URL)),
    echo=settings.DATABASE_ECHO,
    # asyncpg + SQLAlchemy's async engine manages pooling differently; do not
    # pass `pool_size`/`max_overflow` which are invalid for certain async
    # combinations (e.g. PGDialect_asyncpg/NullPool/Engine).
    pool_pre_ping=True,  # Verify connections before using
    poolclass=NullPool if settings.is_development else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields an async database session and ensures it's properly closed
    after use. Used as a FastAPI dependency in route handlers.

    Yields:
        AsyncSession: Database session for executing queries

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection and verify connectivity.

    Called during application startup to ensure database is accessible
    and create tables if needed (in development).
    """
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.run_sync(lambda _: None)
            logger.info("Database connection established successfully")

            # In development, create tables (production uses migrations)
            if settings.is_development:
                from app.db.base import Base

                logger.info("Creating database tables (development mode)")
                await conn.run_sync(Base.metadata.create_all)

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections gracefully.

    Called during application shutdown to clean up resources.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise
