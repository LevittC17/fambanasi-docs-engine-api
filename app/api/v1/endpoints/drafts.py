"""
Draft management endpoints.

Provides CRUD operations and review workflow for unpublished drafts.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_editor, get_current_user, get_db
from app.core.logging import get_logger
from app.db.models.draft import DraftStatus
from app.db.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.draft import (
    DraftCreate,
    DraftListItem,
    DraftResponse,
    DraftStatusUpdate,
    DraftUpdate,
)
from app.services.draft_service import DraftService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=DraftResponse, status_code=201)
async def create_draft(
    draft: DraftCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DraftResponse:
    """
    Create a new draft.

    Args:
        draft: Draft creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created draft
    """
    draft_service = DraftService()
    created_draft = await draft_service.create_draft(
        db=db,
        draft_data=draft,
        author=current_user,
    )

    return DraftResponse.model_validate(created_draft)


@router.get("/{draft_id}", response_model=DraftResponse)
async def get_draft(
    draft_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DraftResponse:
    """
    Get draft by ID.

    Args:
        draft_id: Draft ID
        db: Database session

    Returns:
        Draft information
    """
    draft_service = DraftService()
    draft = await draft_service.get_draft(db=db, draft_id=draft_id)

    return DraftResponse.model_validate(draft)


@router.put("/{draft_id}", response_model=DraftResponse)
async def update_draft(
    draft_id: UUID,
    draft_update: DraftUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DraftResponse:
    """
    Update a draft.

    Args:
        draft_id: Draft ID
        draft_update: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated draft
    """
    draft_service = DraftService()
    updated_draft = await draft_service.update_draft(
        db=db,
        draft_id=draft_id,
        draft_update=draft_update,
        user=current_user,
    )

    return DraftResponse.model_validate(updated_draft)


@router.delete("/{draft_id}", status_code=204)
async def delete_draft(
    draft_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a draft.

    Args:
        draft_id: Draft ID
        current_user: Current authenticated user
        db: Database session
    """
    draft_service = DraftService()
    await draft_service.delete_draft(
        db=db,
        draft_id=draft_id,
        user=current_user,
    )


@router.post("/{draft_id}/submit", response_model=DraftResponse)
async def submit_draft_for_review(
    draft_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    reviewer_id: UUID | None = None,
) -> DraftResponse:
    """
    Submit draft for review.

    Args:
        draft_id: Draft ID
        current_user: Current authenticated user
        db: Database session
        reviewer_id: Optional specific reviewer

    Returns:
        Updated draft
    """
    draft_service = DraftService()
    updated_draft = await draft_service.submit_for_review(
        db=db,
        draft_id=draft_id,
        user=current_user,
        reviewer_id=reviewer_id,
    )

    return DraftResponse.model_validate(updated_draft)


@router.post("/{draft_id}/review", response_model=DraftResponse)
async def review_draft(
    draft_id: UUID,
    status_update: DraftStatusUpdate,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DraftResponse:
    """
    Review draft (approve/reject).

    Requires Editor role or higher.

    Args:
        draft_id: Draft ID
        status_update: Status update (approve/reject with comments)
        current_user: Current authenticated user (reviewer)
        db: Database session

    Returns:
        Updated draft
    """
    draft_service = DraftService()
    updated_draft = await draft_service.update_draft_status(
        db=db,
        draft_id=draft_id,
        status_update=status_update,
        reviewer=current_user,
    )

    return DraftResponse.model_validate(updated_draft)


@router.post("/{draft_id}/publish")
async def publish_draft(
    draft_id: UUID,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    commit_message: str | None = None,
    branch: str | None = None,
) -> dict[str, Any]:
    """
    Publish draft to Git repository.

    Requires Editor role or higher.

    Args:
        draft_id: Draft ID
        current_user: Current authenticated user
        db: Database session
        commit_message: Optional custom commit message
        branch: Optional target branch

    Returns:
        Published document information
    """
    draft_service = DraftService()
    result = await draft_service.publish_draft(
        db=db,
        draft_id=draft_id,
        user=current_user,
        commit_message=commit_message,
        branch=branch,
    )

    return result


@router.get("/", response_model=PaginatedResponse[DraftListItem])
async def list_drafts(
    db: Annotated[AsyncSession, Depends(get_db)],
    author_id: UUID | None = None,
    status: DraftStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[DraftListItem]:
    """
    List drafts with filtering and pagination.

    Args:
        db: Database session
        author_id: Filter by author
        status: Filter by status
        page: Page number
        page_size: Items per page

    Returns:
        Paginated list of drafts
    """
    draft_service = DraftService()
    offset = (page - 1) * page_size

    drafts, total = await draft_service.list_drafts(
        db=db,
        author_id=author_id,
        status=status,
        limit=page_size,
        offset=offset,
    )

    # Convert to list items
    draft_items = [DraftListItem.model_validate(d) for d in drafts]

    return PaginatedResponse[DraftListItem](
        items=draft_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=offset + page_size < total,
        has_previous=page > 1,
    )
