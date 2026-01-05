"""
Migration Runner Script

Run this script to apply the stream_type migration to the database.

Usage:
    python migrations/run_migration.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine
from sqlalchemy import text

def run_migration():
    """Run the migration to add stream_type column"""

    migration_file = Path(__file__).parent / "add_stream_type_to_cameras.sql"

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print("🔄 Running migration: add_stream_type_to_cameras...")

    try:
        with engine.connect() as connection:
            # Execute the migration
            connection.execute(text(migration_sql))
            connection.commit()
            print("✅ Migration completed successfully!")
            print("   - Added streamtype enum")
            print("   - Added stream_type column to cameras table")
            print("   - Set default value to 'downside-up'")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
