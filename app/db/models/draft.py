"""
Draft model for unpublished documentation.

Drafts are stored in the database rather than Git, allowing users
to work on content without committing to the repository.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class DraftStatus(StrEnum):
    """Status of a draft document."""

    DRAFT = "draft"  # Work in progress
    IN_REVIEW = "in_review"  # Submitted for review
    APPROVED = "approved"  # Approved for publishing
    REJECTED = "rejected"  # Rejected, needs revision


class Draft(Base, TimestampMixin):
    """
    Draft document model for unpublished content.

    Drafts allow users to work on documentation without committing
    to Git. Once approved, drafts are published to the repository.
    """

    __tablename__ = "drafts"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Draft unique identifier",
    )

    # Document information
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True, doc="Draft document title"
    )

    slug: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True, doc="URL-friendly slug for the draft"
    )

    target_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Intended Git path when published (e.g., 'docs/api/authentication.md')",
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False, doc="Markdown content of the draft")

    frontmatter: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="YAML frontmatter metadata"
    )

    # Draft status
    status: Mapped[DraftStatus] = mapped_column(
        Enum(DraftStatus, native_enum=False),
        default=DraftStatus.DRAFT,
        nullable=False,
        index=True,
        doc="Current status of the draft",
    )

    # Authorship and review
    author_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Draft author user ID",
    )

    reviewer_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reviewer user ID",
    )

    # Review timestamps
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When draft was submitted for review",
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When draft was reviewed"
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When draft was published to Git"
    )

    # Review feedback
    review_comments: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Reviewer's comments and feedback"
    )

    # Version tracking
    version: Mapped[int] = mapped_column(
        default=1, nullable=False, doc="Draft version number (increments on save)"
    )

    # Relationships
    author: Mapped[User] = relationship("User", foreign_keys=[author_id], lazy="joined")

    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewer_id], lazy="joined")

    def __repr__(self) -> str:
        """String representation of draft."""
        return f"<Draft(id={self.id}, title={self.title}, status={self.status})>"
