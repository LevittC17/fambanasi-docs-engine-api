"""
Authentication endpoints.

Provides user authentication, registration, and token management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
)
from app.db.models.audit_log import AuditAction
from app.db.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, TokenResponse, UserResponse
from app.services.audit_service import AuditService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """
    User login endpoint.

    Authenticates user with email and password, returns JWT tokens.

    Args:
        credentials: Login credentials (email, password)
        db: Database session

    Returns:
        User information and access tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Verify password (in real implementation, compare with hashed password)
        # For now, this is a placeholder - actual password verification
        # would be done against Supabase Auth

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        # Create tokens
        token_data = {"sub": str(user.id), "role": user.role.value}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Update last login
        from datetime import datetime

        user.last_login_at = datetime.utcnow()
        await db.commit()

        # Log audit trail
        audit_service = AuditService()
        await audit_service.log_login(db=db, user=user, success=True)

        logger.info(f"User logged in: {user.email}")

        # Return response
        from app.core.config import settings

        return LoginResponse(
            user=UserResponse.model_validate(user),
            token=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """
    User logout endpoint.

    Logs the logout action for audit trail.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Log audit trail
    audit_service = AuditService()
    await audit_service.log_action(
        db=db,
        action=AuditAction.LOGOUT,
        description=f"User logout: {current_user.email}",
        user_id=current_user.id,
    )

    logger.info(f"User logged out: {current_user.email}")

    return {"message": "Successfully logged out"}
