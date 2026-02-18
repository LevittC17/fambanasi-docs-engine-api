"""
Document management endpoints.

Provides CRUD operations for documentation files in Git repository.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_editor, get_db
from app.core.logging import get_logger
from app.db.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.document_service import DocumentService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{path:path}", response_model=DocumentResponse)
async def get_document(
    path: str,
    branch: str | None = None,
) -> DocumentResponse:
    """
    Get document by path.

    Args:
        path: Document path in repository
        branch: Optional branch name

    Returns:
        Document with content and metadata
    """
    document_service = DocumentService()
    return await document_service.get_document(path=path, branch=branch)


@router.post("/", response_model=DocumentResponse, status_code=201)
async def create_document(
    document: DocumentCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    """
    Create a new document.

    Requires Editor role or higher.

    Args:
        document: Document creation data
        request: HTTP request for IP address
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created document
    """
    document_service = DocumentService()
    return await document_service.create_document(
        db=db,
        document=document,
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )


@router.put("/{path:path}", response_model=DocumentResponse)
async def update_document(
    path: str,
    document: DocumentUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    branch: str | None = None,
) -> DocumentResponse:
    """
    Update an existing document.

    Requires Editor role or higher.

    Args:
        path: Document path
        document: Document update data
        request: HTTP request for IP address
        current_user: Current authenticated user
        db: Database session
        branch: Optional branch name

    Returns:
        Updated document
    """
    document_service = DocumentService()
    return await document_service.update_document(
        db=db,
        path=path,
        document=document,
        user=current_user,
        ip_address=request.client.host if request.client else None,
        branch=branch,
    )


@router.delete("/{path:path}")
async def delete_document(
    path: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_editor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    commit_message: str | None = None,
    branch: str | None = None,
) -> dict[str, bool]:
    """
    Delete a document.

    Requires Editor role or higher.

    Args:
        path: Document path
        request: HTTP request for IP address
        current_user: Current authenticated user
        db: Database session
        commit_message: Optional custom commit message
        branch: Optional branch name

    Returns:
        Deletion confirmation
    """
    document_service = DocumentService()
    result = await document_service.delete_document(
        db=db,
        path=path,
        user=current_user,
        commit_message=commit_message,
        ip_address=request.client.host if request.client else None,
        branch=branch,
    )

    return {"deleted": result["deleted"]}


@router.get("/")
async def list_documents(
    directory: str = "",
    branch: str | None = None,
    recursive: bool = False,
) -> list[dict[str, Any]]:
    """
    List documents in a directory.

    Args:
        directory: Directory path (empty for root)
        branch: Optional branch name
        recursive: Whether to list recursively

    Returns:
        List of document information
    """
    document_service = DocumentService()
    return await document_service.list_documents(
        directory=directory,
        branch=branch,
        recursive=recursive,
    )
