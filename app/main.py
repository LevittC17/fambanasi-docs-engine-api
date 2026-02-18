"""
Main FastAPI application entry point.

Initializes the FastAPI app with all middleware, routers, and
lifecycle event handlers for database and external services.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.session import close_db, init_db
from app.middleware.auth_middleware import AuthenticationMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for database connections,
    external services, and resource cleanup.
    """
    # Startup
    logger.info("Starting application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize services (health checks)
        from app.services.github_service import GitHubService
        from app.services.supabase_service import SupabaseService

        github = GitHubService()
        github_health = await github.health_check()
        logger.info(f"GitHub service: {github_health['status']}")

        supabase = SupabaseService()
        supabase_health = await supabase.health_check()
        logger.info(f"Supabase service: {supabase_health['status']}")

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")

    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI backend for Git-Sync Documentation Engine",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Add custom middleware (order matters - executed in reverse)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint - API information.

    Returns:
        Basic API information and links
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else "disabled",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    Health check endpoint.

    Checks connectivity to all external services (database, GitHub, Supabase)
    and returns overall system health status.

    Returns:
        JSON response with health status
    """
    from datetime import datetime

    from app.services.github_service import GitHubService
    from app.services.supabase_service import SupabaseService

    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {},
    }

    # Check database
    try:
        from sqlalchemy import text

        from app.db.session import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check GitHub
    try:
        github = GitHubService()
        github_health = await github.health_check()
        health_status["services"]["github"] = github_health["status"]

        if github_health["status"] != "healthy":
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"GitHub health check failed: {e}")
        health_status["services"]["github"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Supabase
    try:
        supabase = SupabaseService()
        supabase_health = await supabase.health_check()
        health_status["services"]["supabase"] = supabase_health["status"]

        if supabase_health["status"] != "healthy":
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        health_status["services"]["supabase"] = "unhealthy"
        health_status["status"] = "degraded"

    # Determine HTTP status code
    status_code = 200 if health_status["status"] == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=health_status,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
