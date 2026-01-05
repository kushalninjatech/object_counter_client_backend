"""
Base Model Module

This module provides the abstract base model class that all database models inherit from.
It includes common fields like id, is_active, created_at, and updated_at to ensure
consistency across all database tables.

Author: ANPR Team
Created: 2025
"""

from sqlalchemy import Column, Integer, Boolean, DateTime, text
from app.db.base import Base

# UTC timestamp helper - ensures all timestamps are stored in UTC
utc_now = text("(NOW() AT TIME ZONE 'UTC')")


class BaseModel(Base):
    """
    Abstract Base Model for all database tables

    This class provides common fields that should be present in all database models:
    - id: Primary key for the table
    - is_active: Soft delete flag - allows marking records as inactive instead of deleting
    - created_at: Timestamp when the record was created (UTC)
    - updated_at: Timestamp when the record was last updated (UTC)

    Usage:
        class MyModel(BaseModel):
            __tablename__ = "my_table"
            name = Column(String(255))

    Attributes:
        id (int): Auto-incrementing primary key
        is_active (bool): Whether the record is active (default: True)
        created_at (datetime): When the record was created in UTC
        updated_at (datetime): When the record was last updated in UTC
    """

    __abstract__ = True  # This tells SQLAlchemy this is an abstract base class

    # Primary Key - auto-incrementing integer
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="Unique identifier for the record"
    )

    # Soft Delete Flag - allows marking records as inactive instead of deleting
    # This is useful for audit trails and data recovery
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether the record is active (soft delete flag)"
    )

    # Timestamp: When the record was created
    # server_default ensures the database sets this value if not provided
    created_at = Column(
        DateTime(timezone=True),
        server_default=utc_now,
        nullable=False,
        index=True,
        comment="When the record was created (UTC)"
    )

    # Timestamp: When the record was last updated
    # onupdate ensures this is automatically updated whenever the record changes
    updated_at = Column(
        DateTime(timezone=True),
        server_default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="When the record was last updated (UTC)"
    )

    def __repr__(self):
        """
        String representation of the model instance

        Returns:
            str: A readable representation of the object
        """
        return f"<{self.__class__.__name__}(id={self.id})>"
