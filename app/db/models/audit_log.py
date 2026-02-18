"""
Audit log model for tracking all system actions.

Maintains comprehensive audit trail of user actions, document changes,
and system events for compliance and troubleshooting.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class AuditAction(StrEnum):
    """Types of auditable actions."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"

    # Document operations
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_PUBLISH = "document_publish"

    # Draft operations
    DRAFT_CREATE = "draft_create"
    DRAFT_UPDATE = "draft_update"
    DRAFT_DELETE = "draft_delete"
    DRAFT_SUBMIT = "draft_submit"
    DRAFT_APPROVE = "draft_approve"
    DRAFT_REJECT = "draft_reject"

    # Media operations
    MEDIA_UPLOAD = "media_upload"
    MEDIA_DELETE = "media_delete"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_ROLE_CHANGE = "user_role_change"

    # System events
    SYSTEM_ERROR = "system_error"
    WEBHOOK_RECEIVED = "webhook_received"


class AuditLog(Base):
    """
    Audit log for tracking all system actions.

    Provides complete audit trail for compliance, security monitoring,
    and troubleshooting. Records user actions, system events, and errors.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), doc="Audit log entry ID",
    )

    # Timestamp (not using TimestampMixin as we only need created_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, doc="When the action occurred",
    )

    # User information
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who performed the action (null for system actions)",
    )

    # Action details
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, native_enum=False),
        nullable=False,
        index=True,
        doc="Type of action performed",
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Type of resource affected (document, draft, user, etc.)",
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="ID or path of the affected resource",
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address of the request",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="User agent string from the request"
    )

    # Change details
    description: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Human-readable description of the action"
    )

    # 'metadata' is reserved by SQLAlchemy's Declarative API, use attribute
    # name `metadata_` while keeping the DB column name as 'metadata'.
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, doc="Additional metadata about the action (JSON)"
    )

    # Before/after state for changes
    old_value: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, doc="State before the change (for updates/deletes)"
    )

    new_value: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, doc="State after the change (for creates/updates)"
    )

    # Error tracking
    success: Mapped[bool] = mapped_column(
        default=True, nullable=False, doc="Whether the action succeeded"
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Error message if action failed"
    )

    # Relationships
    user: Mapped[User | None] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        """String representation of audit log."""
        return f"<AuditLog(action={self.action}, user_id={self.user_id}, resource={self.resource_type})>"
