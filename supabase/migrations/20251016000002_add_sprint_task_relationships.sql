-- Add sprint-task relationship fields to restore basic sprint functionality
-- This adds the minimum fields needed for sprint-task associations and timeline tracking

-- ============================================================================
-- TASKS TABLE: Add sprint relationship
-- ============================================================================

-- Add sprint_id to link tasks to sprints
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS sprint_id TEXT;

-- Add index for sprint task queries
CREATE INDEX IF NOT EXISTS idx_tasks_sprint_id ON tasks(sprint_id);

-- Add comment explaining sprint relationship
COMMENT ON COLUMN tasks.sprint_id IS 'Sprint ID this task belongs to. Links task to sprint for sprint planning and tracking.';

-- ============================================================================
-- SPRINTS TABLE: Add task tracking and timeline
-- ============================================================================

-- Add task_ids array to track tasks in sprint
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS task_ids JSONB DEFAULT '[]';

-- Add start_date for sprint timeline
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS start_date DATE;

-- Add end_date for sprint timeline
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS end_date DATE;

-- Add focus object for sprint objectives
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS focus JSONB DEFAULT '{}';

-- Add comments explaining fields
COMMENT ON COLUMN sprints.task_ids IS 'Array of task IDs assigned to this sprint. Denormalized for quick access.';
COMMENT ON COLUMN sprints.start_date IS 'Sprint start date for timeline planning.';
COMMENT ON COLUMN sprints.end_date IS 'Sprint end date for timeline planning.';
COMMENT ON COLUMN sprints.focus IS 'Sprint focus with primary_objective and scope_boundaries.';

-- Example sprint after migration:
-- {
--   "id": "SPRINT-20251016_120000",
--   "title": "Feature Development Sprint",
--   "task_ids": ["TASK-2025-001", "TASK-2025-002"],
--   "start_date": "2025-10-16",
--   "end_date": "2025-10-30",
--   "focus": {
--     "primary_objective": "Implement auth system",
--     "scope_boundaries": "Auth only, no billing"
--   }
-- }
