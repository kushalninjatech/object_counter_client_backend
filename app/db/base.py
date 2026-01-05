"""Database base class and imports for models"""
from sqlalchemy.ext.declarative import declarative_base

# Import all models here for Alembic migrations
Base = declarative_base()

# Import models to register them with Base
from app.models.camera import Camera  # noqa: E402, F401
from app.models.detection import Detection  # noqa: E402, F401
