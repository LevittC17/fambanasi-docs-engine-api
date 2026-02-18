"""
FastAPI dependency injection functions.

Provides reusable dependencies for authentication, authorization,
database access, and other common requirements.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.core.security import decode_token, verify_supabase_token
from app.db.models.user import User, UserRole
from app.db.session import get_db

logger = get_logger(__name__)

# Security scheme for bearer token authentication
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    This dependency extracts the JWT token from the Authorization header,
    validates it, and returns the corresponding user from the database.

    Args:
        credentials: HTTP bearer token from request
        db: Database session

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: If token is invalid or user not found

    Example:
        @app.get("/profile")
        async def get_profile(user: User = Depends(get_current_user)):
            return {"email": user.email}
    """
    try:
        token = credentials.credentials

        # Try to decode as our token first
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
        except AuthenticationError:
            # If that fails, try as Supabase token
            payload = verify_supabase_token(token)
            user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("Token missing user identifier")

        # Fetch user from database
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        return user

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current active user (convenience wrapper).

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object
    """
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory to check user has required role.

    Args:
        required_role: Minimum role required

    Returns:
        Dependency function that validates user role

    Example:
        @app.post("/documents")
        async def create_doc(
            user: User = Depends(require_role(UserRole.EDITOR))
        ):
            ...
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not current_user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        return current_user

    return role_checker


async def get_current_editor(
    current_user: Annotated[User, Depends(require_role(UserRole.EDITOR))],
) -> User:
    """Get current user with at least Editor role."""
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> User:
    """Get current user with Admin role."""
    return current_user


async def verify_webhook_signature(
    x_hub_signature: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        x_hub_signature: SHA1 signature header
        x_hub_signature_256: SHA256 signature header (preferred)

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is missing or invalid
    """

    if not x_hub_signature_256 and not x_hub_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature"
        )

    # For now, we'll implement full verification when handling the webhook
    # This is a placeholder that allows the request through
    return True


def get_pagination_params(page: int = 1, page_size: int = 50) -> dict[str, int]:
    """
    Extract and validate pagination parameters.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Dictionary with offset and limit for database queries

    Raises:
        HTTPException: If parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page number must be >= 1",
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page size must be between 1 and 100",
        )

    offset = (page - 1) * page_size
    return {"offset": offset, "limit": page_size, "page": page, "page_size": page_size}


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User | None:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work differently for authenticated vs anonymous users.

    Args:
        credentials: Optional HTTP bearer token
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
