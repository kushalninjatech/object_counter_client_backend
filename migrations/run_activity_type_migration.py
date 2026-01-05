"""
Migration Runner Script for activity_type

Run this script to apply the activity_type migration to the database.

Usage:
    python migrations/run_activity_type_migration.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine
from sqlalchemy import text

def run_migration():
    """Run the migration to add activity_type column"""

    migration_file = Path(__file__).parent / "add_activity_type_to_detections.sql"

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print("🔄 Running migration: add_activity_type_to_detections...")

    try:
        with engine.connect() as connection:
            # Execute the migration
            connection.execute(text(migration_sql))
            connection.commit()
            print("✅ Migration completed successfully!")
            print("   - Created activitytype enum")
            print("   - Added activity_type column to detections table")
            print("   - Created index on activity_type")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
