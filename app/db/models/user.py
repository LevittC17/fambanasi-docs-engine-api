"""
User model for authentication and authorization.

Stores user information synced from Supabase Auth, including roles
and permissions for role-based access control.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserRole(StrEnum):
    """User roles for role-based access control."""

    VIEWER = "viewer"  # Can only view documentation
    EDITOR = "editor"  # Can create and edit documentation
    ADMIN = "admin"  # Full access including user management


class User(Base, TimestampMixin):
    """
    User model representing authenticated users.

    Synced with Supabase Auth to maintain local user records for
    permissions, preferences, and audit logging.
    """

    __tablename__ = "users"

    # Primary key (matches Supabase Auth UUID)
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, doc="User ID from Supabase Auth"
    )

    # User information
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, doc="User email address"
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="User's full name"
    )

    avatar_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="URL to user's avatar image"
    )

    # Role and permissions
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.VIEWER,
        nullable=False,
        index=True,
        doc="User role for access control",
    )

    # User status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, doc="Whether user account is active"
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Whether user email is verified"
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Last login timestamp"
    )

    # User preferences (JSON)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(
        Text, nullable=True, doc="User preferences as JSON string"
    )

    def __repr__(self) -> str:
        """String representation of user."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def has_permission(self, required_role: UserRole) -> bool:
        """
        Check if user has required permission level.

        Args:
            required_role: Minimum role required

        Returns:
            True if user has sufficient permissions
        """
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.EDITOR: 2,
            UserRole.ADMIN: 3,
        }
        return role_hierarchy[self.role] >= role_hierarchy[required_role]
