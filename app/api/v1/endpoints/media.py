"""
Media management endpoints.

Provides image and file upload, optimization, and management
using Supabase Storage as the backend.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import get_current_editor
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.user import User
from app.services.media_service import MediaService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", status_code=201)
async def upload_media(
    file: Annotated[UploadFile, File(description="Image or document file to upload")],
    current_user: Annotated[User, Depends(get_current_editor)],
    optimize: bool = True,
) -> dict[str, Any]:
    """
    Upload a media file.

    Accepts images and documents, automatically optimizing images
    for web delivery. Returns public URL for use in documentation.

    Requires Editor role or higher.

    Args:
        file: Uploaded file
        current_user: Current authenticated user
        optimize: Whether to optimize images (default True)

    Returns:
        Upload result with public URL and file information
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Check content type
    content_type = file.content_type or ""
    allowed_types = settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_DOCUMENT_TYPES

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type not allowed: {content_type}. Allowed: {allowed_types}",
        )

    # Read file data
    file_data = await file.read()

    # Check file size
    if len(file_data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE} bytes",
        )

    # Upload based on type
    media_service = MediaService()

    if content_type in settings.ALLOWED_IMAGE_TYPES:
        result = await media_service.upload_image(
            file_data=file_data,
            filename=file.filename,
            optimize=optimize,
        )
    else:
        # Handle document upload
        from app.services.supabase_service import SupabaseService
        from app.utils.file_helpers import sanitize_filename

        supabase = SupabaseService()
        safe_filename = sanitize_filename(file.filename)
        path = f"documents/{safe_filename}"

        result = await supabase.upload_file(
            bucket=settings.SUPABASE_BUCKET_NAME,
            path=path,
            file_data=file_data,
            content_type=content_type,
        )
        result["filename"] = safe_filename

    logger.info(f"File uploaded by {current_user.email}: {result.get('filename')}")

    return result


@router.get("/")
async def list_media(
    current_user: Annotated[User, Depends(get_current_editor)],
    directory: str = "images",
) -> list[dict[str, Any]]:
    """
    List uploaded media files.

    Requires Editor role or higher.

    Args:
        current_user: Current authenticated user
        directory: Directory to list (images, documents)

    Returns:
        List of media file information
    """
    media_service = MediaService()
    return await media_service.list_images(directory=directory)


@router.delete("/{path:path}", status_code=204)
async def delete_media(
    path: str,
    current_user: Annotated[User, Depends(get_current_editor)],
) -> None:
    """
    Delete a media file.

    Requires Editor role or higher.

    Args:
        path: Media file path in storage
        current_user: Current authenticated user
    """
    media_service = MediaService()
    await media_service.delete_image(path=path)

    logger.info(f"Media deleted by {current_user.email}: {path}")
