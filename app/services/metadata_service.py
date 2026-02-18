"""
Metadata service for document metadata management.

Handles caching, indexing, and querying of document metadata
for fast search and analytics without hitting Git repository.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.core.logging import get_logger
from app.db.models.metadata import DocumentMetadata
from app.schemas.metadata import MetadataCreate, MetadataUpdate
from app.utils.file_helpers import generate_slug
from app.utils.markdown import estimate_reading_time, extract_excerpt, strip_markdown

logger = get_logger(__name__)


class MetadataService:
    """
    Service for document metadata operations.

    Manages metadata cache for fast search and filtering without
    querying the Git repository for every request.
    """

    async def create_metadata(self, db: AsyncSession, metadata: MetadataCreate) -> DocumentMetadata:
        """
        Create metadata record for a document.

        Args:
            db: Database session
            metadata: Metadata to create

        Returns:
            Created metadata record
        """
        try:
            logger.info(f"Creating metadata for: {metadata.file_path}")

            db_metadata = DocumentMetadata(
                file_path=metadata.file_path,
                title=metadata.title,
                slug=metadata.slug or generate_slug(metadata.title),
                category=metadata.category,
                tags=metadata.tags,
                team=metadata.team,
                description=metadata.description,
                author=metadata.author,
                version=metadata.version,
                git_sha=metadata.git_sha,
                git_url=metadata.git_url,
                word_count=metadata.word_count,
                reading_time=metadata.reading_time,
                custom_fields=metadata.custom_fields,
            )

            db.add(db_metadata)
            await db.commit()
            await db.refresh(db_metadata)

            logger.info(f"Metadata created with ID: {db_metadata.id}")
            return db_metadata

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating metadata: {e}")
            raise

    async def get_metadata(self, db: AsyncSession, metadata_id: UUID) -> DocumentMetadata:
        """
        Get metadata by ID.

        Args:
            db: Database session
            metadata_id: Metadata record ID

        Returns:
            Metadata record

        Raises:
            ResourceNotFoundError: If metadata not found
        """
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == metadata_id)
        )
        metadata = result.scalar_one_or_none()

        if not metadata:
            raise ResourceNotFoundError("Metadata", str(metadata_id))

        return metadata

    async def get_metadata_by_path(
        self, db: AsyncSession, file_path: str
    ) -> DocumentMetadata | None:
        """
        Get metadata by file path.

        Args:
            db: Database session
            file_path: Document file path

        Returns:
            Metadata record or None if not found
        """
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.file_path == file_path)
        )
        return result.scalar_one_or_none()

    async def update_metadata(
        self, db: AsyncSession, metadata_id: UUID, metadata_update: MetadataUpdate
    ) -> DocumentMetadata:
        """
        Update metadata record.

        Args:
            db: Database session
            metadata_id: Metadata record ID
            metadata_update: Fields to update

        Returns:
            Updated metadata record

        Raises:
            ResourceNotFoundError: If metadata not found
        """
        try:
            # Get existing metadata
            db_metadata = await self.get_metadata(db, metadata_id)

            logger.info(f"Updating metadata: {metadata_id}")

            # Update fields
            update_data = metadata_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_metadata, field, value)

            await db.commit()
            await db.refresh(db_metadata)

            return db_metadata

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating metadata {metadata_id}: {e}")
            raise

    async def delete_metadata(self, db: AsyncSession, metadata_id: UUID) -> None:
        """
        Delete metadata record.

        Args:
            db: Database session
            metadata_id: Metadata record ID

        Raises:
            ResourceNotFoundError: If metadata not found
        """
        try:
            # Verify metadata exists
            await self.get_metadata(db, metadata_id)

            logger.info(f"Deleting metadata: {metadata_id}")

            await db.execute(delete(DocumentMetadata).where(DocumentMetadata.id == metadata_id))
            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting metadata {metadata_id}: {e}")
            raise

    async def delete_metadata_by_path(self, db: AsyncSession, file_path: str) -> None:
        """
        Delete metadata by file path.

        Args:
            db: Database session
            file_path: Document file path
        """
        try:
            logger.info(f"Deleting metadata for path: {file_path}")

            await db.execute(
                delete(DocumentMetadata).where(DocumentMetadata.file_path == file_path)
            )
            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting metadata for {file_path}: {e}")
            raise

    async def upsert_metadata(
        self, db: AsyncSession, file_path: str, metadata: MetadataCreate
    ) -> DocumentMetadata:
        """
        Create or update metadata (upsert operation).

        Args:
            db: Database session
            file_path: Document file path
            metadata: Metadata to upsert

        Returns:
            Created or updated metadata record
        """
        existing = await self.get_metadata_by_path(db, file_path)

        if existing:
            # Update existing
            update_data = MetadataUpdate(**metadata.model_dump())
            return await self.update_metadata(db, existing.id, update_data)
        else:
            # Create new
            return await self.create_metadata(db, metadata)

    async def sync_metadata_from_content(
        self,
        db: AsyncSession,
        file_path: str,
        content: str,
        frontmatter: dict[str, Any],
        git_sha: str | None = None,
        git_url: str | None = None,
    ) -> DocumentMetadata:
        """
        Sync metadata from document content and frontmatter.

        Automatically extracts metadata from document content.

        Args:
            db: Database session
            file_path: Document file path
            content: Document content
            frontmatter: Parsed frontmatter
            git_sha: Git commit SHA
            git_url: GitHub URL

        Returns:
            Synced metadata record
        """
        try:
            logger.info(f"Syncing metadata for: {file_path}")

            # Extract or use frontmatter values
            title = frontmatter.get("title", file_path.split("/")[-1].replace(".md", ""))

            # Calculate content metrics
            plain_text = strip_markdown(content)
            word_count = len(plain_text.split())
            reading_time = estimate_reading_time(content)
            description = frontmatter.get("description") or extract_excerpt(content)

            metadata = MetadataCreate(
                file_path=file_path,
                title=title,
                slug=generate_slug(title),
                category=frontmatter.get("category"),
                tags=frontmatter.get("tags", []),
                team=frontmatter.get("team"),
                description=description,
                author=frontmatter.get("author"),
                version=frontmatter.get("version"),
                git_sha=git_sha,
                git_url=git_url,
                word_count=word_count,
                reading_time=reading_time,
                custom_fields=frontmatter.get("custom_fields"),
            )

            return await self.upsert_metadata(db, file_path, metadata)

        except Exception as e:
            logger.error(f"Error syncing metadata for {file_path}: {e}")
            raise

    async def search_metadata(
        self,
        db: AsyncSession,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        team: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DocumentMetadata], int]:
        """
        Search and filter metadata.

        Args:
            db: Database session
            query: Search query string
            category: Filter by category
            tags: Filter by tags
            team: Filter by team
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Tuple of (metadata list, total count)
        """
        stmt = select(DocumentMetadata)

        # Apply filters
        if query:
            stmt = stmt.where(
                DocumentMetadata.title.ilike(f"%{query}%")
                | DocumentMetadata.description.ilike(f"%{query}%")
            )

        if category:
            stmt = stmt.where(DocumentMetadata.category == category)

        if tags:
            # PostgreSQL array contains check
            stmt = stmt.where(DocumentMetadata.tags.contains(tags))

        if team:
            stmt = stmt.where(DocumentMetadata.team == team)

        # Get total count
        count_stmt = select(DocumentMetadata).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = len(total_result.all())

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        # Execute query
        result = await db.execute(stmt)
        metadata_list = result.scalars().all()

        return list(metadata_list), total

    async def get_metadata_stats(self, db: AsyncSession) -> dict[str, Any]:
        """
        Get metadata statistics.

        Args:
            db: Database session

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func

        # Total documents
        total_result = await db.execute(select(func.count(DocumentMetadata.id)))
        total_documents = total_result.scalar()

        # Categories count
        categories_result = await db.execute(
            select(DocumentMetadata.category, func.count(DocumentMetadata.id)).group_by(
                DocumentMetadata.category
            )
        )
        categories = {cat: count for cat, count in categories_result.all() if cat}

        # Average metrics
        avg_result = await db.execute(
            select(
                func.avg(DocumentMetadata.word_count),
                func.avg(DocumentMetadata.reading_time),
            )
        )
        avg_word_count, avg_reading_time = avg_result.one()

        # Last updated
        latest_result = await db.execute(select(func.max(DocumentMetadata.updated_at)))
        last_updated = latest_result.scalar()

        return {
            "total_documents": total_documents or 0,
            "categories": categories,
            "teams": {},  # TODO: Implement teams aggregation
            "tags": {},  # TODO: Implement tags aggregation
            "avg_word_count": float(avg_word_count) if avg_word_count else None,
            "avg_reading_time": float(avg_reading_time) if avg_reading_time else None,
            "last_updated": last_updated.isoformat() if last_updated else None,
        }
