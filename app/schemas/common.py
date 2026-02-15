"""
Common schemas used across the application.

Defines reusable schemas for pagination, error responses,
and other cross-cutting concerns.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated responses."""

    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class ErrorDetail(BaseModel):
    """Schema for detailed error information."""

    field: str | None = Field(None, description="Field name if validation error")
    message: str = Field(..., description="Error message")
    type: str | None = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str = Field(..., description="Error message")
    details: list[ErrorDetail] | dict[str, Any] = Field(
        default_factory=list, description="Additional error details"
    )
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="ISO timestamp when error occurred")
    path: str | None = Field(None, description="Request path that caused the error")


class SuccessResponse(BaseModel):
    """Schema for generic success responses."""

    message: str = Field(..., description="Success message")
    data: dict[str, Any] | None = Field(None, description="Additional response data")


class HealthCheckResponse(BaseModel):
    """Schema for health check endpoint response."""

    status: str = Field(
        ..., description="Overall health status: 'healthy', 'degraded', 'unhealthy'"
    )
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Current server timestamp")
    services: dict[str, str] = Field(
        ..., description="Status of individual services (database, redis, github, etc.)"
    )
