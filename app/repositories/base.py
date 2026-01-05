"""
Base Repository Module

This module provides the abstract base repository class with common CRUD operations.
All specific repositories (Camera, Detection, etc.) inherit from this base class.

Author: ANPR Team
Created: 2025
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.base import BaseModel

# TypeVar for generic model type
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base Repository with Common CRUD Operations

    This abstract class provides standard database operations that are common
    across all repositories. Specific repositories inherit from this class and
    add their own custom query methods.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository works with

    Attributes:
        model: The SQLAlchemy model class
        db: The database session

    Example:
        class CameraRepository(BaseRepository[Camera]):
            def __init__(self, db: Session):
                super().__init__(Camera, db)
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize the repository

        Args:
            model: The SQLAlchemy model class
            db: The database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: int, include_inactive: bool = False) -> Optional[ModelType]:
        """
        Get a single record by ID

        Args:
            id: The record ID
            include_inactive: Whether to include inactive records (default: False)

        Returns:
            The model instance if found, None otherwise
        """
        query = self.db.query(self.model).filter(self.model.id == id)

        if not include_inactive:
            query = query.filter(self.model.is_active == True)  # noqa: E712

        return query.first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[ModelType]:
        """
        Get all records with pagination

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive records (default: False)
            order_by: Field name to order by (default: created_at)
            desc: Whether to order descending (default: True)

        Returns:
            List of model instances
        """
        query = self.db.query(self.model)

        if not include_inactive:
            query = query.filter(self.model.is_active == True)  # noqa: E712

        # Apply ordering
        order_column = getattr(self.model, order_by, self.model.created_at)
        if desc:
            order_column = order_column.desc()

        return query.order_by(order_column).offset(skip).limit(limit).all()

    def create(self, **kwargs) -> ModelType:
        """
        Create a new record

        Args:
            **kwargs: Field values for the new record

        Returns:
            The created model instance

        Example:
            camera = camera_repo.create(
                name="Gate 1",
                stream_url="rtsp://...",
                organization_id=1
            )
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update an existing record

        Args:
            id: The record ID
            **kwargs: Field values to update

        Returns:
            The updated model instance if found, None otherwise

        Example:
            camera = camera_repo.update(1, name="New Name", confidence=0.7)
        """
        instance = self.get_by_id(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, id: int, soft_delete: bool = True) -> bool:
        """
        Delete a record (soft or hard delete)

        Args:
            id: The record ID
            soft_delete: If True, mark as inactive; if False, permanently delete

        Returns:
            True if deleted successfully, False if record not found

        Example:
            # Soft delete (mark as inactive)
            camera_repo.delete(1, soft_delete=True)

            # Hard delete (permanently remove)
            camera_repo.delete(1, soft_delete=False)
        """
        instance = self.get_by_id(id, include_inactive=True)
        if not instance:
            return False

        if soft_delete:
            instance.is_active = False
            self.db.commit()
        else:
            self.db.delete(instance)
            self.db.commit()

        return True

    def count(self, filters: Optional[Dict[str, Any]] = None, include_inactive: bool = False) -> int:
        """
        Count records matching the given filters

        Args:
            filters: Dictionary of field:value pairs to filter by
            include_inactive: Whether to include inactive records (default: False)

        Returns:
            Number of matching records

        Example:
            count = camera_repo.count({"organization_id": 1})
        """
        query = self.db.query(self.model)

        if not include_inactive:
            query = query.filter(self.model.is_active == True)  # noqa: E712

        if filters:
            conditions = [getattr(self.model, key) == value for key, value in filters.items()]
            query = query.filter(and_(*conditions))

        return query.count()

    def exists(self, id: int, include_inactive: bool = False) -> bool:
        """
        Check if a record exists

        Args:
            id: The record ID
            include_inactive: Whether to include inactive records (default: False)

        Returns:
            True if the record exists, False otherwise
        """
        return self.get_by_id(id, include_inactive=include_inactive) is not None

    def bulk_create(self, records: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk

        Args:
            records: List of dictionaries with field values

        Returns:
            List of created model instances

        Example:
            cameras = camera_repo.bulk_create([
                {"name": "Camera 1", "stream_url": "rtsp://..."},
                {"name": "Camera 2", "stream_url": "rtsp://..."}
            ])
        """
        instances = [self.model(**record) for record in records]
        self.db.bulk_save_objects(instances)
        self.db.commit()
        return instances
