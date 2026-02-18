"""
GitHub service for repository operations.

Handles all interactions with the GitHub API including file operations,
commits, branch management, and webhook processing.
"""

import base64
from datetime import UTC, datetime
from typing import Any

from github import Auth, Github, GithubException, GithubObject, Repository

from app.core.config import settings
from app.core.exceptions import GitHubAPIError, ResourceNotFoundError
from app.core.logging import get_logger
from app.utils.commit_messages import generate_commit_message

logger = get_logger(__name__)


class GitHubService:
    """
    Service for GitHub repository operations.

    Provides high-level methods for document management in the Git repository,
    abstracting away GitHub API complexity and handling errors gracefully.
    """

    def __init__(self) -> None:
        """Initialize GitHub service with authentication."""
        try:
            auth = Auth.Token(settings.GITHUB_TOKEN)
            self._client = Github(auth=auth)
            self._repo: Repository.Repository = self._client.get_repo(
                f"{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}"
            )
            logger.info(
                f"GitHub service initialized for {settings.GITHUB_OWNER}/{settings.GITHUB_REPO}"
            )
        except GithubException as e:
            logger.error(f"Failed to initialize GitHub service: {e}")
            raise GitHubAPIError(
                message="Failed to connect to GitHub", details={"error": str(e)}
            ) from e

    def _get_full_path(self, path: str) -> str:
        """
        Get full path including docs root prefix.

        Args:
            path: Relative path to document

        Returns:
            Full path in repository
        """
        # Remove leading slash if present
        path = path.lstrip("/")

        # Add docs root if not already present
        if not path.startswith(settings.DOCS_ROOT_PATH):
            return f"{settings.DOCS_ROOT_PATH}/{path}"

        return path

    async def get_file(self, path: str, branch: str | None = None) -> dict[str, Any]:
        """
        Get file content and metadata from repository.

        Args:
            path: Path to file in repository
            branch: Branch name (defaults to main)

        Returns:
            Dictionary with file content and metadata

        Raises:
            ResourceNotFoundError: If file doesn't exist
            GitHubAPIError: If GitHub API request fails
        """
        try:
            full_path = self._get_full_path(path)
            branch = branch or settings.GITHUB_BRANCH

            logger.info(f"Fetching file: {full_path} from {branch}")

            # Get file content
            file_content = self._repo.get_contents(full_path, ref=branch)

            if isinstance(file_content, list):
                raise GitHubAPIError(message=f"Path is a directory, not a file: {path}")

            # Decode content
            content = base64.b64decode(file_content.content).decode("utf-8")

            # Get last commit for this file
            commits = self._repo.get_commits(path=full_path, sha=branch)
            last_commit = commits[0] if commits.totalCount > 0 else None

            return {
                "path": path,
                "full_path": full_path,
                "content": content,
                "sha": file_content.sha,
                "size": file_content.size,
                "url": file_content.html_url,
                "last_modified": last_commit.commit.author.date if last_commit else None,
                "last_commit": self._format_commit_info(last_commit) if last_commit else None,
            }

        except GithubException as e:
            if e.status == 404:
                raise ResourceNotFoundError("Document", path) from e
            logger.error(f"GitHub API error getting file {path}: {e}")
            raise GitHubAPIError(
                message=f"Failed to get file: {path}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def create_file(
        self,
        path: str,
        content: str,
        message: str | None = None,
        branch: str | None = None,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new file in the repository.

        Args:
            path: Path where file should be created
            content: File content
            message: Commit message (auto-generated if not provided)
            branch: Target branch (defaults to main)
            author_name: Commit author name
            author_email: Commit author email

        Returns:
            Dictionary with commit information

        Raises:
            GitHubAPIError: If file creation fails
        """
        try:
            full_path = self._get_full_path(path)
            branch = branch or settings.GITHUB_BRANCH

            # Generate commit message if not provided
            if not message:
                message = generate_commit_message(
                    action="create",
                    path=path,
                    title=self._extract_title_from_content(content),
                )

            logger.info(f"Creating file: {full_path} in {branch}")

            # Create file
            result = self._repo.create_file(
                path=full_path,
                message=message,
                content=content,
                branch=branch,
            )

            return {
                "path": path,
                "full_path": full_path,
                "commit": self._format_commit_info(result["commit"]),
                "content_sha": result["content"].sha,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating file {path}: {e}")
            raise GitHubAPIError(
                message=f"Failed to create file: {path}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def update_file(
        self,
        path: str,
        content: str,
        message: str | None = None,
        sha: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing file in the repository.

        Args:
            path: Path to file to update
            content: New file content
            message: Commit message (auto-generated if not provided)
            sha: Current file SHA (fetched if not provided)
            branch: Target branch (defaults to main)

        Returns:
            Dictionary with commit information

        Raises:
            ResourceNotFoundError: If file doesn't exist
            GitHubAPIError: If file update fails
        """
        try:
            full_path = self._get_full_path(path)
            branch = branch or settings.GITHUB_BRANCH

            # Get current SHA if not provided
            if not sha:
                file_info = await self.get_file(path, branch)
                sha = file_info["sha"]

            # Generate commit message if not provided
            if not message:
                message = generate_commit_message(
                    action="update",
                    path=path,
                    title=self._extract_title_from_content(content),
                )

            logger.info(f"Updating file: {full_path} in {branch}")

            # Update file
            result = self._repo.update_file(
                path=full_path,
                message=message,
                content=content,
                sha=sha,
                branch=branch,
            )

            return {
                "path": path,
                "full_path": full_path,
                "commit": self._format_commit_info(result["commit"]),
                "content_sha": result["content"].sha,
            }

        except GithubException as e:
            if e.status == 404:
                raise ResourceNotFoundError("Document", path) from e
            logger.error(f"GitHub API error updating file {path}: {e}")
            raise GitHubAPIError(
                message=f"Failed to update file: {path}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def delete_file(
        self,
        path: str,
        message: str | None = None,
        sha: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete a file from the repository.

        Args:
            path: Path to file to delete
            message: Commit message (auto-generated if not provided)
            sha: Current file SHA (fetched if not provided)
            branch: Target branch (defaults to main)

        Returns:
            Dictionary with commit information

        Raises:
            ResourceNotFoundError: If file doesn't exist
            GitHubAPIError: If file deletion fails
        """
        try:
            full_path = self._get_full_path(path)
            branch = branch or settings.GITHUB_BRANCH

            # Get current SHA if not provided
            if not sha:
                file_info = await self.get_file(path, branch)
                sha = file_info["sha"]

            # Generate commit message if not provided
            if not message:
                message = generate_commit_message(action="delete", path=path)

            logger.info(f"Deleting file: {full_path} from {branch}")

            # Delete file
            result = self._repo.delete_file(
                path=full_path,
                message=message,
                sha=sha,
                branch=branch,
            )

            return {
                "path": path,
                "full_path": full_path,
                "commit": self._format_commit_info(result["commit"]),
            }

        except GithubException as e:
            if e.status == 404:
                raise ResourceNotFoundError("Document", path) from e
            logger.error(f"GitHub API error deleting file {path}: {e}")
            raise GitHubAPIError(
                message=f"Failed to delete file: {path}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def move_file(
        self,
        old_path: str,
        new_path: str,
        message: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        """
        Move or rename a file in the repository.

        Implemented as delete + create to maintain Git history.

        Args:
            old_path: Current file path
            new_path: New file path
            message: Commit message (auto-generated if not provided)
            branch: Target branch (defaults to main)

        Returns:
            Dictionary with commit information

        Raises:
            ResourceNotFoundError: If source file doesn't exist
            GitHubAPIError: If move operation fails
        """
        try:
            branch = branch or settings.GITHUB_BRANCH

            # Get current file content and SHA
            file_info = await self.get_file(old_path, branch)
            content = file_info["content"]
            sha = file_info["sha"]

            # Generate commit message if not provided
            if not message:
                message = generate_commit_message(action="move", path=old_path, new_path=new_path)

            logger.info(f"Moving file: {old_path} -> {new_path}")

            # Create file at new location
            create_result = await self.create_file(
                path=new_path,
                content=content,
                message=f"{message} (step 1: create)",
                branch=branch,
            )

            # Delete file from old location
            delete_result = await self.delete_file(
                path=old_path,
                message=f"{message} (step 2: delete)",
                sha=sha,
                branch=branch,
            )

            return {
                "old_path": old_path,
                "new_path": new_path,
                "create_commit": create_result["commit"],
                "delete_commit": delete_result["commit"],
            }

        except Exception as e:
            logger.error(f"Error moving file {old_path} to {new_path}: {e}")
            raise

    async def list_files(
        self,
        directory: str = "",
        branch: str | None = None,
        recursive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List files in a directory.

        Args:
            directory: Directory path (empty for root)
            branch: Branch name (defaults to main)
            recursive: Whether to list recursively

        Returns:
            List of file information dictionaries

        Raises:
            GitHubAPIError: If listing fails
        """
        try:
            full_path = self._get_full_path(directory) if directory else settings.DOCS_ROOT_PATH
            branch = branch or settings.GITHUB_BRANCH

            logger.info(f"Listing files in: {full_path}")

            contents = self._repo.get_contents(full_path, ref=branch)

            if not isinstance(contents, list):
                contents = [contents]

            files = []

            for item in contents:
                if item.type == "file":
                    files.append(
                        {
                            "path": item.path.replace(f"{settings.DOCS_ROOT_PATH}/", ""),
                            "name": item.name,
                            "size": item.size,
                            "sha": item.sha,
                            "url": item.html_url,
                        }
                    )
                elif item.type == "dir" and recursive:
                    # Recursively list subdirectory
                    subdir_files = await self.list_files(
                        directory=item.path.replace(f"{settings.DOCS_ROOT_PATH}/", ""),
                        branch=branch,
                        recursive=True,
                    )
                    files.extend(subdir_files)

            return files

        except GithubException as e:
            logger.error(f"GitHub API error listing files in {directory}: {e}")
            raise GitHubAPIError(
                message=f"Failed to list files in: {directory}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def get_commit_history(
        self,
        path: str | None = None,
        branch: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get commit history for a file or repository.

        Args:
            path: File path (None for entire repository)
            branch: Branch name (defaults to main)
            limit: Maximum number of commits to return

        Returns:
            List of commit information dictionaries

        Raises:
            GitHubAPIError: If fetching commits fails
        """
        try:
            branch = branch or settings.GITHUB_BRANCH
            full_path = self._get_full_path(path) if path else None

            logger.info(f"Fetching commit history for: {path or 'repository'}")

            commits = self._repo.get_commits(
                sha=branch,
                path=full_path if full_path else GithubObject.NotSet,
            )

            commit_list = []
            for i, commit in enumerate(commits):
                if i >= limit:
                    break
                commit_list.append(self._format_commit_info(commit))

            return commit_list

        except GithubException as e:
            logger.error(f"GitHub API error fetching commit history: {e}")
            raise GitHubAPIError(
                message="Failed to fetch commit history",
                details={"error": str(e), "status": e.status},
            ) from e

    async def create_branch(
        self, branch_name: str, from_branch: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new branch.

        Args:
            branch_name: Name for the new branch
            from_branch: Source branch (defaults to main)

        Returns:
            Dictionary with branch information

        Raises:
            GitHubAPIError: If branch creation fails
        """
        try:
            from_branch = from_branch or settings.GITHUB_BRANCH

            logger.info(f"Creating branch: {branch_name} from {from_branch}")

            # Get source branch reference
            source_ref = self._repo.get_git_ref(f"heads/{from_branch}")
            source_sha = source_ref.object.sha

            # Create new branch
            new_ref = self._repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)

            return {
                "branch": branch_name,
                "sha": new_ref.object.sha,
                "url": new_ref.url,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating branch {branch_name}: {e}")
            raise GitHubAPIError(
                message=f"Failed to create branch: {branch_name}",
                details={"error": str(e), "status": e.status},
            ) from e

    def _format_commit_info(self, commit: Any) -> dict[str, Any]:
        """
        Format commit information for API response.

        Args:
            commit: GitHub commit object

        Returns:
            Dictionary with formatted commit information
        """
        return {
            "sha": commit.sha,
            "message": commit.commit.message,
            "author": commit.commit.author.name,
            "email": commit.commit.author.email,
            "date": commit.commit.author.date.isoformat(),
            "url": commit.html_url,
        }

    def _extract_title_from_content(self, content: str) -> str | None:
        """
        Extract title from markdown content.

        Looks for first H1 heading or frontmatter title.

        Args:
            content: Markdown content

        Returns:
            Extracted title or None
        """
        lines = content.split("\n")

        # Look for frontmatter title
        if lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if line.strip().startswith("title:"):
                    return line.split(":", 1)[1].strip().strip("\"'")

        # Look for first H1 heading
        for line in lines:
            if line.strip().startswith("# "):
                return line.strip()[2:].strip()

        return None

    async def health_check(self) -> dict[str, Any]:  # noqa: C901
        """
        Check GitHub API connectivity and rate limits.

        Returns:
            Dictionary with health check information
        """
        try:
            rate_limit = self._client.get_rate_limit()

            # Support multiple shapes returned by PyGithub across versions.
            core = getattr(rate_limit, "core", None)
            remaining = limit = reset = None

            if core is not None:
                remaining = getattr(core, "remaining", None)
                limit = getattr(core, "limit", None)
                reset = getattr(core, "reset", None)
            else:
                # Try raw_data (dict) shape: {"resources": {"core": {...}}}
                raw = getattr(rate_limit, "raw_data", None)
                if isinstance(raw, dict):
                    core = raw.get("resources", {}).get("core")
                    if core:
                        remaining = core.get("remaining")
                        limit = core.get("limit")
                        reset = core.get("reset")
                elif isinstance(rate_limit, dict):
                    core = rate_limit.get("resources", {}).get("core")
                    if core:
                        remaining = core.get("remaining")
                        limit = core.get("limit")
                        reset = core.get("reset")

            # Normalize reset to ISO string
            reset_iso = None
            if isinstance(reset, (int, float)):
                reset_iso = datetime.fromtimestamp(reset, tz=UTC).isoformat()
            elif hasattr(reset, "isoformat"):
                try:
                    reset_iso = reset.isoformat()  # type: ignore[union-attr]
                except Exception:
                    reset_iso = str(reset)
            elif reset is not None:
                reset_iso = str(reset)

            return {
                "status": "healthy",
                "repository": f"{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}",
                "rate_limit": {
                    "remaining": remaining if remaining is not None else "unknown",
                    "limit": limit if limit is not None else "unknown",
                    "reset": reset_iso,
                },
            }
        except Exception as e:
            logger.error(f"GitHub health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
