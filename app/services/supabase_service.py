"""
Supabase service for authentication and storage.

Handles user authentication, file storage, and database operations
using Supabase as the backend service.
"""

from typing import Any
from uuid import UUID

from supabase import Client, create_client

from app.core.config import settings
from app.core.exceptions import AuthenticationError, SupabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)


class SupabaseService:
    """
    Service for Supabase operations.

    Provides authentication, storage, and database access through
    Supabase's unified API.
    """

    def __init__(self) -> None:
        """Initialize Supabase client."""
        try:
            self._client: Client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
            )
            logger.info("Supabase service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase service: {e}")
            raise SupabaseError(
                message="Failed to connect to Supabase", details={"error": str(e)}
            ) from e

    async def verify_user(self, user_id: str | UUID) -> dict[str, Any]:
        """
        Verify user exists in Supabase Auth.

        Args:
            user_id: User ID to verify

        Returns:
            User information from Supabase Auth

        Raises:
            AuthenticationError: If user doesn't exist
            SupabaseError: If verification fails
        """
        try:
            user_id_str = str(user_id)

            # Get user from Supabase Auth admin API
            response = self._client.auth.admin.get_user_by_id(user_id_str)

            if not response or not response.user:
                raise AuthenticationError(f"User not found: {user_id}")

            return {
                "id": response.user.id,
                "email": response.user.email,
                "email_confirmed_at": response.user.email_confirmed_at,
                "created_at": response.user.created_at,
                "updated_at": response.user.updated_at,
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error verifying user {user_id}: {e}")
            raise SupabaseError(
                message="Failed to verify user", details={"error": str(e)}
            ) from e

    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: bytes,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload file to Supabase Storage.

        Args:
            bucket: Storage bucket name
            path: File path within bucket
            file_data: File content as bytes
            content_type: MIME type of the file

        Returns:
            Dictionary with file information and public URL

        Raises:
            SupabaseError: If upload fails
        """
        try:
            logger.info(f"Uploading file to {bucket}/{path}")

            # Upload file
            self._client.storage.from_(bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": content_type} if content_type else None,
            )

            # Get public URL
            public_url = self._client.storage.from_(bucket).get_public_url(path)

            return {
                "path": path,
                "bucket": bucket,
                "public_url": public_url,
                "size": len(file_data),
            }

        except Exception as e:
            logger.error(f"Error uploading file to {bucket}/{path}: {e}")
            raise SupabaseError(
                message="Failed to upload file", details={"error": str(e), "path": path}
            ) from e

    async def delete_file(self, bucket: str, path: str) -> None:
        """
        Delete file from Supabase Storage.

        Args:
            bucket: Storage bucket name
            path: File path within bucket

        Raises:
            SupabaseError: If deletion fails
        """
        try:
            logger.info(f"Deleting file from {bucket}/{path}")

            self._client.storage.from_(bucket).remove([path])

        except Exception as e:
            logger.error(f"Error deleting file from {bucket}/{path}: {e}")
            raise SupabaseError(
                message="Failed to delete file", details={"error": str(e), "path": path}
            ) from e

    async def get_file_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """
        Get signed URL for private file.

        Args:
            bucket: Storage bucket name
            path: File path within bucket
            expires_in: URL expiration time in seconds

        Returns:
            Signed URL for file access

        Raises:
            SupabaseError: If URL generation fails
        """
        try:
            response = self._client.storage.from_(bucket).create_signed_url(
                path=path, expires_in=expires_in
            )

            return response["signedURL"]

        except Exception as e:
            logger.error(f"Error getting signed URL for {bucket}/{path}: {e}")
            raise SupabaseError(
                message="Failed to generate file URL",
                details={"error": str(e), "path": path},
            ) from e

    async def list_files(self, bucket: str, path: str = "") -> list[dict[str, Any]]:
        """
        List files in storage bucket.

        Args:
            bucket: Storage bucket name
            path: Directory path to list

        Returns:
            List of file information dictionaries

        Raises:
            SupabaseError: If listing fails
        """
        try:
            response = self._client.storage.from_(bucket).list(path)

            return [
                {
                    "name": item["name"],
                    "id": item.get("id"),
                    "size": item.get("metadata", {}).get("size"),
                    "content_type": item.get("metadata", {}).get("mimetype"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
                for item in response
            ]

        except Exception as e:
            logger.error(f"Error listing files in {bucket}/{path}: {e}")
            raise SupabaseError(
                message="Failed to list files", details={"error": str(e), "path": path}
            ) from e

    async def ensure_bucket_exists(self, bucket: str) -> None:
        """
        Ensure storage bucket exists, create if not.

        Args:
            bucket: Bucket name to check/create

        Raises:
            SupabaseError: If bucket operations fail
        """
        try:
            # Try to list buckets
            buckets = self._client.storage.list_buckets()

            # Check if bucket exists
            if not any(b["name"] == bucket for b in buckets):
                logger.info(f"Creating storage bucket: {bucket}")
                self._client.storage.create_bucket(bucket, {"public": True})

        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise SupabaseError(
                message="Failed to ensure bucket exists",
                details={"error": str(e), "bucket": bucket},
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """
        Check Supabase connectivity.

        Returns:
            Dictionary with health check information
        """
        try:
            # Try to list buckets as a connectivity test
            self._client.storage.list_buckets()

            return {
                "status": "healthy",
                "url": settings.SUPABASE_URL,
            }
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
