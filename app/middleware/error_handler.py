"""
Global error handling middleware.

Catches and formats all exceptions into consistent API responses,
logs errors, and optionally sends to monitoring services.
"""

import traceback
from collections.abc import Callable
from datetime import datetime

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import BaseAPIException
from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.

    Catches all exceptions, formats them into consistent JSON responses,
    and logs errors for debugging and monitoring.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error handling.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response (may be error response)
        """
        try:
            response = await call_next(request)
            return response

        except BaseAPIException as e:
            # Handle our custom exceptions
            logger.warning(
                f"API exception: {e.message}",
                extra={
                    "status_code": e.status_code,
                    "path": request.url.path,
                    "method": request.method,
                    "details": e.details,
                },
            )

            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "details": e.details,
                    "status_code": e.status_code,
                    "timestamp": datetime.utcnow().isoformat(),
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
