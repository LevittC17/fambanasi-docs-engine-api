"""
Core configuration module for the FastAPI application.

This module defines all application settings using Pydantic BaseSettings,
enabling configuration through environment variables with type validation.
Settings are loaded from .env files and environment variables.
"""

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All sensitive configuration (API keys, database URLs) should be
    provided via environment variables, never hardcoded.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    # Application Settings
    APP_NAME: str = Field(default="Fambanasi Docs Engine API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development/staging/production)",
    )

    # Server Settings
    HOST: str = Field(default="0.0.0.0", description="Server host")  # noqa: S104
    PORT: int = Field(default=8000, description="Server port")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 route prefix")

    # Security Settings
    SECRET_KEY: str = Field(..., description="Secret key for JWT token generation")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=10080, description="Access token expiry (7 days)"
    )
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(
        default=43200, description="Refresh token expiry (30 days)"
    )

    # CORS Settings
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS")
    CORS_ALLOW_METHODS: list[str] = Field(default=["*"], description="Allowed HTTP methods")
    CORS_ALLOW_HEADERS: list[str] = Field(default=["*"], description="Allowed HTTP headers")

    # Database Settings (Supabase PostgreSQL)
    DATABASE_URL: PostgresDsn = Field(..., description="PostgreSQL database URL from Supabase")
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries (dev only)")

    # Supabase Settings
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous/public key")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Supabase service role key (private)")
    SUPABASE_JWT_SECRET: str = Field(..., description="Supabase JWT secret for token validation")
    SUPABASE_BUCKET_NAME: str = Field(
        default="docs-media", description="Supabase storage bucket for media"
    )

    # GitHub Settings
    GITHUB_TOKEN: str = Field(..., description="GitHub Personal Access Token with repo permissions")
    GITHUB_OWNER: str = Field(..., description="GitHub repository owner/organization")
    GITHUB_REPO: str = Field(..., description="GitHub repository name (fambanasi-docs-content)")
    GITHUB_BRANCH: str = Field(default="main", description="Default branch for commits")
    GITHUB_WEBHOOK_SECRET: str = Field(..., description="Secret for validating GitHub webhooks")

    # Redis Settings (for caching and rate limiting)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    REDIS_CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds (1 hour)")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="Max requests per minute per user")

    # File Upload Settings
    MAX_UPLOAD_SIZE: int = Field(
        default=10485760, description="Max file upload size in bytes (10MB)"
    )
    ALLOWED_IMAGE_TYPES: list[str] = Field(
        default=["image/jpeg", "image/png", "image/gif", "image/webp"],
        description="Allowed image MIME types",
    )
    ALLOWED_DOCUMENT_TYPES: list[str] = Field(
        default=["application/pdf", "text/markdown", "text/plain"],
        description="Allowed document MIME types",
    )

    # Document Settings
    DOCS_ROOT_PATH: str = Field(
        default="docs", description="Root path in Git repo for documentation"
    )
    MEDIA_ROOT_PATH: str = Field(
        default="media", description="Root path in Git repo for media assets"
    )
    DEFAULT_DOCUMENT_AUTHOR: str = Field(
        default="System", description="Default author for system-generated commits"
    )

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    LOG_FILE: str | None = Field(default=None, description="Log file path (None for stdout only)")

    # Monitoring & Observability
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN for error tracking")
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ALLOWED_IMAGE_TYPES", "ALLOWED_DOCUMENT_TYPES", mode="before")
    @classmethod
    def parse_allowed_types(cls, v: Any) -> list[str]:
        """Parse allowed MIME types from JSON array or comma-separated string."""
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:  # noqa: S110
                    # Log error or ignore
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Any) -> str:
        """Ensure DATABASE_URL is properly formatted."""
        if isinstance(v, str):
            return v
        return str(v)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function uses lru_cache to ensure settings are loaded only once,
    improving performance and ensuring consistency across the application.

    Returns:
        Settings: Cached settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
