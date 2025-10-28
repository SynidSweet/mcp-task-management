-- Fix template_sprints to properly mirror sprints table structure
-- Replace planning_task_ids and milestone_task_ids with simple task_ids array

-- Add task_ids column (matches sprints table)
ALTER TABLE template_sprints ADD COLUMN IF NOT EXISTS task_ids JSONB DEFAULT '[]';

-- Migrate existing data: Combine planning_task_ids and milestone_task_ids into task_ids
UPDATE template_sprints
SET task_ids = (
    COALESCE(planning_task_ids, '[]'::jsonb) || COALESCE(milestone_task_ids, '[]'::jsonb)
)
WHERE task_ids = '[]'::jsonb;

-- Drop the opinionated columns
ALTER TABLE template_sprints DROP COLUMN IF EXISTS planning_task_ids;
ALTER TABLE template_sprints DROP COLUMN IF EXISTS milestone_task_ids;

-- Update comment
COMMENT ON COLUMN template_sprints.task_ids IS 'Array of template_task.template_ids (mirrors sprints.task_ids structure)';

-- Migration complete: template_sprints now properly mirrors sprints table
