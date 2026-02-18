"""
Media service for file uploads and asset management.

Handles image uploads, optimization, and storage using
Supabase Storage with automatic compression.
"""

import io
from typing import Any

from PIL import Image

from app.core.config import settings
from app.core.exceptions import FileUploadError
from app.core.logging import get_logger
from app.services.supabase_service import SupabaseService
from app.utils.file_helpers import sanitize_filename

logger = get_logger(__name__)


class MediaService:
    """
    Service for media file operations.

    Provides image upload, optimization, and management
    using Supabase Storage.
    """

    def __init__(self) -> None:
        """Initialize media service."""
        self.supabase = SupabaseService()
        self.bucket = settings.SUPABASE_BUCKET_NAME

    async def upload_image(
        self,
        file_data: bytes,
        filename: str,
        optimize: bool = True,
        max_width: int = 1920,
        quality: int = 85,
    ) -> dict[str, Any]:
        """
        Upload and optionally optimize an image.

        Args:
            file_data: Image file data
            filename: Original filename
            optimize: Whether to optimize image
            max_width: Maximum width for optimization
            quality: JPEG quality (1-100)

        Returns:
            Dictionary with upload information

        Raises:
            FileUploadError: If upload or optimization fails
        """
        try:
            # Sanitize filename
            safe_filename = sanitize_filename(filename)

            # Optimize if requested
            if optimize:
                file_data, content_type = await self._optimize_image(
                    file_data, max_width=max_width, quality=quality
                )
            else:
                content_type = self._get_content_type(filename)

            # Validate file size
            if len(file_data) > settings.MAX_UPLOAD_SIZE:
                raise FileUploadError(
                    f"File size exceeds maximum: {settings.MAX_UPLOAD_SIZE} bytes"
                )

            # Generate storage path
            path = f"images/{safe_filename}"

            logger.info(f"Uploading image: {path}")

            # Upload to Supabase Storage
            result = await self.supabase.upload_file(
                bucket=self.bucket,
                path=path,
                file_data=file_data,
                content_type=content_type,
            )

            return {
                "filename": safe_filename,
                "path": path,
                "url": result["public_url"],
                "size": result["size"],
                "content_type": content_type,
            }

        except FileUploadError:
            raise
        except Exception as e:
            logger.error(f"Error uploading image {filename}: {e}")
            raise FileUploadError(f"Failed to upload image: {str(e)}") from e

    async def _optimize_image(
        self,
        file_data: bytes,
        max_width: int = 1920,
        quality: int = 85,
    ) -> tuple[bytes, str]:
        """
        Optimize image by resizing and compressing.

        Args:
            file_data: Original image data
            max_width: Maximum width
            quality: JPEG quality

        Returns:
            Tuple of (optimized data, content type)
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(file_data))

            # Convert RGBA to RGB if necessary
            if image.mode == "RGBA":
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                image = rgb_image

            # Resize if wider than max_width
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save optimized image
            output = io.BytesIO()

            # Determine format
            if image.format in ["JPEG", "JPG"]:
                image.save(output, format="JPEG", quality=quality, optimize=True)
                content_type = "image/jpeg"
            elif image.format == "PNG":
                image.save(output, format="PNG", optimize=True)
                content_type = "image/png"
            elif image.format == "WEBP":
                image.save(output, format="WEBP", quality=quality)
                content_type = "image/webp"
            else:
                # Default to JPEG
                image.save(output, format="JPEG", quality=quality, optimize=True)
                content_type = "image/jpeg"

            return output.getvalue(), content_type

        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            raise FileUploadError(f"Failed to optimize image: {str(e)}") from e

    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename."""
        ext = filename.lower().split(".")[-1]

        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }

        return content_types.get(ext, "application/octet-stream")

    async def delete_image(self, path: str) -> None:
        """
        Delete an image from storage.

        Args:
            path: Image path in storage
        """
        try:
            logger.info(f"Deleting image: {path}")
            await self.supabase.delete_file(self.bucket, path)
        except Exception as e:
            logger.error(f"Error deleting image {path}: {e}")
            raise

    async def list_images(self, directory: str = "images") -> list[dict[str, Any]]:
        """
        List images in storage.

        Args:
            directory: Directory to list

        Returns:
            List of image information
        """
        try:
            return await self.supabase.list_files(self.bucket, directory)
        except Exception as e:
            logger.error(f"Error listing images: {e}")
            raise
