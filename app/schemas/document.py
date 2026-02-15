"""
Document management schemas.

Defines request/response models for document operations
including creation, updates, and Git integration.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentBase(BaseModel):
    """Base document schema with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(..., min_length=1, description="Markdown content")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v


class DocumentFrontmatter(BaseModel):
    """Schema for document frontmatter metadata."""

    title: str | None = None
    description: str | None = None
    author: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    team: str | None = None
    version: str | None = None
    date: datetime | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    path: str = Field(
        ...,
        min_length=1,
        description="Target path in Git repository (e.g., 'docs/api/authentication.md')",
    )
    frontmatter: DocumentFrontmatter | None = Field(
        None, description="Document metadata"
    )
    commit_message: str | None = Field(
        None,
        max_length=500,
        description="Custom commit message (auto-generated if not provided)",
    )
    branch: str = Field(default="main", description="Target Git branch")

    @field_validator("path")
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Validate document path format."""
        if not v.endswith(".md"):
            raise ValueError("Document path must end with .md extension")
        if v.startswith("/"):
            raise ValueError("Document path should not start with /")
        if ".." in v:
            raise ValueError(
                "Document path cannot contain .. (parent directory references)"
            )
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    frontmatter: DocumentFrontmatter | None = None
    commit_message: str | None = Field(None, max_length=500)

    @field_validator("content")
    @classmethod
    def validate_content_if_provided(cls, v: str | None) -> str | None:
        """Ensure content is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v


class GitCommitInfo(BaseModel):
    """Schema for Git commit information."""

    sha: str = Field(..., description="Git commit SHA")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Commit author")
    date: datetime = Field(..., description="Commit timestamp")
    url: str = Field(..., description="GitHub URL to commit")


class DocumentResponse(BaseModel):
    """Schema for document response data."""

    path: str = Field(..., description="Document path in repository")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Markdown content")
    frontmatter: DocumentFrontmatter | None = Field(
        None, description="Document metadata"
    )
    last_modified: datetime = Field(..., description="Last modification timestamp")
    last_commit: GitCommitInfo | None = Field(None, description="Last Git commit info")
    size: int = Field(..., description="File size in bytes")
    url: str = Field(..., description="GitHub URL to document")

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    """Schema for document list item (summary view)."""

    path: str
    title: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    last_modified: datetime
    author: str | None = None
    size: int

    model_config = {"from_attributes": True}


class DocumentSearchResult(BaseModel):
    """Schema for document search results."""

    path: str
    title: str
    description: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    excerpt: str | None = Field(
        None, description="Content excerpt with search term highlighted"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Search relevance score"
    )

    model_config = {"from_attributes": True}


class DocumentMoveRequest(BaseModel):
    """Schema for moving/renaming a document."""

    new_path: str = Field(..., min_length=1, description="New path for the document")
    commit_message: str | None = Field(None, max_length=500)

    @field_validator("new_path")
    @classmethod
    def validate_new_path_format(cls, v: str) -> str:
        """Validate new document path format."""
        if not v.endswith(".md"):
            raise ValueError("Document path must end with .md extension")
        if v.startswith("/"):
            raise ValueError("Document path should not start with /")
        if ".." in v:
            raise ValueError(
                "Document path cannot contain .. (parent directory references)"
            )
        return v


class DocumentDeleteRequest(BaseModel):
    """Schema for deleting a document."""

    commit_message: str | None = Field(None, max_length=500)
    permanent: bool = Field(
        default=False,
        description="If true, delete permanently; otherwise mark as deleted",
    )
