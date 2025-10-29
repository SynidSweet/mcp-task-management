-- Migration: Change projects.id from UUID to TEXT (folder name)
-- Date: 2025-10-29
-- Purpose: Use folder name as project_id instead of UUID for human readability

-- Step 1: Drop all foreign key constraints that reference projects(id, machine_id)
-- These will be recreated after the column type change

ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_machine_id_fkey;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_id_machine_id_fkey;
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS journal_sessions_project_id_machine_id_fkey;
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS specifications_project_id_machine_id_fkey;
ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS template_tasks_project_id_machine_id_fkey;
ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS template_sprints_project_id_machine_id_fkey;
ALTER TABLE commands DROP CONSTRAINT IF EXISTS commands_project_id_machine_id_fkey;
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_project_id_machine_id_fkey;
ALTER TABLE documentation DROP CONSTRAINT IF EXISTS documentation_project_id_machine_id_fkey;

-- Step 2: Drop the primary key constraint on projects (with CASCADE to drop dependent constraints)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey CASCADE;

-- Step 3: Convert projects.id from UUID to TEXT
-- For existing data: Cast UUID to TEXT (will preserve UUID strings for now)
-- New projects will use folder name instead
ALTER TABLE projects ALTER COLUMN id TYPE TEXT USING id::TEXT;

-- Step 4: Recreate the primary key
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- Step 5: Convert project_id columns in child tables from UUID to TEXT
ALTER TABLE tasks ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE sprints ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE journal_sessions ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE specifications ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE template_tasks ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE template_sprints ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE commands ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE agents ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;
ALTER TABLE documentation ALTER COLUMN project_id TYPE TEXT USING project_id::TEXT;

-- Step 6: Recreate foreign key constraints
ALTER TABLE tasks
  ADD CONSTRAINT tasks_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE sprints
  ADD CONSTRAINT sprints_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE journal_sessions
  ADD CONSTRAINT journal_sessions_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE specifications
  ADD CONSTRAINT specifications_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE template_tasks
  ADD CONSTRAINT template_tasks_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE template_sprints
  ADD CONSTRAINT template_sprints_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE commands
  ADD CONSTRAINT commands_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE agents
  ADD CONSTRAINT agents_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

ALTER TABLE documentation
  ADD CONSTRAINT documentation_project_id_machine_id_fkey
  FOREIGN KEY (project_id, machine_id)
  REFERENCES projects(id, machine_id)
  ON DELETE CASCADE;

-- Step 7: Update column comments
COMMENT ON COLUMN projects.id IS 'Project identifier (folder name from .claude-tasks/data/project_id file, shared across machines)';

-- Note: Existing projects will have UUID strings as their id until they update their project_id file
-- New projects will automatically use folder name from project_manager.get_or_generate_project_id()
