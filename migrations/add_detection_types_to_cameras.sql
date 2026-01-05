-- Migration: Add detection_types column to cameras table
-- Date: 2026-01-01
-- Description: Adds detection_types JSON field to support multiple YOLO class selection

-- Add detection_types column to cameras table
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS detection_types JSON DEFAULT '[0, 2, 3, 5, 7]' NOT NULL;

-- Add comment to the column
COMMENT ON COLUMN cameras.detection_types IS 'List of YOLO class IDs to detect: 0=person, 2=car, 3=motorcycle, 5=bus, 7=truck';

-- Update existing records to use default value
UPDATE cameras SET detection_types = '[0, 2, 3, 5, 7]' WHERE detection_types IS NULL;
