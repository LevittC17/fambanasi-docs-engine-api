"""
Document service for high-level document operations.

Orchestrates GitHub, metadata, and audit services to provide
unified document management with full tracking and validation.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.audit_log import AuditAction
from app.db.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentFrontmatter,
    DocumentResponse,
    DocumentUpdate,
    GitCommitInfo,
)
from app.services.audit_service import AuditService
from app.services.github_service import GitHubService
from app.services.metadata_service import MetadataService
from app.utils.file_helpers import combine_frontmatter_and_content, extract_frontmatter
from app.utils.validators import validate_file_path

logger = get_logger(__name__)


class DocumentService:
    """
    Service for document management operations.

    Provides high-level document CRUD operations that orchestrate
    GitHub, metadata, and audit services for complete document lifecycle.
    """

    def __init__(self) -> None:
        """Initialize document service with dependencies."""
        self.github = GitHubService()
        self.metadata = MetadataService()
        self.audit = AuditService()

    async def get_document(
        self,
        path: str,
        branch: str | None = None,
    ) -> DocumentResponse:
        """
        Get document by path.

        Args:
            path: Document path in repository
            branch: Branch name (defaults to main)

        Returns:
            Document with content and metadata

        Raises:
            ResourceNotFoundError: If document doesn't exist
        """
        try:
            # Validate path
            validate_file_path(path)

            logger.info(f"Getting document: {path}")

            # Get file from GitHub
            file_info = await self.github.get_file(path, branch)

            # Extract frontmatter
            frontmatter_dict, content = extract_frontmatter(file_info["content"])

            # Create frontmatter schema
            frontmatter = DocumentFrontmatter(**frontmatter_dict) if frontmatter_dict else None

            # Create commit info
            last_commit = None
            if file_info.get("last_commit"):
                last_commit = GitCommitInfo(**file_info["last_commit"])

            return DocumentResponse(
                path=path,
                title=frontmatter.title if frontmatter and frontmatter.title else path.split("/")[-1].replace(".md", ""),
                content=content,
                frontmatter=frontmatter,
                last_modified=file_info["last_modified"],
                last_commit=last_commit,
                size=file_info["size"],
                url=file_info["url"],
            )

        except Exception as e:
            logger.error(f"Error getting document {path}: {e}")
            raise

    async def create_document(
        self,
        db: AsyncSession,
        document: DocumentCreate,
        user: User,
        ip_address: str | None = None,
    ) -> DocumentResponse:
        """
        Create a new document.

        Args:
            db: Database session
            document: Document creation data
            user: User creating the document
            ip_address: IP address of request

        Returns:
            Created document

        Raises:
            ValidationError: If document data is invalid
        """
        try:
            # Validate path
            validate_file_path(document.path)

            logger.info(f"Creating document: {document.path}")

            # Prepare content with frontmatter
            frontmatter_dict = document.frontmatter.model_dump() if document.frontmatter else {}
            full_content = combine_frontmatter_and_content(frontmatter_dict, document.content)

            # Create file in GitHub
            result = await self.github.create_file(
                path=document.path,
                content=full_content,
                message=document.commit_message,
                branch=document.branch,
            )

            # Sync metadata
            await self.metadata.sync_metadata_from_content(
                db=db,
                file_path=document.path,
                content=document.content,
                frontmatter=frontmatter_dict,
                git_sha=result["commit"]["sha"],
                git_url=result["commit"]["url"],
            )

            # Log audit trail
            await self.audit.log_document_create(
                db=db,
                user=user,
                document_path=document.path,
                title=document.title,
                ip_address=ip_address,
            )

            # Return created document
            return await self.get_document(document.path, document.branch)

        except Exception as e:
            logger.error(f"Error creating document {document.path}: {e}")
            raise

    async def update_document(
        self,
        db: AsyncSession,
        path: str,
        document: DocumentUpdate,
        user: User,
        ip_address: str | None = None,
        branch: str | None = None,
    ) -> DocumentResponse:
        """
        Update an existing document.

        Args:
            db: Database session
            path: Document path
            document: Document update data
            user: User updating the document
            ip_address: IP address of request
            branch: Branch name

        Returns:
            Updated document

        Raises:
            ResourceNotFoundError: If document doesn't exist
        """
        try:
            # Validate path
            validate_file_path(path)

            logger.info(f"Updating document: {path}")

            # Get current document to merge updates
            current = await self.get_document(path, branch)

            # Merge updates
            title = document.title or current.title
            content = document.content or current.content

            # Merge frontmatter
            current_fm = current.frontmatter.model_dump() if current.frontmatter else {}
            update_fm = document.frontmatter.model_dump() if document.frontmatter else {}
            merged_fm = {**current_fm, **update_fm}

            # Update title in frontmatter if changed
            if document.title:
                merged_fm["title"] = document.title

            # Prepare content with frontmatter
            full_content = combine_frontmatter_and_content(merged_fm, content)

            # Update file in GitHub
            result = await self.github.update_file(
                path=path,
                content=full_content,
                message=document.commit_message,
                branch=branch,
            )

            # Sync metadata
            await self.metadata.sync_metadata_from_content(
                db=db,
                file_path=path,
                content=content,
                frontmatter=merged_fm,
                git_sha=result["commit"]["sha"],
                git_url=result["commit"]["url"],
            )

            # Log audit trail
            await self.audit.log_document_update(
                db=db,
                user=user,
                document_path=path,
                title=title,
                ip_address=ip_address,
            )

            # Return updated document
            return await self.get_document(path, branch)

        except Exception as e:
            logger.error(f"Error updating document {path}: {e}")
            raise

    async def delete_document(
        self,
        db: AsyncSession,
        path: str,
        user: User,
        commit_message: str | None = None,
        ip_address: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a document.

        Args:
            db: Database session
            path: Document path
            user: User deleting the document
            commit_message: Custom commit message
            ip_address: IP address of request
            branch: Branch name

        Returns:
            Dictionary with deletion information

        Raises:
            ResourceNotFoundError: If document doesn't exist
        """
        try:
            # Validate path
            validate_file_path(path)

            logger.info(f"Deleting document: {path}")

            # Get document info before deletion
            document = await self.get_document(path, branch)

            # Delete file from GitHub
            result = await self.github.delete_file(
                path=path,
                message=commit_message,
                branch=branch,
            )

            # Delete metadata
            await self.metadata.delete_metadata_by_path(db, path)

            # Log audit trail
            await self.audit.log_document_delete(
                db=db,
                user=user,
                document_path=path,
                title=document.title,
                ip_address=ip_address,
            )

            return {
                "path": path,
                "title": document.title,
                "deleted": True,
                "commit": result["commit"],
            }

        except Exception as e:
            logger.error(f"Error deleting document {path}: {e}")
            raise

    async def move_document(
        self,
        db: AsyncSession,
        old_path: str,
        new_path: str,
        user: User,
        commit_message: str | None = None,
        ip_address: str | None = None,
        branch: str | None = None,
    ) -> DocumentResponse:
        """
        Move or rename a document.

        Args:
            db: Database session
            old_path: Current document path
            new_path: New document path
            user: User moving the document
            commit_message: Custom commit message
            ip_address: IP address of request
            branch: Branch name

        Returns:
            Moved document

        Raises:
            ResourceNotFoundError: If document doesn't exist
        """
        try:
            # Validate paths
            validate_file_path(old_path)
            validate_file_path(new_path)

            logger.info(f"Moving document: {old_path} -> {new_path}")

            # Get document info before move
            document = await self.get_document(old_path, branch)

            # Move file in GitHub
            result = await self.github.move_file(
                old_path=old_path,
                new_path=new_path,
                message=commit_message,
                branch=branch,
            )

            # Delete old metadata
            await self.metadata.delete_metadata_by_path(db, old_path)

            # Create new metadata
            frontmatter_dict = document.frontmatter.model_dump() if document.frontmatter else {}
            await self.metadata.sync_metadata_from_content(
                db=db,
                file_path=new_path,
                content=document.content,
                frontmatter=frontmatter_dict,
                git_sha=result["create_commit"]["sha"],
                git_url=result["create_commit"]["url"],
            )

            # Log audit trail
            await self.audit.log_action(
                db=db,
                action=AuditAction.DOCUMENT_MOVE,
                description=f"Moved document: {old_path} to {new_path}",
                user_id=user.id,
                resource_type="document",
                resource_id=new_path,
                ip_address=ip_address,
                old_value={"path": old_path},
                new_value={"path": new_path},
            )

            # Return moved document
            return await self.get_document(new_path, branch)

        except Exception as e:
            logger.error(f"Error moving document {old_path} to {new_path}: {e}")
            raise

    async def list_documents(
        self,
        directory: str = "",
        branch: str | None = None,
        recursive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List documents in a directory.

        Args:
            directory: Directory path
            branch: Branch name
            recursive: Whether to list recursively

        Returns:
            List of document information
        """
        try:
            logger.info(f"Listing documents in: {directory or 'root'}")

            files = await self.github.list_files(
                directory=directory,
                branch=branch,
                recursive=recursive,
            )

            # Filter for markdown files only
            return [f for f in files if f["name"].endswith(".md")]

        except Exception as e:
            logger.error(f"Error listing documents in {directory}: {e}")
            raise
