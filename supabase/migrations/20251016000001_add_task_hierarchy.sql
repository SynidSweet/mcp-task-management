-- Add task hierarchy support to tasks table
-- Restores parent-child task relationships that were accidentally removed during dev simplification

-- Add parent_task_id column for task hierarchy
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS parent_task_id TEXT;

-- Add child_task_ids array for tracking children
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS child_task_ids JSONB DEFAULT '[]';

-- Add foreign key constraint to parent_task_id (self-referential)
-- Note: Using ON DELETE SET NULL instead of CASCADE to preserve child tasks if parent deleted
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_parent_task
  FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE SET NULL;

-- Add index for parent queries (find all children of a parent)
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id);

-- Add comment explaining hierarchy
COMMENT ON COLUMN tasks.parent_task_id IS 'Parent task ID for subtask relationships (hierarchy). Separate from dependencies which control workflow execution order.';
COMMENT ON COLUMN tasks.child_task_ids IS 'Array of child task IDs. Denormalized for quick access to children.';

-- Example data structure after migration:
-- {
--   "id": "TASK-2025-001",
--   "parent_task_id": "TASK-2025-000",
--   "child_task_ids": ["TASK-2025-002", "TASK-2025-003"],
--   "dependencies": {"blocks": [], "blocked_by": [], "related": []}
-- }
