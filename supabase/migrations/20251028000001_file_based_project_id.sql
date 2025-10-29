-- Migration: File-Based Project ID System
-- Date: 2025-10-28
-- Purpose: Enable same project identification across different machines with different paths
--
-- Changes:
--   1. Remove UNIQUE constraint on path (same project can have different paths on different machines)
--   2. Change PRIMARY KEY from (id) to (id, machine_id) - composite key
--   3. Add index on path for quick lookups
--
-- IMPORTANT: This is a breaking change. Existing projects need to be migrated.
-- Run migrate_to_file_based_project_id.py after this migration.

-- Step 1: Drop UNIQUE constraint on path
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;

-- Step 2: Drop old primary key constraint
-- Note: This will temporarily leave the table without a PK
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;

-- Step 3: Ensure machine_id column exists and is NOT NULL
-- (It should already exist from previous migrations)
ALTER TABLE projects ALTER COLUMN machine_id SET NOT NULL;

-- Step 4: Add composite primary key (id, machine_id)
-- This allows same project_id on multiple machines
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- Step 5: Add index on path for quick lookups by local path
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);

-- Step 6: Add index on just id for "get all machines for this project" queries
CREATE INDEX IF NOT EXISTS idx_projects_id ON projects(id);

-- Update comment
COMMENT ON TABLE projects IS 'Projects with composite key (id, machine_id). Same project can exist on multiple machines with different paths. project_id is stored in .claude-tasks/data/project_id file.';

COMMENT ON COLUMN projects.id IS 'Project UUID from .claude-tasks/data/project_id file (shared across machines)';
COMMENT ON COLUMN projects.machine_id IS 'Machine identifier (one row per machine accessing this project)';
COMMENT ON COLUMN projects.path IS 'Local filesystem path on this specific machine';
