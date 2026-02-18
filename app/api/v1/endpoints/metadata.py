"""
Metadata management endpoints.

Provides document metadata operations including search, filtering,
analytics, and bulk updates.
"""

from datetime import UTC
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_current_editor, get_db
from app.core.logging import get_logger
from app.db.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.metadata import (
    DocumentMetadataResponse,
    MetadataBulkUpdate,
    MetadataCreate,
    MetadataStatsResponse,
    MetadataUpdate,
)
from app.services.metadata_service import MetadataService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse[DocumentMetadataResponse])
async def list_metadata(
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str | None = Query(None, description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    tags: list[str] = Query(default=[], description="Filter by tags"),
    team: str | None = Query(None, description="Filter by team"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[DocumentMetadataResponse]:
    """
    List and filter document metadata.

    Supports searching by query text and filtering by category,
    tags, and team for advanced document discovery.

    Args:
        db: Database session
        query: Optional text search query
        category: Optional category filter
        tags: Optional tag filters
        team: Optional team filter
        page: Page number
        page_size: Items per page

    Returns:
        Paginated list of document metadata
    """
    metadata_service = MetadataService()
    offset = (page - 1) * page_size

    metadata_list, total = await metadata_service.search_metadata(
        db=db,
        query=query,
        category=category,
        tags=tags if tags else None,
        team=team,
        limit=page_size,
        offset=offset,
    )

    items = [DocumentMetadataResponse.model_validate(m) for m in metadata_list]

    return PaginatedResponse[DocumentMetadataResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=offset + page_size < total,
        has_previous=page > 1,
    )


@router.get("/stats", response_model=MetadataStatsResponse)
async def get_metadata_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetadataStatsResponse:
    """
    Get documentation analytics and statistics.

    Returns aggregate statistics including document counts by
    category/team, average word counts, and freshness metrics.

    Args:
        db: Database session

    Returns:
        Metadata statistics
    """
    from datetime import datetime

    metadata_service = MetadataService()
    stats = await metadata_service.get_metadata_stats(db=db)

    return MetadataStatsResponse(
        total_documents=stats["total_documents"],
        categories=stats["categories"],
        teams=stats["teams"],
        tags=stats["tags"],
        avg_word_count=stats["avg_word_count"],
        avg_reading_time=stats["avg_reading_time"],
        last_updated=(
            datetime.fromisoformat(stats["last_updated"])
            if stats.get("last_updated")
            else datetime.now(UTC)
        ),
    )


@router.get("/{metadata_id}", response_model=DocumentMetadataResponse)
async def get_metadata(
    metadata_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadataResponse:
    """
    Get metadata by ID.

    Args:
        metadata_id: Metadata record ID
        db: Database session

    Returns:
        Document metadata
    """
    metadata_service = MetadataService()
    metadata = await metadata_service.get_metadata(db=db, metadata_id=metadata_id)

    return DocumentMetadataResponse.model_validate(metadata)


@router.post("/", response_model=DocumentMetadataResponse, status_code=201)
async def create_metadata(
    metadata: MetadataCreate,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadataResponse:
    """
    Create metadata for a document.

    Requires Editor role or higher.

    Args:
        metadata: Metadata to create
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created metadata record
    """
    metadata_service = MetadataService()
    created = await metadata_service.create_metadata(db=db, metadata=metadata)

    return DocumentMetadataResponse.model_validate(created)


@router.put("/{metadata_id}", response_model=DocumentMetadataResponse)
async def update_metadata(
    metadata_id: UUID,
    metadata_update: MetadataUpdate,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadataResponse:
    """
    Update document metadata.

    Requires Editor role or higher.

    Args:
        metadata_id: Metadata record ID
        metadata_update: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated metadata
    """
    metadata_service = MetadataService()
    updated = await metadata_service.update_metadata(
        db=db,
        metadata_id=metadata_id,
        metadata_update=metadata_update,
    )

    return DocumentMetadataResponse.model_validate(updated)


@router.delete("/{metadata_id}", status_code=204)
async def delete_metadata(
    metadata_id: UUID,
    current_user: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete metadata record.

    Requires Admin role.

    Args:
        metadata_id: Metadata record ID
        current_user: Current authenticated user (admin)
        db: Database session
    """
    metadata_service = MetadataService()
    await metadata_service.delete_metadata(db=db, metadata_id=metadata_id)


@router.put("/bulk", response_model=dict)
async def bulk_update_metadata(
    bulk_update: MetadataBulkUpdate,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Bulk update metadata for multiple documents.

    Applies the same metadata updates to all specified documents.
    Requires Editor role or higher.

    Args:
        bulk_update: Bulk update request with file paths and updates
        current_user: Current authenticated user
        db: Database session

    Returns:
        Summary of update results
    """
    metadata_service = MetadataService()
    updated_count = 0
    failed_paths = []

    for file_path in bulk_update.file_paths:
        try:
            existing = await metadata_service.get_metadata_by_path(db, file_path)
            if existing:
                await metadata_service.update_metadata(
                    db=db,
                    metadata_id=existing.id,
                    metadata_update=bulk_update.updates,
                )
                updated_count += 1
            else:
                failed_paths.append(file_path)
        except Exception as e:
            logger.error(f"Bulk update failed for {file_path}: {e}")
            failed_paths.append(file_path)

    return {
        "updated": updated_count,
        "failed": len(failed_paths),
        "failed_paths": failed_paths,
    }
