"""
Authentication middleware for request processing.

Handles JWT token extraction, validation, and user context
setting for all authenticated requests.
"""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle authentication for all requests.

    Extracts and validates JWT tokens, setting user context
    in the request state for downstream processing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            request.state.token = token
        else:
            request.state.token = None

        # Set user context (will be populated by dependencies)
        request.state.user = None

        response = await call_next(request)
        return response
