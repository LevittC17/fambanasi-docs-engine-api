"""
User management endpoints.

Provides admin-level user management including listing,
role management, and activity monitoring.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_db
from app.core.logging import get_logger
from app.db.models.user import User, UserRole
from app.schemas.auth import UserResponse, UserUpdate
from app.schemas.common import PaginatedResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[UserResponse]:
    """
    List all users.

    Admin only. Supports filtering by role and active status.

    Args:
        db: Database session
        current_user: Current admin user
        page: Page number
        page_size: Items per page
        role: Optional role filter
        is_active: Optional active status filter

    Returns:
        Paginated list of users
    """
    from sqlalchemy import func

    stmt = select(User)

    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    # Count total
    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.order_by(User.created_at.desc()).limit(page_size).offset(offset)

    result = await db.execute(stmt)
    users = result.scalars().all()

    return PaginatedResponse[UserResponse](
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=offset + page_size < total,
        has_previous=page > 1,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> UserResponse:
    """
    Get user by ID.

    Admin only.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user

    Returns:
        User information
    """
    from app.core.exceptions import ResourceNotFoundError

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError("User", str(user_id))

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> UserResponse:
    """
    Update user information or role.

    Admin only. Can update role, active status, and preferences.

    Args:
        user_id: User ID
        user_update: Fields to update
        db: Database session
        current_user: Current admin user

    Returns:
        Updated user
    """
    from app.core.exceptions import ResourceNotFoundError
    from app.db.models.audit_log import AuditAction
    from app.services.audit_service import AuditService

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError("User", str(user_id))

    # Track role change for audit
    old_role = user.role

    # Apply updates
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    # Log role change
    if "role" in update_data and update_data["role"] != old_role:
        audit_service = AuditService()
        await audit_service.log_action(
            db=db,
            action=AuditAction.USER_ROLE_CHANGE,
            description=f"Role changed for {user.email}: {old_role} -> {user.role}",
            user_id=current_user.id,
            resource_type="user",
            resource_id=str(user.id),
            old_value={"role": old_role.value},
            new_value={"role": user.role.value},
        )

    return UserResponse.model_validate(user)


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    """
    Get user activity log.

    Admin only.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user
        page: Page number
        page_size: Items per page

    Returns:
        Paginated user activity log
    """
    from app.services.audit_service import AuditService

    audit_service = AuditService()
    offset = (page - 1) * page_size

    logs, total = await audit_service.get_user_activity(
        db=db,
        user_id=user_id,
        limit=page_size,
        offset=offset,
    )

    return {
        "items": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
