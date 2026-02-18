"""
Document metadata schemas.

Defines request/response models for document metadata
used in search indexing and categorization.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetadataBase(BaseModel):
    """Base metadata schema with common fields."""

    file_path: str = Field(..., description="Full path to document in Git repository")
    title: str = Field(..., description="Document title")
    slug: str = Field(..., description="URL-friendly slug")


class MetadataCreate(MetadataBase):
    """Schema for creating document metadata."""

    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    team: str | None = None
    description: str | None = None
    author: str | None = None
    version: str | None = None
    git_sha: str | None = None
    git_url: str | None = None
    word_count: int | None = None
    reading_time: int | None = None
    custom_fields: dict | None = None


class MetadataUpdate(BaseModel):
    """Schema for updating document metadata."""

    title: str | None = None
    slug: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    team: str | None = None
    description: str | None = None
    author: str | None = None
    version: str | None = None
    git_sha: str | None = None
    git_url: str | None = None
    word_count: int | None = None
    reading_time: int | None = None
    custom_fields: dict | None = None


class DocumentMetadataResponse(MetadataBase):
    """Schema for metadata response data."""

    id: UUID
    category: str | None
    tags: list[str]
    team: str | None
    description: str | None
    author: str | None
    version: str | None
    git_sha: str | None
    git_url: str | None
    word_count: int | None
    reading_time: int | None
    custom_fields: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetadataSearchQuery(BaseModel):
    """Schema for metadata search/filter query."""

    query: str | None = Field(None, description="Search query string")
    category: str | None = Field(None, description="Filter by category")
    tags: list[str] = Field(default_factory=list, description="Filter by tags")
    team: str | None = Field(None, description="Filter by team")
    author: str | None = Field(None, description="Filter by author")
    version: str | None = Field(None, description="Filter by version")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class MetadataBulkUpdate(BaseModel):
    """Schema for bulk metadata updates."""

    file_paths: list[str] = Field(..., min_length=1, description="List of file paths to update")
    updates: MetadataUpdate = Field(..., description="Updates to apply to all specified documents")


class MetadataStatsResponse(BaseModel):
    """Schema for metadata statistics."""

    total_documents: int
    categories: dict[str, int] = Field(description="Document count by category")
    teams: dict[str, int] = Field(description="Document count by team")
    tags: dict[str, int] = Field(description="Document count by tag")
    avg_word_count: float | None
    avg_reading_time: float | None
    last_updated: datetime
