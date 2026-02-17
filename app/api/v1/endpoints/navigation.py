"""
Navigation endpoints.

Provides folder-aware navigation tree and breadcrumb generation
that mirrors the Git repository structure.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.models.user import User
from app.schemas.navigation import BreadcrumbTrail, NavigationTree
from app.services.navigation_service import NavigationService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/tree", response_model=NavigationTree)
async def get_navigation_tree(
    branch: str | None = Query(None, description="Branch name (defaults to main)"),
) -> NavigationTree:
    """
    Get complete navigation tree.

    Builds hierarchical folder-aware navigation from the Git repository
    structure. Results reflect live repository state.

    Args:
        branch: Optional branch name

    Returns:
        Hierarchical navigation tree with document and folder nodes
    """
    nav_service = NavigationService()
    return await nav_service.build_navigation_tree(branch=branch)


@router.get("/breadcrumbs", response_model=BreadcrumbTrail)
async def get_breadcrumbs(
    path: str = Query(..., description="Document path to generate breadcrumbs for"),
) -> BreadcrumbTrail:
    """
    Get breadcrumb trail for a document path.

    Args:
        path: Document path

    Returns:
        Breadcrumb trail from root to current document
    """
    nav_service = NavigationService()
    items = await nav_service.get_breadcrumbs(path=path)

    return BreadcrumbTrail(items=items)
