"""
Rate limiting middleware for API protection.

Implements token bucket algorithm using Redis to prevent
API abuse and ensure fair resource usage.
"""

import time
from typing import Any, Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Limits requests per user/IP to prevent abuse and ensure
    system stability under load.
    """

    def __init__(self, app: Callable[..., Any], redis_client: Any = None) -> None:
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            redis_client: Redis client for distributed rate limiting
        """
        super().__init__(app)
        self.redis_client = redis_client
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE

        # In-memory fallback if Redis unavailable
        self._memory_cache: dict[str, dict[str, Any]] = {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response (429 if rate limit exceeded)
        """
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get identifier (user ID or IP)
        identifier = await self._get_identifier(request)

        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(identifier)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "details": {"retry_after": retry_after, "limit": self.rate_limit},
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response

    async def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Args:
            request: HTTP request

        Returns:
            Identifier string (user ID or IP address)
        """
        # Try to get user ID from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user:
            return f"user:{user.id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _check_rate_limit(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier for rate limiting

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if self.redis_client:
            return await self._check_redis_rate_limit(identifier)
        else:
            return await self._check_memory_rate_limit(identifier)

    async def _check_redis_rate_limit(self, identifier: str) -> tuple[bool, int]:
        """
        Check rate limit using Redis.

        Args:
            identifier: Unique identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        try:
            key = f"rate_limit:{identifier}"
            window = 60  # 1 minute window

            # Get current count
            current = await self.redis_client.get(key)

            if current is None:
                # First request in window
                await self.redis_client.setex(key, window, 1)
                return True, 0

            current_count = int(current)

            if current_count >= self.rate_limit:
                # Rate limit exceeded
                ttl = await self.redis_client.ttl(key)
                return False, max(ttl, 1)

            # Increment counter
            await self.redis_client.incr(key)
            return True, 0

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fall back to memory cache
            return await self._check_memory_rate_limit(identifier)

    async def _check_memory_rate_limit(self, identifier: str) -> tuple[bool, int]:
        """
        Check rate limit using in-memory cache.

        Args:
            identifier: Unique identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window = 60  # 1 minute window

        if identifier not in self._memory_cache:
            self._memory_cache[identifier] = {"count": 1, "window_start": now}
            return True, 0

        cache_entry = self._memory_cache[identifier]

        # Check if window has expired
        if now - cache_entry["window_start"] >= window:
            # Reset window
            self._memory_cache[identifier] = {"count": 1, "window_start": now}
            return True, 0

        # Check if limit exceeded
        if cache_entry["count"] >= self.rate_limit:
            retry_after = int(window - (now - cache_entry["window_start"]))
            return False, max(retry_after, 1)

        # Increment counter
        cache_entry["count"] += 1
        return True, 0
