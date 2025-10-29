-- Fix Foreign Key Constraints for Composite Primary Key
-- Date: 2025-10-28
-- Purpose: Update all FK constraints to reference the composite key (id, machine_id)
--          after the projects table was changed to use a composite primary key
--
-- Related: 20251028000001_file_based_project_id.sql
-- Audit Report: /dev/COMPOSITE_KEY_AUDIT_REPORT.md

-- ============================================================================
-- STEP 1: Add missing machine_id column to specifications_validated
-- ============================================================================

-- Check if specifications_validated table exists before proceeding
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        -- Add machine_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'specifications_validated'
            AND column_name = 'machine_id'
        ) THEN
            ALTER TABLE specifications_validated ADD COLUMN machine_id TEXT;

            -- Populate machine_id from specifications table
            UPDATE specifications_validated sv
            SET machine_id = s.machine_id
            FROM specifications s
            WHERE sv.id = s.id;

            -- Make machine_id NOT NULL
            ALTER TABLE specifications_validated ALTER COLUMN machine_id SET NOT NULL;

            RAISE NOTICE 'Added machine_id column to specifications_validated';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Drop existing single-column FK constraints
-- ============================================================================

-- Tasks table
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_fkey;

-- Sprints table
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_id_fkey;

-- Journal sessions
ALTER TABLE journal_sessions DROP CONSTRAINT IF EXISTS journal_sessions_project_id_fkey;

-- Backlog items (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        ALTER TABLE backlog_items DROP CONSTRAINT IF EXISTS backlog_items_project_id_fkey;
    END IF;
END $$;

-- Sync metadata (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_metadata') THEN
        ALTER TABLE sync_metadata DROP CONSTRAINT IF EXISTS sync_metadata_project_id_fkey;
    END IF;
END $$;

-- Entities
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        ALTER TABLE entities DROP CONSTRAINT IF EXISTS entities_project_id_fkey;
    END IF;
END $$;

-- Entity UI state
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_ui_state') THEN
        ALTER TABLE entity_ui_state DROP CONSTRAINT IF EXISTS entity_ui_state_project_id_fkey;
    END IF;
END $$;

-- Documents
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_project_id_fkey;
    END IF;
END $$;

-- Cross references
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_references') THEN
        ALTER TABLE cross_references DROP CONSTRAINT IF EXISTS cross_references_project_id_fkey;
    END IF;
END $$;

-- Specifications validated
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        ALTER TABLE specifications_validated DROP CONSTRAINT IF EXISTS specifications_validated_project_id_fkey;
    END IF;
END $$;

-- Template tasks
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_tasks') THEN
        ALTER TABLE template_tasks DROP CONSTRAINT IF EXISTS template_tasks_project_id_fkey;
    END IF;
END $$;

-- Template sprints
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_sprints') THEN
        ALTER TABLE template_sprints DROP CONSTRAINT IF EXISTS template_sprints_project_id_fkey;
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Add composite FK constraints
-- ============================================================================

-- Tasks table
ALTER TABLE tasks
ADD CONSTRAINT tasks_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- Sprints table
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

-- Backlog items (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        ALTER TABLE backlog_items
        ADD CONSTRAINT backlog_items_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Sync metadata (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_metadata') THEN
        ALTER TABLE sync_metadata
        ADD CONSTRAINT sync_metadata_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Entities
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        ALTER TABLE entities
        ADD CONSTRAINT entities_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Entity UI state
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_ui_state') THEN
        ALTER TABLE entity_ui_state
        ADD CONSTRAINT entity_ui_state_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Documents
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        ALTER TABLE documents
        ADD CONSTRAINT documents_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Cross references
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_references') THEN
        ALTER TABLE cross_references
        ADD CONSTRAINT cross_references_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Specifications validated
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        ALTER TABLE specifications_validated
        ADD CONSTRAINT specifications_validated_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Template tasks
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_tasks') THEN
        ALTER TABLE template_tasks
        ADD CONSTRAINT template_tasks_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- Template sprints
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_sprints') THEN
        ALTER TABLE template_sprints
        ADD CONSTRAINT template_sprints_project_fkey
        FOREIGN KEY (project_id, machine_id)
        REFERENCES projects(id, machine_id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Ensure composite indexes exist for performance
-- ============================================================================

-- These should already exist from previous migrations, but adding IF NOT EXISTS for safety

CREATE INDEX IF NOT EXISTS idx_tasks_project_machine
ON tasks(project_id, machine_id);

CREATE INDEX IF NOT EXISTS idx_sprints_project_machine
ON sprints(project_id, machine_id);

CREATE INDEX IF NOT EXISTS idx_journal_project_machine
ON journal_sessions(project_id, machine_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'backlog_items') THEN
        CREATE INDEX IF NOT EXISTS idx_backlog_project_machine
        ON backlog_items(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_metadata') THEN
        CREATE INDEX IF NOT EXISTS idx_sync_metadata_project_machine
        ON sync_metadata(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        CREATE INDEX IF NOT EXISTS idx_entities_project_machine
        ON entities(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_ui_state') THEN
        CREATE INDEX IF NOT EXISTS idx_entity_ui_state_project_machine
        ON entity_ui_state(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        CREATE INDEX IF NOT EXISTS idx_documents_project_machine
        ON documents(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cross_references') THEN
        CREATE INDEX IF NOT EXISTS idx_cross_references_project_machine
        ON cross_references(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'specifications_validated') THEN
        CREATE INDEX IF NOT EXISTS idx_specifications_validated_project_machine
        ON specifications_validated(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_tasks') THEN
        CREATE INDEX IF NOT EXISTS idx_template_tasks_project_machine
        ON template_tasks(project_id, machine_id);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'template_sprints') THEN
        CREATE INDEX IF NOT EXISTS idx_template_sprints_project_machine
        ON template_sprints(project_id, machine_id);
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Report on foreign keys referencing projects
DO $$
DECLARE
    fk_record RECORD;
    fk_count INTEGER := 0;
BEGIN
    RAISE NOTICE '=== Foreign Key Verification Report ===';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables with foreign keys to projects:';

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
        fk_count := fk_count + 1;
        IF fk_record.column_count = 2 THEN
            RAISE NOTICE '✅ % - % columns: %',
                fk_record.table_name,
                fk_record.column_count,
                fk_record.columns;
        ELSE
            RAISE WARNING '⚠️  % - % columns: % (SHOULD BE 2!)',
                fk_record.table_name,
                fk_record.column_count,
                fk_record.columns;
        END IF;
    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE 'Total tables with foreign keys to projects: %', fk_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Migration complete. All foreign keys should show 2 columns (project_id, machine_id).';
END $$;

-- Update comment on projects table
COMMENT ON TABLE projects IS 'Projects with composite key (id, machine_id). Foreign keys properly reference composite key. Migration 20251028000002 applied.';
