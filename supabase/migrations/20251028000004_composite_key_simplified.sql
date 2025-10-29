-- Migration: Composite Key - Simplified for Existing Tables Only
-- Date: 2025-10-28
-- Purpose: Apply composite primary key focusing only on tables that actually exist
--
-- Tables confirmed to exist:
--   tasks, sprints, journal_sessions, backlog_items, documentation,
--   specifications, specifications_validated, template_tasks, template_sprints

-- ============================================================================
-- STEP 1: Drop ALL possible FK constraint names (aggressive approach)
-- ============================================================================

-- Tasks table - try all possible names
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_fkey;
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_fkey;
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_project;
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_project_id;

-- Sprints table
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_id_fkey;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_fkey;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS fk_sprints_project;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS fk_sprints_project_id;

-- Journal sessions
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS journal_sessions_project_id_fkey;
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS journal_sessions_project_fkey;
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS fk_journal_sessions_project;
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS fk_journal_sessions_project_id;

-- Backlog items
ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS backlog_items_project_id_fkey;
ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS backlog_items_project_fkey;
ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS fk_backlog_items_project;
ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS fk_backlog_items_project_id;

-- Documentation
ALTER TABLE documentation DROP CONSTRAINT IF EXISTS documentation_project_id_fkey;
ALTER TABLE documentation DROP CONSTRAINT IF EXISTS documentation_project_fkey;
ALTER TABLE documentation DROP CONSTRAINT IF EXISTS fk_documentation_project;
ALTER TABLE documentation DROP CONSTRAINT IF EXISTS fk_documentation_project_id;

-- Specifications
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS specifications_project_id_fkey;
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS specifications_project_fkey;
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS fk_specifications_project;
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS fk_specifications_project_id;

-- Specifications validated
ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS specifications_validated_project_id_fkey;
ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS specifications_validated_project_fkey;
ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS fk_specifications_validated_project;
ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS fk_specifications_validated_project_id;

-- Template tasks
ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS template_tasks_project_id_fkey;
ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS template_tasks_project_fkey;
ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS fk_template_tasks_project;
ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS fk_template_tasks_project_id;

-- Template sprints
ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS template_sprints_project_id_fkey;
ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS template_sprints_project_fkey;
ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS fk_template_sprints_project;
ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS fk_template_sprints_project_id;

-- ============================================================================
-- STEP 2: Drop UNIQUE constraint on path and old PRIMARY KEY
-- ============================================================================

-- Drop UNIQUE on path (may already be done)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;

-- Drop old PRIMARY KEY (should work now that FKs are gone)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;

-- Ensure machine_id is NOT NULL
ALTER TABLE projects ALTER COLUMN machine_id SET NOT NULL;

-- ============================================================================
-- STEP 3: Add composite PRIMARY KEY
-- ============================================================================

ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
CREATE INDEX IF NOT EXISTS idx_projects_id ON projects(id);

-- ============================================================================
-- STEP 4: Add machine_id to specifications_validated if missing
-- (May already be done)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'specifications_validated' AND column_name = 'machine_id'
    ) THEN
        ALTER TABLE specifications_validated ADD COLUMN machine_id TEXT;

        UPDATE specifications_validated sv
        SET machine_id = s.machine_id
        FROM specifications s
        WHERE sv.id = s.id;

        ALTER TABLE specifications_validated ALTER COLUMN machine_id SET NOT NULL;
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Add composite FK constraints
-- ============================================================================

-- Tasks
ALTER TABLE tasks
ADD CONSTRAINT tasks_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Sprints
ALTER TABLE sprints
ADD CONSTRAINT sprints_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Journal sessions
ALTER TABLE journal_sessions
ADD CONSTRAINT journal_sessions_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Backlog items
ALTER TABLE backlog_items
ADD CONSTRAINT backlog_items_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Documentation
ALTER TABLE documentation
ADD CONSTRAINT documentation_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Specifications
ALTER TABLE specifications
ADD CONSTRAINT specifications_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Specifications validated
ALTER TABLE specifications_validated
ADD CONSTRAINT specifications_validated_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Template tasks
ALTER TABLE template_tasks
ADD CONSTRAINT template_tasks_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Template sprints
ALTER TABLE template_sprints
ADD CONSTRAINT template_sprints_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- ============================================================================
-- STEP 6: Create composite indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_tasks_project_machine ON tasks(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_sprints_project_machine ON sprints(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_journal_project_machine ON journal_sessions(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_backlog_project_machine ON backlog_items(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_documentation_project_machine ON documentation(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_specifications_project_machine ON specifications(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_specifications_validated_project_machine ON specifications_validated(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_template_tasks_project_machine ON template_tasks(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_template_sprints_project_machine ON template_sprints(project_id, machine_id);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== Composite Key Migration Complete ===';
    RAISE NOTICE 'Run verify_composite_fks_final.py to confirm all changes applied.';
END $$;

COMMENT ON TABLE projects IS 'Projects with composite PRIMARY KEY (id, machine_id). Migration 20251028000004 applied.';
