-- Migration: Composite Key - Complete Atomic Migration
-- Date: 2025-10-28
-- Purpose: Properly implement composite primary key (id, machine_id) on projects table
--          with all dependent foreign key constraint updates in correct order
--
-- This migration REPLACES the failed partial execution of:
--   - 20251028000001_file_based_project_id.sql (partially applied, needs completion)
--   - 20251028000002_fix_composite_foreign_keys.sql (never applied)
--
-- CRITICAL: This must be run as a single transaction to maintain database integrity

-- ============================================================================
-- STEP 1: Drop all FK constraints that reference projects table
-- Must do this BEFORE we can change the projects PRIMARY KEY
-- ============================================================================

-- Core tables
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_fkey;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_id_fkey;
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS journal_sessions_project_id_fkey;

-- Optional tables (use DO blocks to handle if they don't exist)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        EXECUTE 'ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS backlog_items_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_metadata') THEN
        EXECUTE 'ALTER TABLE sync_metadata DROP CONSTRAINT IF EXISTS sync_metadata_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        EXECUTE 'ALTER TABLE entities DROP CONSTRAINT IF EXISTS entities_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_ui_state') THEN
        EXECUTE 'ALTER TABLE entity_ui_state DROP CONSTRAINT IF EXISTS entity_ui_state_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        EXECUTE 'ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documentation') THEN
        EXECUTE 'ALTER TABLE documentation DROP CONSTRAINT IF EXISTS documentation_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_references') THEN
        EXECUTE 'ALTER TABLE cross_references DROP CONSTRAINT IF EXISTS cross_references_project_id_fkey';
    END IF;
END $$;

-- Specifications system
ALTER TABLE specifications DROP CONSTRAINT IF EXISTS specifications_project_id_fkey;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        EXECUTE 'ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS specifications_validated_project_id_fkey';
    END IF;
END $$;

-- Template system
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_tasks') THEN
        EXECUTE 'ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS template_tasks_project_id_fkey';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_sprints') THEN
        EXECUTE 'ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS template_sprints_project_id_fkey';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Modify projects table - Primary Key and Constraints
-- Now we can safely modify the projects table since no FKs depend on it
-- ============================================================================

-- Drop UNIQUE constraint on path (may have already been dropped)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;

-- Drop old PRIMARY KEY (now that FKs are gone)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;

-- Ensure machine_id is NOT NULL (required for composite PK)
ALTER TABLE projects ALTER COLUMN machine_id SET NOT NULL;

-- Add new composite PRIMARY KEY
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
CREATE INDEX IF NOT EXISTS idx_projects_id ON projects(id);

-- ============================================================================
-- STEP 3: Add machine_id to specifications_validated if missing
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        -- Check if column exists
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'specifications_validated' AND column_name = 'machine_id'
        ) THEN
            -- Add column
            ALTER TABLE specifications_validated ADD COLUMN machine_id TEXT;

            -- Populate from specifications table
            UPDATE specifications_validated sv
            SET machine_id = s.machine_id
            FROM specifications s
            WHERE sv.id = s.id;

            -- Make NOT NULL
            ALTER TABLE specifications_validated ALTER COLUMN machine_id SET NOT NULL;

            RAISE NOTICE 'Added machine_id to specifications_validated';
        ELSE
            RAISE NOTICE 'machine_id already exists in specifications_validated';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Recreate FK constraints as COMPOSITE constraints
-- Now reference the new composite PRIMARY KEY (id, machine_id)
-- ============================================================================

-- Core tables
ALTER TABLE tasks
ADD CONSTRAINT tasks_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

ALTER TABLE sprints
ADD CONSTRAINT sprints_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

