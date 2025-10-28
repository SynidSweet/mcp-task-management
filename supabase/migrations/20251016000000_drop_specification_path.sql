-- Drop specification_path column from specifications table
-- This field is no longer used - path is calculated on-demand from display_id hierarchy

-- Migration: Drop specification_path column
ALTER TABLE specifications DROP COLUMN IF EXISTS specification_path;

-- Add comment to table explaining path calculation
COMMENT ON TABLE specifications IS 'Specifications with Dual-ID hierarchy. Path is calculated on-demand as parent_display_id/display_id chain.';
