"""
SQLAlchemy base configuration and declarative base.

This module provides the declarative base class for all database models
and common model functionality like timestamps and soft deletes.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common functionality including:
    - Automatic table name generation from class name
    - Common timestamp fields (created_at, updated_at)
    - Dictionary conversion for serialization
    """

    # Generate __tablename__ automatically from class name
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class TimestampMixin:
    """Mixin to add timestamp fields to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when record was last updated",
    )
