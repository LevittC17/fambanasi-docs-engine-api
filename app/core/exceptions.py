"""
Custom exception classes for the application.

Defines domain-specific exceptions with appropriate HTTP status codes
and error messages for consistent error handling across the API.
"""

from typing import Any


class BaseAPIException(Exception):
    """Base exception class for all API exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize API exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(BaseAPIException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=401, details=details)


class AuthorizationError(BaseAPIException):
    """Raised when user lacks required permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=403, details=details)


class ResourceNotFoundError(BaseAPIException):
    """Raised when requested resource doesn't exist."""

    def __init__(self, resource: str, identifier: str | None = None) -> None:
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message=message, status_code=404)


class ResourceConflictError(BaseAPIException):
    """Raised when resource operation conflicts with current state."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=409, details=details)


class ValidationError(BaseAPIException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=422, details=details)


class GitHubAPIError(BaseAPIException):
    """Raised when GitHub API operation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=f"GitHub API error: {message}", status_code=502, details=details
        )


class SupabaseError(BaseAPIException):
    """Raised when Supabase operation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=f"Supabase error: {message}", status_code=502, details=details
        )


class RateLimitExceededError(BaseAPIException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ) -> None:
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message=message, status_code=429, details=details)


class FileUploadError(BaseAPIException):
    """Raised when file upload fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=400, details=details)


class DocumentProcessingError(BaseAPIException):
    """Raised when document processing fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=422, details=details)
