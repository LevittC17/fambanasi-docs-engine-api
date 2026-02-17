"""
Audit service for logging user actions and system events.

Maintains comprehensive audit trail for compliance, security
monitoring, and troubleshooting.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.audit_log import AuditAction, AuditLog
from app.db.models.user import User

logger = get_logger(__name__)


class AuditService:
    """
    Service for audit logging operations.

    Provides methods to log user actions, system events, and errors
    for security monitoring and compliance.
    """

    async def log_action(
        self,
        db: AsyncSession,
        action: AuditAction,
        description: str,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        """
        Log an action to the audit trail.

        Args:
            db: Database session
            action: Type of action performed
            description: Human-readable description
            user_id: User who performed the action
            resource_type: Type of resource affected
            resource_id: ID or path of affected resource
            ip_address: IP address of request
            user_agent: User agent string
            metadata: Additional metadata
            old_value: State before change
            new_value: State after change
            success: Whether action succeeded
            error_message: Error message if failed

        Returns:
            Created audit log entry
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                metadata=metadata,
                old_value=old_value,
                new_value=new_value,
                success=success,
                error_message=error_message,
            )

            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)

            logger.info(
                f"Audit log created: {action.value} by user {user_id} - {description}"
            )

            return audit_log

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating audit log: {e}")
            # Don't raise - audit logging shouldn't break normal operations
            return None

    async def log_document_create(
        self,
        db: AsyncSession,
        user: User,
        document_path: str,
        title: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log document creation."""
        return await self.log_action(
            db=db,
            action=AuditAction.DOCUMENT_CREATE,
            description=f"Created document: {title}",
            user_id=user.id,
            resource_type="document",
            resource_id=document_path,
            ip_address=ip_address,
            new_value={"path": document_path, "title": title},
        )

    async def log_document_update(
        self,
        db: AsyncSession,
        user: User,
        document_path: str,
        title: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log document update."""
        return await self.log_action(
            db=db,
            action=AuditAction.DOCUMENT_UPDATE,
            description=f"Updated document: {title}",
            user_id=user.id,
            resource_type="document",
            resource_id=document_path,
            ip_address=ip_address,
        )

    async def log_document_delete(
        self,
        db: AsyncSession,
        user: User,
        document_path: str,
        title: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log document deletion."""
        return await self.log_action(
            db=db,
            action=AuditAction.DOCUMENT_DELETE,
            description=f"Deleted document: {title}",
            user_id=user.id,
            resource_type="document",
            resource_id=document_path,
            ip_address=ip_address,
            old_value={"path": document_path, "title": title},
        )

    async def log_login(
        self,
        db: AsyncSession,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> AuditLog:
        """Log user login attempt."""
        return await self.log_action(
            db=db,
            action=AuditAction.LOGIN,
            description=f"User login: {user.email}",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )

    async def get_user_activity(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """
        Get activity log for a specific user.

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Tuple of (audit logs, total count)
        """
        from sqlalchemy import func

        # Get total count
        count_result = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.user_id == user_id)
        )
        total = count_result.scalar()

        # Get logs
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()

        return list(logs), total or 0

    async def get_resource_history(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
    ) -> list[AuditLog]:
        """
        Get change history for a specific resource.

        Args:
            db: Database session
            resource_type: Type of resource
            resource_id: Resource identifier
            limit: Maximum results

        Returns:
            List of audit logs
        """
        result = await db.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
