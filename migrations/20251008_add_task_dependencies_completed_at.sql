-- Migration: Add dependencies and completed_at to tasks table
-- Date: 2025-10-08
-- Description: Adds fields needed by dev MCP task tools

-- Add dependencies column (JSONB) to store task relationships
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS dependencies JSONB DEFAULT '{"blocks": [], "blocked_by": [], "related": []}'::jsonb;

-- Add completed_at column (TIMESTAMPTZ) to track completion time
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Add comments for documentation
COMMENT ON COLUMN tasks.dependencies IS 'Task dependencies: {blocks: [task_ids], blocked_by: [task_ids], related: [task_ids]}';
COMMENT ON COLUMN tasks.completed_at IS 'Timestamp when task was marked as completed';

-- Verify columns were added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'tasks'
AND column_name IN ('dependencies', 'completed_at');
