# Database Migrations

This directory contains database migration scripts for the ANPR Client Backend.

## Available Migrations

### add_stream_type_to_cameras.sql

**Description**: Adds `stream_type` enum field to the `cameras` table to support different camera orientations.

**Changes**:
- Creates `streamtype` enum with values: 'upside-down', 'downside-up'
- Adds `stream_type` column to `cameras` table
- Sets default value to 'downside-up' for all existing cameras

**Fields Added**:
- `stream_type` (streamtype, NOT NULL, default: 'downside-up')

## Running Migrations

### Option 1: Using Python Script (Recommended)

```bash
cd /home/user/Documents/Projects/anpr_client_v2_fe_be/anpr_client_backend
python migrations/run_migration.py
```

### Option 2: Using psql

```bash
psql -U your_username -d anpr_client_db -f migrations/add_stream_type_to_cameras.sql
```

### Option 3: Manual Execution

Connect to your database and run the SQL commands from `add_stream_type_to_cameras.sql`.

## Verification

After running the migration, verify it was successful:

```sql
-- Check if enum type exists
SELECT * FROM pg_type WHERE typname = 'streamtype';

-- Check if column exists
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'cameras' AND column_name = 'stream_type';

-- Check existing records
SELECT id, name, stream_type FROM cameras;
```

Expected output:
- All cameras should have `stream_type` set to 'downside-up'
- The column should be NOT NULL with default 'downside-up'

## Rollback

If you need to rollback this migration:

```sql
-- Remove the column
ALTER TABLE cameras DROP COLUMN IF EXISTS stream_type;

-- Drop the enum type
DROP TYPE IF EXISTS streamtype;
```

## Notes

- This migration is backward compatible - all existing cameras will default to 'downside-up'
- The migration is idempotent - it can be run multiple times safely
- Make sure to backup your database before running migrations in production
