#!/usr/bin/env python3
"""
Database initialization script.

Creates all database tables and optionally seeds initial data.
Run this after setting up your environment variables.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger, setup_logging
from app.db.base import Base
from app.db.session import engine

setup_logging()
logger = get_logger(__name__)


async def init_database() -> None:
    """Initialize database schema."""
    try:
        logger.info("Starting database initialization...")

        async with engine.begin() as conn:
            # Drop all tables (use with caution!)
            # await conn.run_sync(Base.metadata.drop_all)
            # logger.info("Dropped existing tables")

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Created all database tables")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
