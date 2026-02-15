"""Pydantic schemas package for request/response validation."""

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    GitCommitInfo,
)
from app.schemas.draft import (
    DraftCreate,
    DraftResponse,
    DraftStatusUpdate,
    DraftUpdate,
)
from app.schemas.metadata import (
    DocumentMetadataResponse,
    MetadataCreate,
    MetadataUpdate,
)
from app.schemas.navigation import NavigationNode, NavigationTree
from app.schemas.webhook import WebhookPayload

__all__ = [
    # Auth schemas
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    # Document schemas
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "GitCommitInfo",
    # Draft schemas
    "DraftCreate",
    "DraftResponse",
    "DraftStatusUpdate",
    "DraftUpdate",
    # Metadata schemas
    "DocumentMetadataResponse",
    "MetadataCreate",
    "MetadataUpdate",
    # Navigation schemas
    "NavigationNode",
    "NavigationTree",
    # Webhook schemas
    "WebhookPayload",
]
