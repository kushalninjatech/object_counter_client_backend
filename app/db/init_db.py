"""Database initialization"""
from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    """
    Initialize database by creating all tables

    Note: In production, use Alembic migrations instead
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")
