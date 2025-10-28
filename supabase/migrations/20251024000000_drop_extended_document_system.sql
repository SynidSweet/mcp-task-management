-- Drop Extended Document System Migration
-- This migration removes the old complex document management system
-- in favor of the simple documentation table that syncs from /docs/*.md files

-- ====================================================================
-- PART 1: DROP DEPENDENT OBJECTS
-- ====================================================================

-- Drop triggers
DROP TRIGGER IF EXISTS trigger_update_documents_is_global ON documents;

-- Drop functions
DROP FUNCTION IF EXISTS update_documents_is_global();
DROP FUNCTION IF EXISTS get_document_tree(UUID, TEXT, TEXT);
DROP FUNCTION IF EXISTS set_document_validated_status(UUID, BOOLEAN);
DROP FUNCTION IF EXISTS set_document_implemented_status(UUID, BOOLEAN);

-- ====================================================================
-- PART 2: DROP TABLES (in reverse dependency order)
-- ====================================================================

-- Drop cross-references table (depends on documents)
DROP TABLE IF EXISTS cross_references CASCADE;

-- Drop approved document sections (depends on documents and document_sections)
DROP TABLE IF EXISTS approved_document_sections CASCADE;

-- Drop document sections (depends on documents)
DROP TABLE IF EXISTS document_sections CASCADE;

-- Drop main documents table
DROP TABLE IF EXISTS documents CASCADE;

-- Drop system identifiers table (was created for documents system)
DROP TABLE IF EXISTS system_identifiers CASCADE;

-- ====================================================================
-- PART 3: VERIFICATION
-- ====================================================================

-- Verify tables are dropped
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        RAISE EXCEPTION 'documents table still exists after drop!';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_sections') THEN
        RAISE EXCEPTION 'document_sections table still exists after drop!';
    END IF;

    RAISE NOTICE 'Extended document system successfully removed';
END $$;

-- ====================================================================
-- MIGRATION COMPLETE
-- ====================================================================

COMMENT ON TABLE documentation IS 'Simple documentation table - syncs from /docs/**/*.md files with title, path, and content only';
