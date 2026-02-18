"""
Global error handling middleware.

Catches and formats all exceptions into consistent API responses,
logs errors, and optionally sends to monitoring services.
"""

import traceback
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import BaseAPIError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global exception handling.

    Catches unhandled exceptions and returns standardized JSON responses.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Dispatch request through middleware chain.

        Args:
            request: Incoming request
            call_next: Next middleware function

        Returns:
            HTTP response
        """
        try:
            return await call_next(request)
        except BaseAPIError as e:
            # Handle application-specific exceptions
            logger.warning(f"API error: {e.message}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "details": e.details,
                    "status_code": e.status_code,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "path": request.url.path,
                },
            )

        except ValueError as e:
            # Handle validation errors
            logger.warning(
                f"Validation error: {str(e)}",
                extra={"path": request.url.path, "method": request.method},
            )

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation error",
                    "details": {"message": str(e)},
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path,
                },
            )

        except Exception as e:
            # Handle unexpected errors
            error_id = datetime.utcnow().isoformat()

            logger.error(
                f"Unhandled exception [{error_id}]: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
            )

            # In production, don't expose internal error details
            error_message = "Internal server error"
            error_details = {"error_id": error_id}

            if settings.DEBUG:
                error_details["message"] = str(e)
                error_details["type"] = type(e).__name__
                error_details["traceback"] = traceback.format_exc()

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": error_message,
                    "details": error_details,
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path,
                },
            )
