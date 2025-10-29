-- Migration: Composite Key - Final Implementation with Correct FK Names
-- Date: 2025-10-28
-- Purpose: Implement composite primary key (id, machine_id) on projects table
--          Based on actual database FK constraint discovery
--
-- Actual FK constraints found:
--   - agents.agents_project_id_fkey
--   - commands.commands_project_id_fkey
--
-- Note: Most tables (tasks, sprints, etc.) don't currently have FK constraints,
--       so we'll add them as composite constraints from the start.

-- ============================================================================
-- STEP 1: Drop existing FK constraints (only 2 found in database)
-- ============================================================================

-- Agents table
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_project_id_fkey;

-- Commands table
ALTER TABLE commands DROP CONSTRAINT IF EXISTS commands_project_id_fkey;

-- Also try possible FK names for core tables (may not exist)
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_fkey;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_id_fkey;
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS journal_sessions_project_id_fkey;
ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS backlog_items_project_id_fkey;
ALTER TABLE documentation DROP CONSTRAINT IF EXISTS documentation_project_id_fkey;
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS specifications_project_id_fkey;
ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS specifications_validated_project_id_fkey;
ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS template_tasks_project_id_fkey;
ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS template_sprints_project_id_fkey;

-- ============================================================================
-- STEP 2: Convert project_id columns from TEXT to UUID (type alignment)
-- CRITICAL: projects.id is UUID, but some tables have TEXT project_id
-- ============================================================================

-- Tasks table
ALTER TABLE tasks ALTER COLUMN project_id TYPE UUID USING project_id::UUID;

-- Sprints table
ALTER TABLE sprints ALTER COLUMN project_id TYPE UUID USING project_id::UUID;

-- Journal sessions
ALTER TABLE journal_sessions ALTER COLUMN project_id TYPE UUID USING project_id::UUID;

-- Backlog items (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        EXECUTE 'ALTER TABLE backlog_items ALTER COLUMN project_id TYPE UUID USING project_id::UUID';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Modify projects table PRIMARY KEY
-- ============================================================================

-- Drop old PRIMARY KEY (now safe - FKs are gone)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;

-- Ensure machine_id is NOT NULL (required for PK)
ALTER TABLE projects ALTER COLUMN machine_id SET NOT NULL;

-- Add composite PRIMARY KEY
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
CREATE INDEX IF NOT EXISTS idx_projects_id ON projects(id);

-- ============================================================================
-- STEP 4: Add machine_id to specifications_validated if missing
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

        RAISE NOTICE 'Added machine_id to specifications_validated';
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Add machine_id to agents and commands tables if missing
-- ============================================================================

-- Agents table
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents' AND table_schema = 'public') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'agents' AND column_name = 'machine_id'
        ) THEN
            ALTER TABLE agents ADD COLUMN machine_id TEXT;
            -- Try to populate from projects if possible
            UPDATE agents a
            SET machine_id = p.machine_id
            FROM projects p
            WHERE a.project_id = p.id;

            -- For any that couldn't be populated, use a default
            UPDATE agents SET machine_id = 'unknown' WHERE machine_id IS NULL;
            ALTER TABLE agents ALTER COLUMN machine_id SET NOT NULL;

            RAISE NOTICE 'Added machine_id to agents';
        END IF;
    END IF;
END $$;

-- Commands table
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'commands' AND table_schema = 'public') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'commands' AND column_name = 'machine_id'
        ) THEN
            ALTER TABLE commands ADD COLUMN machine_id TEXT;
            -- Try to populate from projects if possible
            UPDATE commands c
            SET machine_id = p.machine_id
            FROM projects p
            WHERE c.project_id = p.id;

            -- For any that couldn't be populated, use a default
            UPDATE commands SET machine_id = 'unknown' WHERE machine_id IS NULL;
            ALTER TABLE commands ALTER COLUMN machine_id SET NOT NULL;

            RAISE NOTICE 'Added machine_id to commands';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- STEP 6: Create composite FK constraints for ALL tables
-- ============================================================================

-- Agents (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents' AND table_schema = 'public') THEN
        ALTER TABLE agents
        ADD CONSTRAINT agents_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;

        RAISE NOTICE 'Added composite FK to agents';
    END IF;
END $$;

-- Commands (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'commands' AND table_schema = 'public') THEN
        ALTER TABLE commands
        ADD CONSTRAINT commands_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;

        RAISE NOTICE 'Added composite FK to commands';
    END IF;
END $$;

-- Core tables (add FK constraints - they may not have existed before)

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
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated' AND table_schema = 'public') THEN
        ALTER TABLE specifications_validated
        ADD CONSTRAINT specifications_validated_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

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
-- STEP 7: Create composite indexes for performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_tasks_project_machine ON tasks(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_sprints_project_machine ON sprints(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_journal_project_machine ON journal_sessions(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_backlog_project_machine ON backlog_items(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_documentation_project_machine ON documentation(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_specifications_project_machine ON specifications(project_id, machine_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated' AND table_schema = 'public') THEN
        CREATE INDEX IF NOT EXISTS idx_specifications_validated_project_machine ON specifications_validated(project_id, machine_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_template_tasks_project_machine ON template_tasks(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_template_sprints_project_machine ON template_sprints(project_id, machine_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents' AND table_schema = 'public') THEN
        CREATE INDEX IF NOT EXISTS idx_agents_project_machine ON agents(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'commands' AND table_schema = 'public') THEN
        CREATE INDEX IF NOT EXISTS idx_commands_project_machine ON commands(project_id, machine_id);
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    pk_count INTEGER;
    fk_count INTEGER;
BEGIN
    -- Check PK
    SELECT COUNT(*) INTO pk_count
    FROM information_schema.key_column_usage kcu
    JOIN information_schema.table_constraints tc
        ON kcu.constraint_name = tc.constraint_name
    WHERE tc.table_name = 'projects'
      AND tc.constraint_type = 'PRIMARY KEY';

    IF pk_count = 2 THEN
        RAISE NOTICE '✅ Composite PRIMARY KEY (id, machine_id) created successfully';
    ELSE
        RAISE WARNING '⚠️  PRIMARY KEY has % columns (expected 2)', pk_count;
    END IF;

    -- Check FKs
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints tc
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND EXISTS (
          SELECT 1 FROM information_schema.constraint_column_usage ccu
          WHERE ccu.constraint_name = tc.constraint_name
            AND ccu.table_name = 'projects'
      );

    RAISE NOTICE '✅ Created % composite FK constraints to projects table', fk_count;
    RAISE NOTICE '';
    RAISE NOTICE '=== Migration 20251028000005 Complete ===';
END $$;

-- Update comment
COMMENT ON TABLE projects IS 'Projects with composite PRIMARY KEY (id, machine_id). Same project can exist on multiple machines with different paths. project_id from .claude-tasks/data/project_id file. Migration 20251028000005 applied.';
