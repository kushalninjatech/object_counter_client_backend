-- Migration: Add stream_type column to cameras table
-- Date: 2025-01-01
-- Description: Adds stream_type enum field to support upside-down and downside-up camera orientations

-- Drop existing enum type if it exists (in case it was created with wrong values)
DROP TYPE IF EXISTS streamtype CASCADE;

-- Create enum type for stream orientation with correct values
CREATE TYPE streamtype AS ENUM ('upside-down', 'downside-up');

-- Add stream_type column to cameras table
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS stream_type streamtype DEFAULT 'downside-up' NOT NULL;

-- Add comment to the column
COMMENT ON COLUMN cameras.stream_type IS 'Stream orientation: upside-down or downside-up (normal)';

-- Update existing records to use default value (downside-up)
UPDATE cameras SET stream_type = 'downside-up' WHERE stream_type IS NULL;
