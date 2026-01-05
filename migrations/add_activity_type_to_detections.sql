-- Migration: Add activity_type column to detections table
-- Date: 2026-01-01
-- Description: Adds activity_type enum field to track detection direction (in/out)

-- Create enum type for activity direction
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activitytype') THEN
        CREATE TYPE activitytype AS ENUM ('in', 'out');
    END IF;
END $$;

-- Add activity_type column to detections table
ALTER TABLE detections
ADD COLUMN IF NOT EXISTS activity_type activitytype;

-- Add comment to the column
COMMENT ON COLUMN detections.activity_type IS 'Detection direction: in or out';

-- Create index for filtering by activity_type
CREATE INDEX IF NOT EXISTS idx_detections_activity_type ON detections(activity_type);