ALTER TABLE journal_sessions
ADD CONSTRAINT journal_sessions_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Specifications
ALTER TABLE specifications
ADD CONSTRAINT specifications_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Optional tables
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        EXECUTE 'ALTER TABLE backlog_items ADD CONSTRAINT backlog_items_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_metadata') THEN
        EXECUTE 'ALTER TABLE sync_metadata ADD CONSTRAINT sync_metadata_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        EXECUTE 'ALTER TABLE entities ADD CONSTRAINT entities_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_ui_state') THEN
        EXECUTE 'ALTER TABLE entity_ui_state ADD CONSTRAINT entity_ui_state_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        EXECUTE 'ALTER TABLE documents ADD CONSTRAINT documents_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documentation') THEN
        EXECUTE 'ALTER TABLE documentation ADD CONSTRAINT documentation_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_references') THEN
        EXECUTE 'ALTER TABLE cross_references ADD CONSTRAINT cross_references_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        EXECUTE 'ALTER TABLE specifications_validated ADD CONSTRAINT specifications_validated_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_tasks') THEN
        EXECUTE 'ALTER TABLE template_tasks ADD CONSTRAINT template_tasks_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_sprints') THEN
        EXECUTE 'ALTER TABLE template_sprints ADD CONSTRAINT template_sprints_project_fkey FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id) ON DELETE CASCADE';
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Create composite indexes for performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_tasks_project_machine ON tasks(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_sprints_project_machine ON sprints(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_journal_project_machine ON journal_sessions(project_id, machine_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        CREATE INDEX IF NOT EXISTS idx_backlog_project_machine ON backlog_items(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_metadata') THEN
        CREATE INDEX IF NOT EXISTS idx_sync_metadata_project_machine ON sync_metadata(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        CREATE INDEX IF NOT EXISTS idx_entities_project_machine ON entities(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_ui_state') THEN
        CREATE INDEX IF NOT EXISTS idx_entity_ui_state_project_machine ON entity_ui_state(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        CREATE INDEX IF NOT EXISTS idx_documents_project_machine ON documents(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documentation') THEN
        CREATE INDEX IF NOT EXISTS idx_documentation_project_machine ON documentation(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_references') THEN
        CREATE INDEX IF NOT EXISTS idx_cross_references_project_machine ON cross_references(project_id, machine_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_specifications_project_machine ON specifications(project_id, machine_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        CREATE INDEX IF NOT EXISTS idx_specifications_validated_project_machine ON specifications_validated(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_tasks') THEN
        CREATE INDEX IF NOT EXISTS idx_template_tasks_project_machine ON template_tasks(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_sprints') THEN
        CREATE INDEX IF NOT EXISTS idx_template_sprints_project_machine ON template_sprints(project_id, machine_id);
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION: Report on migration success
-- ============================================================================

DO $$
DECLARE
    fk_count INTEGER := 0;
    fk_record RECORD;
    all_composite BOOLEAN := TRUE;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== MIGRATION VERIFICATION REPORT ===';
    RAISE NOTICE '';
    RAISE NOTICE 'Projects table primary key check...';

    -- Check PK
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'projects'
      AND constraint_type = 'PRIMARY KEY'
      AND constraint_name = 'projects_pkey';

    IF fk_count > 0 THEN
        RAISE NOTICE '  ✓ Primary key constraint exists';
    ELSE
        RAISE WARNING '  ✗ Primary key constraint missing!';
    END IF;

    -- Check path UNIQUE constraint (should NOT exist)
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'projects'
      AND constraint_type = 'UNIQUE'
      AND constraint_name = 'projects_path_key';

    IF fk_count = 0 THEN
        RAISE NOTICE '  ✓ Path UNIQUE constraint removed';
    ELSE
        RAISE WARNING '  ✗ Path UNIQUE constraint still exists!';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE 'Foreign key constraints to projects:';

    -- Check all FK constraints
    FOR fk_record IN
        SELECT
            tc.table_name,
            tc.constraint_name,
            COUNT(kcu.column_name) as column_count,
            STRING_AGG(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_name = 'projects'
            AND tc.table_schema = 'public'
        GROUP BY tc.table_name, tc.constraint_name
        ORDER BY tc.table_name
    LOOP
        IF fk_record.column_count = 2 THEN
            RAISE NOTICE '  ✓ % - composite FK (%)', fk_record.table_name, fk_record.columns;
        ELSE
            RAISE WARNING '  ✗ % - single column FK (%) - SHOULD BE 2!', fk_record.table_name, fk_record.columns;
            all_composite := FALSE;
        END IF;
    END LOOP;

    RAISE NOTICE '';
    IF all_composite THEN
        RAISE NOTICE '✅ ALL FOREIGN KEYS ARE COMPOSITE - Migration successful!';
    ELSE
        RAISE WARNING '⚠️  Some foreign keys are still single-column!';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '=== END VERIFICATION REPORT ===';
END $$;

-- Update table comment
COMMENT ON TABLE projects IS 'Projects with composite PRIMARY KEY (id, machine_id). Same project can exist on multiple machines. project_id from .claude-tasks/data/project_id file. Migration 20251028000003 applied.';
