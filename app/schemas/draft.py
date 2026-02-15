"""
Draft document schemas.

Defines request/response models for draft operations
including creation, updates, and review workflow.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.db.models.draft import DraftStatus


class DraftBase(BaseModel):
    """Base draft schema with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Draft title")
    content: str = Field(..., min_length=1, description="Markdown content")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v


class DraftCreate(DraftBase):
    """Schema for creating a new draft."""

    target_path: str = Field(
        ...,
        min_length=1,
        description="Intended Git path when published (e.g., 'docs/api/authentication.md')",
    )
    frontmatter: str | None = Field(None, description="YAML frontmatter metadata")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_format(cls, v: str) -> str:
        """Validate target path format."""
        if not v.endswith(".md"):
            raise ValueError("Target path must end with .md extension")
        if v.startswith("/"):
            raise ValueError("Target path should not start with /")
        if ".." in v:
            raise ValueError(
                "Target path cannot contain .. (parent directory references)"
            )
        return v


class DraftUpdate(BaseModel):
    """Schema for updating an existing draft."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    target_path: str | None = None
    frontmatter: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content_if_provided(cls, v: str | None) -> str | None:
        """Ensure content is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v

    @field_validator("target_path")
    @classmethod
    def validate_target_path_if_provided(cls, v: str | None) -> str | None:
        """Validate target path format if provided."""
        if v is not None:
            if not v.endswith(".md"):
                raise ValueError("Target path must end with .md extension")
            if v.startswith("/"):
                raise ValueError("Target path should not start with /")
            if ".." in v:
                raise ValueError(
                    "Target path cannot contain .. (parent directory references)"
                )
        return v


class DraftStatusUpdate(BaseModel):
    """Schema for updating draft status (submit, approve, reject)."""

    status: DraftStatus = Field(..., description="New draft status")
    review_comments: str | None = Field(None, description="Reviewer's comments")

    @field_validator("review_comments")
    @classmethod
    def validate_comments_for_rejection(cls, v: str | None, info) -> str | None:
        """Require comments when rejecting a draft."""
        if info.data.get("status") == DraftStatus.REJECTED and not v:
            raise ValueError("Review comments are required when rejecting a draft")
        return v


class DraftResponse(BaseModel):
    """Schema for draft response data."""

    id: UUID
    title: str
    slug: str
    target_path: str
    content: str
    frontmatter: str | None
    status: DraftStatus
    author_id: UUID
    reviewer_id: UUID | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    published_at: datetime | None
    review_comments: str | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DraftListItem(BaseModel):
    """Schema for draft list item (summary view)."""

    id: UUID
    title: str
    slug: str
    target_path: str
    status: DraftStatus
    author_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DraftPublishRequest(BaseModel):
    """Schema for publishing a draft to Git."""

    commit_message: str | None = Field(
        None,
        max_length=500,
        description="Custom commit message (auto-generated if not provided)",
    )
    branch: str = Field(default="main", description="Target Git branch")


class DraftSubmitForReview(BaseModel):
    """Schema for submitting a draft for review."""

    reviewer_id: UUID | None = Field(
        None, description="ID of specific reviewer (optional, can be auto-assigned)"
    )
    notes: str | None = Field(None, description="Notes for the reviewer")
