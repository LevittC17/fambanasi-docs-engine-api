"""
Search endpoints.

Provides server-side search support and metadata-powered filtering
to complement the client-side Pagefind integration.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.logging import get_logger
from app.schemas.document import DocumentSearchResult
from app.schemas.metadata import MetadataSearchQuery
from app.services.metadata_service import MetadataService
from app.utils.markdown import extract_excerpt

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=list[DocumentSearchResult])
async def search_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(..., min_length=1, description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    tags: list[str] = Query(default=[], description="Filter by tags"),
    team: str | None = Query(None, description="Filter by team"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[DocumentSearchResult]:
    """
    Server-side document search.

    Searches document metadata for the given query with optional
    category, tag, and team filters. Complements client-side Pagefind
    search with server-driven filtering.

    Args:
        db: Database session
        q: Search query string
        category: Optional category filter
        tags: Optional tag filters
        team: Optional team filter
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of matching document search results with relevance scores
    """
    metadata_service = MetadataService()

    metadata_list, _ = await metadata_service.search_metadata(
        db=db,
        query=q,
        category=category,
        tags=tags if tags else None,
        team=team,
        limit=limit,
        offset=offset,
    )

    # Convert to search result format
    results = []
    for meta in metadata_list:
        # Simple relevance scoring based on title match
        title_match = q.lower() in (meta.title or "").lower()
        desc_match = q.lower() in (meta.description or "").lower()

        relevance = 0.0
        if title_match:
            relevance += 0.7
        if desc_match:
            relevance += 0.3

        # Clamp relevance to 0.0 - 1.0
        relevance = min(max(relevance, 0.1), 1.0)

        results.append(
            DocumentSearchResult(
                path=meta.file_path,
                title=meta.title,
                description=meta.description,
                category=meta.category,
                tags=meta.tags or [],
                excerpt=meta.description,
                relevance_score=relevance,
            )
        )

    # Sort by relevance score descending
    results.sort(key=lambda x: x.relevance_score, reverse=True)

    return results


@router.get("/suggestions")
async def get_search_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(..., min_length=1, description="Partial query for suggestions"),
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions"),
) -> list[dict]:
    """
    Get search suggestions for autocomplete.

    Returns quick suggestions based on document titles matching
    the partial query for autocomplete functionality.

    Args:
        db: Database session
        q: Partial search query
        limit: Maximum suggestions to return

    Returns:
        List of suggestion dictionaries with title and path
    """
    metadata_service = MetadataService()

    metadata_list, _ = await metadata_service.search_metadata(
        db=db,
        query=q,
        limit=limit,
        offset=0,
    )

    return [
        {
            "title": meta.title,
            "path": meta.file_path,
            "category": meta.category,
        }
        for meta in metadata_list
    ]


@router.get("/filters")
async def get_search_filters(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get available search filter options.

    Returns all available categories, teams, and popular tags for
    building filter UI in the frontend command palette.

    Args:
        db: Database session

    Returns:
        Available filter options
    """
    metadata_service = MetadataService()
    stats = await metadata_service.get_metadata_stats(db=db)

    return {
        "categories": list(stats["categories"].keys()),
        "teams": list(stats["teams"].keys()),
        "tags": list(stats["tags"].keys()),
    }
