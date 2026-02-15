"""
Document metadata model for search and categorization.

Stores metadata extracted from document frontmatter and used for
Pagefind search indexing and filtering.
"""

from sqlalchemy import ARRAY, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DocumentMetadata(Base, TimestampMixin):
    """
    Document metadata for search and categorization.

    Caches metadata from Git repository documents to enable
    fast search filtering and analytics without querying Git.
    """

    __tablename__ = "document_metadata"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
        doc="Metadata record ID",
    )

    # Document identification
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
        doc="Full path to document in Git repository",
    )

    title: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True, doc="Document title"
    )

    slug: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True, doc="URL-friendly slug"
    )

    # Categorization
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Primary category (Engineering, Product, Operations, etc.)",
    )

    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, doc="Array of tags for filtering"
    )

    team: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Team or department owning the document",
    )

    # Content metadata
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Short description or excerpt"
    )

    author: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="Document author"
    )

    # Version information
    version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, doc="Documentation version (v1.0, v2.0, etc.)"
    )

    # Git information
    git_sha: Mapped[str | None] = mapped_column(
        String(40), nullable=True, doc="Git commit SHA of last update"
    )

    git_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="GitHub URL to the document"
    )

    # Search optimization
    word_count: Mapped[int | None] = mapped_column(
        nullable=True, doc="Approximate word count"
    )

    reading_time: Mapped[int | None] = mapped_column(
        nullable=True, doc="Estimated reading time in minutes"
    )

    # Additional metadata (flexible JSON)
    custom_fields: Mapped[dict | None] = mapped_column(
        Text, nullable=True, doc="Additional custom metadata as JSON string"
    )

    def __repr__(self) -> str:
        """String representation of metadata."""
        return f"<DocumentMetadata(path={self.file_path}, title={self.title})>"
