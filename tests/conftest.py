"""
Pytest configuration and shared fixtures.

Provides reusable test fixtures for database sessions,
authenticated users, mock services, and test client setup.
"""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """
    Provide test database session.

    Creates a fresh session for each test and rolls back
    changes after the test completes.
    """
    test_session_local = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with test_session_local() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a test viewer user."""
    user = User(
        id=uuid4(),
        email="viewer@test.com",
        full_name="Test Viewer",
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def editor_user(db_session: AsyncSession) -> User:
    """Create a test editor user."""
    user = User(
        id=uuid4(),
        email="editor@test.com",
        full_name="Test Editor",
        role=UserRole.EDITOR,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid4(),
        email="admin@test.com",
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def generate_token(user: User) -> str:
    """Generate JWT access token for a test user."""
    return create_access_token(data={"sub": str(user.id), "role": user.role.value})


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """
    Provide async HTTP test client with database override.

    Overrides the database dependency with the test session
    so all requests use the in-memory test database.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_github_service():
    """Mock GitHub service for unit tests."""
    mock = MagicMock()

    mock.get_file = AsyncMock(
        return_value={
            "path": "docs/test.md",
            "full_path": "docs/test.md",
            "content": "# Test\n\nTest content",
            "sha": "abc123def456",
            "size": 100,
            "url": "https://github.com/org/repo/blob/main/docs/test.md",
            "last_modified": "2026-01-01T00:00:00Z",
            "last_commit": {
                "sha": "abc123def456",
                "message": "docs: Create test",
                "author": "Test Author",
                "email": "test@example.com",
                "date": "2026-01-01T00:00:00Z",
                "url": "https://github.com/org/repo/commit/abc123",
            },
        }
    )

    mock.create_file = AsyncMock(
        return_value={
            "path": "docs/test.md",
            "full_path": "docs/test.md",
            "commit": {
                "sha": "newsha123",
                "message": "docs: Create test",
                "author": "Test Author",
                "email": "test@example.com",
                "date": "2026-01-01T00:00:00Z",
                "url": "https://github.com/org/repo/commit/newsha123",
            },
            "content_sha": "content_sha_123",
        }
    )

    mock.update_file = AsyncMock(
        return_value={
            "path": "docs/test.md",
            "full_path": "docs/test.md",
            "commit": {
                "sha": "updatedsha123",
                "message": "docs: Update test",
                "author": "Test Author",
                "email": "test@example.com",
                "date": "2026-01-01T00:00:00Z",
                "url": "https://github.com/org/repo/commit/updatedsha123",
            },
            "content_sha": "updated_content_sha",
        }
    )

    mock.delete_file = AsyncMock(
        return_value={
            "path": "docs/test.md",
            "full_path": "docs/test.md",
            "commit": {
                "sha": "deletedsha123",
                "message": "docs: Delete test",
                "author": "Test Author",
                "email": "test@example.com",
                "date": "2026-01-01T00:00:00Z",
                "url": "https://github.com/org/repo/commit/deletedsha123",
            },
        }
    )

    mock.list_files = AsyncMock(
        return_value=[
            {
                "path": "api/authentication.md",
                "name": "authentication.md",
                "size": 1500,
                "sha": "sha001",
                "url": "https://github.com/org/repo/blob/main/docs/api/authentication.md",
            },
            {
                "path": "api/endpoints.md",
                "name": "endpoints.md",
                "size": 2400,
                "sha": "sha002",
                "url": "https://github.com/org/repo/blob/main/docs/api/endpoints.md",
            },
        ]
    )

    mock.health_check = AsyncMock(
        return_value={
            "status": "healthy",
            "repository": "org/repo",
            "rate_limit": {
                "remaining": 4500,
                "limit": 5000,
                "reset": "2026-01-01T01:00:00",
            },
        }
    )

    return mock


@pytest.fixture
def mock_supabase_service():
    """Mock Supabase service for unit tests."""
    mock = MagicMock()

    mock.upload_file = AsyncMock(
        return_value={
            "path": "images/test.png",
            "bucket": "docs-media",
            "public_url": "https://supabase.co/storage/v1/object/public/docs-media/images/test.png",
            "size": 50000,
        }
    )

    mock.delete_file = AsyncMock(return_value=None)
    mock.health_check = AsyncMock(return_value={"status": "healthy"})

    return mock
