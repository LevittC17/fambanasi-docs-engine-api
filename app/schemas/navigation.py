"""
Navigation tree schemas.

Defines request/response models for the folder-aware
navigation system that mirrors Git repository structure.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class NavigationNode(BaseModel):
    """
    Schema for a single node in the navigation tree.

    Represents either a folder (with children) or a document (leaf node).
    """

    id: str = Field(..., description="Unique identifier for the node")
    label: str = Field(..., description="Display label for the node")
    path: str = Field(..., description="Full path in Git repository")
    type: str = Field(..., description="Node type: 'folder' or 'document'")
    children: list[NavigationNode] = Field(
        default_factory=list, description="Child nodes (empty for documents)"
    )
    order: int = Field(default=0, description="Display order (for manual sorting)")
    icon: str | None = Field(None, description="Optional icon name")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (category, tags, etc.)"
    )

    @field_validator("type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        """Ensure node type is valid."""
        if v not in ["folder", "document"]:
            raise ValueError("Node type must be 'folder' or 'document'")
        return v

    model_config = {"from_attributes": True}


class NavigationTree(BaseModel):
    """
    Schema for the complete navigation tree.

    Represents the entire documentation structure as a hierarchical tree.
    """

    root: NavigationNode = Field(..., description="Root node of the navigation tree")
    total_documents: int = Field(
        ..., description="Total number of documents in the tree"
    )
    total_folders: int = Field(..., description="Total number of folders in the tree")
    last_updated: str = Field(..., description="ISO timestamp of last tree update")

    model_config = {"from_attributes": True}


class NavigationUpdateRequest(BaseModel):
    """Schema for updating navigation structure."""

    path: str = Field(..., description="Path of node to update")
    new_order: int | None = Field(None, description="New display order")
    new_parent: str | None = Field(
        None, description="New parent path (for moving nodes)"
    )
    new_label: str | None = Field(None, description="New display label")


class NavigationBulkUpdateRequest(BaseModel):
    """Schema for bulk navigation updates."""

    updates: list[NavigationUpdateRequest] = Field(
        ..., min_length=1, description="List of navigation updates to apply"
    )


class BreadcrumbItem(BaseModel):
    """Schema for breadcrumb navigation item."""

    label: str
    path: str

    model_config = {"from_attributes": True}


class BreadcrumbTrail(BaseModel):
    """Schema for breadcrumb trail."""

    items: list[BreadcrumbItem] = Field(
        ..., description="Breadcrumb items from root to current"
    )

    model_config = {"from_attributes": True}
