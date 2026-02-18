"""
Draft service for unpublished document management.

Handles draft creation, editing, review workflow, and publishing
to the Git repository.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.models.draft import Draft, DraftStatus
from app.db.models.user import User, UserRole
from app.schemas.draft import DraftCreate, DraftStatusUpdate, DraftUpdate
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService
from app.utils.file_helpers import generate_slug
from app.utils.validators import validate_file_path

logger = get_logger(__name__)


class DraftService:
    """
    Service for draft document operations.

    Manages unpublished drafts with review workflow before
    publishing to the Git repository.
    """

    def __init__(self) -> None:
        """Initialize draft service with dependencies."""
        self.document_service = DocumentService()
        self.audit = AuditService()

    async def create_draft(
        self,
        db: AsyncSession,
        draft_data: DraftCreate,
        author: User,
    ) -> Draft:
        """
        Create a new draft.

        Args:
            db: Database session
            draft_data: Draft creation data
            author: User creating the draft

        Returns:
            Created draft

        Raises:
            ValidationError: If draft data is invalid
        """
        try:
            # Validate target path
            validate_file_path(draft_data.target_path)

            logger.info(f"Creating draft: {draft_data.title}")

            # Generate slug from title
            slug = generate_slug(draft_data.title)

            # Create draft
            draft = Draft(
                title=draft_data.title,
                slug=slug,
                target_path=draft_data.target_path,
                content=draft_data.content,
                frontmatter=draft_data.frontmatter,
                status=DraftStatus.DRAFT,
                author_id=author.id,
            )

            db.add(draft)
            await db.commit()
            await db.refresh(draft)

            # Log audit trail
            await self.audit.log_action(
                db=db,
                action="draft_create",
                description=f"Created draft: {draft.title}",
                user_id=author.id,
                resource_type="draft",
                resource_id=str(draft.id),
                new_value={"title": draft.title, "target_path": draft.target_path},
            )

            logger.info(f"Draft created with ID: {draft.id}")
            return draft

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating draft: {e}")
            raise

    async def get_draft(
        self,
        db: AsyncSession,
        draft_id: UUID,
    ) -> Draft:
        """
        Get draft by ID.

        Args:
            db: Database session
            draft_id: Draft ID

        Returns:
            Draft object

        Raises:
            ResourceNotFoundError: If draft doesn't exist
        """
        result = await db.execute(select(Draft).where(Draft.id == draft_id))
        draft = result.scalar_one_or_none()

        if not draft:
            raise ResourceNotFoundError("Draft", str(draft_id))

        return draft

    async def update_draft(
        self,
        db: AsyncSession,
        draft_id: UUID,
        draft_update: DraftUpdate,
        user: User,
    ) -> Draft:
        """
        Update an existing draft.

        Args:
            db: Database session
            draft_id: Draft ID
            draft_update: Fields to update
            user: User updating the draft

        Returns:
            Updated draft

        Raises:
            ResourceNotFoundError: If draft doesn't exist
            ValidationError: If update is invalid
        """
        try:
            # Get existing draft
            draft = await self.get_draft(db, draft_id)

            # Check permissions
            if draft.author_id != user.id and not user.has_permission(UserRole.ADMIN):
                raise ValidationError("Only the author or admin can update this draft")

            logger.info(f"Updating draft: {draft_id}")

            # Update fields
            update_data = draft_update.model_dump(exclude_unset=True)

            # Regenerate slug if title changed
            if "title" in update_data:
                update_data["slug"] = generate_slug(update_data["title"])

            # Increment version
            update_data["version"] = draft.version + 1

            for field, value in update_data.items():
                setattr(draft, field, value)

            await db.commit()
            await db.refresh(draft)

            # Log audit trail
            await self.audit.log_action(
                db=db,
                action="draft_update",
                description=f"Updated draft: {draft.title}",
                user_id=user.id,
                resource_type="draft",
                resource_id=str(draft.id),
            )

            return draft

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating draft {draft_id}: {e}")
            raise

    async def delete_draft(
        self,
        db: AsyncSession,
        draft_id: UUID,
        user: User,
    ) -> None:
        """
        Delete a draft.

        Args:
            db: Database session
            draft_id: Draft ID
            user: User deleting the draft

        Raises:
            ResourceNotFoundError: If draft doesn't exist
            ValidationError: If user lacks permissions
        """
        try:
            # Get draft
            draft = await self.get_draft(db, draft_id)

            # Check permissions
            if draft.author_id != user.id and not user.has_permission(UserRole.ADMIN):
                raise ValidationError("Only the author or admin can delete this draft")

            logger.info(f"Deleting draft: {draft_id}")

            # Log audit trail before deletion
            await self.audit.log_action(
                db=db,
                action="draft_delete",
                description=f"Deleted draft: {draft.title}",
                user_id=user.id,
                resource_type="draft",
                resource_id=str(draft.id),
                old_value={"title": draft.title, "target_path": draft.target_path},
            )

            await db.delete(draft)
            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting draft {draft_id}: {e}")
            raise

    async def submit_for_review(
        self,
        db: AsyncSession,
        draft_id: UUID,
        user: User,
        reviewer_id: UUID | None = None,
    ) -> Draft:
        """
        Submit draft for review.

        Args:
            db: Database session
            draft_id: Draft ID
            user: User submitting the draft
            reviewer_id: Optional specific reviewer

        Returns:
            Updated draft

        Raises:
            ResourceNotFoundError: If draft doesn't exist
            ValidationError: If submission is invalid
        """
        try:
            # Get draft
            draft = await self.get_draft(db, draft_id)

            # Check permissions
            if draft.author_id != user.id:
                raise ValidationError("Only the author can submit a draft for review")

            # Check current status
            if draft.status != DraftStatus.DRAFT:
                raise ValidationError(f"Cannot submit draft with status: {draft.status}")

            logger.info(f"Submitting draft for review: {draft_id}")

            # Update status
            draft.status = DraftStatus.IN_REVIEW
            draft.submitted_at = datetime.utcnow()
            draft.reviewer_id = reviewer_id

            await db.commit()
            await db.refresh(draft)

            # Log audit trail
            await self.audit.log_action(
                db=db,
                action="draft_submit",
                description=f"Submitted draft for review: {draft.title}",
                user_id=user.id,
                resource_type="draft",
                resource_id=str(draft.id),
            )

            return draft

        except Exception as e:
            await db.rollback()
            logger.error(f"Error submitting draft {draft_id}: {e}")
            raise

    async def update_draft_status(
        self,
        db: AsyncSession,
        draft_id: UUID,
        status_update: DraftStatusUpdate,
        reviewer: User,
    ) -> Draft:
        """
        Update draft status (approve/reject).

        Args:
            db: Database session
            draft_id: Draft ID
            status_update: Status update data
            reviewer: User reviewing the draft

        Returns:
            Updated draft

        Raises:
            ResourceNotFoundError: If draft doesn't exist
            ValidationError: If status update is invalid
        """
        try:
            # Get draft
            draft = await self.get_draft(db, draft_id)

            # Check permissions
            if not reviewer.has_permission(UserRole.EDITOR):
                raise ValidationError("Only editors and admins can review drafts")

            # Check current status
            if draft.status != DraftStatus.IN_REVIEW:
                raise ValidationError(f"Cannot review draft with status: {draft.status}")

            logger.info(f"Updating draft status: {draft_id} -> {status_update.status}")

            # Update status
            draft.status = status_update.status
            draft.reviewer_id = reviewer.id
            draft.reviewed_at = datetime.utcnow()
            draft.review_comments = status_update.review_comments

            await db.commit()
            await db.refresh(draft)

            # Log audit trail
            action = (
                "draft_approve" if status_update.status == DraftStatus.APPROVED else "draft_reject"
            )
            await self.audit.log_action(
                db=db,
                action=action,
                description=f"{status_update.status.value.title()} draft: {draft.title}",
                user_id=reviewer.id,
                resource_type="draft",
                resource_id=str(draft.id),
                metadata={"comments": status_update.review_comments},
            )

            return draft

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating draft status {draft_id}: {e}")
            raise

    async def publish_draft(
        self,
        db: AsyncSession,
        draft_id: UUID,
        user: User,
        commit_message: str | None = None,
        branch: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Publish draft to Git repository.

        Args:
            db: Database session
            draft_id: Draft ID
            user: User publishing the draft
            commit_message: Custom commit message
            branch: Target branch
            ip_address: IP address of request

        Returns:
            Dictionary with published document information

        Raises:
            ResourceNotFoundError: If draft doesn't exist
            ValidationError: If publishing is invalid
        """
        try:
            # Get draft
            draft = await self.get_draft(db, draft_id)

            # Check permissions
            if draft.author_id != user.id and not user.has_permission(UserRole.ADMIN):
                raise ValidationError("Only the author or admin can publish this draft")

            # Check status
            if draft.status not in [DraftStatus.APPROVED, DraftStatus.DRAFT]:
                raise ValidationError(f"Cannot publish draft with status: {draft.status}")

            logger.info(f"Publishing draft: {draft_id} to {draft.target_path}")

            # Create document from draft
            from app.schemas.document import DocumentCreate, DocumentFrontmatter

            # Parse frontmatter if exists
            frontmatter = None
            if draft.frontmatter:
                import yaml

                frontmatter_dict = yaml.safe_load(draft.frontmatter)
                frontmatter = DocumentFrontmatter(**frontmatter_dict)

            document = DocumentCreate(
                path=draft.target_path,
                title=draft.title,
                content=draft.content,
                frontmatter=frontmatter,
                commit_message=commit_message,
                branch=branch or "main",
            )

            # Publish to repository
            published_doc = await self.document_service.create_document(
                db=db,
                document=document,
                user=user,
                ip_address=ip_address,
            )

            # Update draft status
            draft.status = DraftStatus.APPROVED  # Keep as approved
            draft.published_at = datetime.utcnow()

            await db.commit()
            await db.refresh(draft)

            # Log audit trail
            await self.audit.log_action(
                db=db,
                action="document_publish",
                description=f"Published draft to document: {draft.title}",
                user_id=user.id,
                resource_type="draft",
                resource_id=str(draft.id),
                new_value={"path": draft.target_path},
            )

            return {
                "draft_id": str(draft.id),
                "document": published_doc,
                "published_at": draft.published_at,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error publishing draft {draft_id}: {e}")
            raise

    async def list_drafts(
        self,
        db: AsyncSession,
        author_id: UUID | None = None,
        status: DraftStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Draft], int]:
        """
        List drafts with optional filtering.

        Args:
            db: Database session
            author_id: Filter by author
            status: Filter by status
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Tuple of (drafts list, total count)
        """
        from sqlalchemy import func

        stmt = select(Draft)

        # Apply filters
        if author_id:
            stmt = stmt.where(Draft.author_id == author_id)

        if status:
            stmt = stmt.where(Draft.status == status)

        # Get total count
        count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar()

        # Apply pagination and ordering
        stmt = stmt.order_by(Draft.updated_at.desc()).limit(limit).offset(offset)

        # Execute query
        result = await db.execute(stmt)
        drafts = result.scalars().all()

        return list(drafts), total or 0
