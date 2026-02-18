"""
GitHub webhook schemas.

Defines request models for handling GitHub webhook events
that trigger documentation rebuilds and cache invalidation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WebhookRepository(BaseModel):
    """Schema for repository information in webhook payload."""

    id: int
    name: str
    full_name: str
    private: bool
    owner: dict[str, Any]
    html_url: str
    description: str | None = None
    fork: bool
    url: str
    default_branch: str


class WebhookCommit(BaseModel):
    """Schema for commit information in webhook payload."""

    id: str
    tree_id: str
    message: str
    timestamp: datetime
    url: str
    author: dict[str, str]
    committer: dict[str, str]
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)


class WebhookPusher(BaseModel):
    """Schema for pusher information in webhook payload."""

    name: str
    email: str


class WebhookPayload(BaseModel):
    """
    Schema for GitHub push webhook payload.

    Handles webhook events when documentation is pushed to the repository,
    triggering cache invalidation and rebuild processes.
    """

    ref: str = Field(..., description="Git ref that was pushed (e.g., refs/heads/main)")
    before: str = Field(..., description="SHA before the push")
    after: str = Field(..., description="SHA after the push")
    repository: WebhookRepository
    pusher: WebhookPusher
    sender: dict[str, Any]
    created: bool = Field(default=False)
    deleted: bool = Field(default=False)
    forced: bool = Field(default=False)
    commits: list[WebhookCommit] = Field(default_factory=list)
    head_commit: WebhookCommit | None = None

    @property
    def branch_name(self) -> str:
        """Extract branch name from ref."""
        return self.ref.replace("refs/heads/", "")

    @property
    def is_main_branch(self) -> bool:
        """Check if push was to main/master branch."""
        return self.branch_name in ["main", "master"]

    @property
    def affected_docs(self) -> list[str]:
        """Get list of all documentation files affected by this push."""
        docs = []
        for commit in self.commits:
            docs.extend(commit.added)
            docs.extend(commit.modified)
            docs.extend(commit.removed)
        # Filter for markdown files only
        return [f for f in docs if f.endswith(".md")]


class WebhookResponse(BaseModel):
    """Schema for webhook processing response."""

    status: str = Field(..., description="Processing status: 'received', 'processed', 'error'")
    message: str = Field(..., description="Human-readable status message")
    affected_files: list[str] = Field(default_factory=list)
    rebuild_triggered: bool = Field(default=False)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
