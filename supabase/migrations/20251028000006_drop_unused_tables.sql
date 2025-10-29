-- Migration: Drop Unused and Legacy Tables
-- Date: 2025-10-28
-- Purpose: Clean up database by removing unused tables to avoid confusing AI agents
--
-- Tables being removed:
--   - Old Entity System validation tables (replaced by specifications_validated system)
--   - Empty/unimplemented features
--   - Duplicate/incorrect validation tables
--
-- Tables being KEPT:
--   - mcp_configs (used by UnifiedFileMonitor for MCP config sync)
--   - specifications_validated (current validation system - empty is normal)
--   - specification_requirements_validated (current system - empty is normal)
--   - specification_constraints_validated (current system - empty is normal)
--   - conversations / conversation_messages (used by frontend for AI chatting)

-- ============================================================================
-- OLD ENTITY SYSTEM (Replaced by specifications system)
-- ============================================================================

-- These tables contain 759 legacy records from the old entity-based requirements system
-- The entity system was replaced by the specifications system in Oct 2025

DROP TABLE IF EXISTS approved_entity_requirements CASCADE;
DROP TABLE IF EXISTS approved_entity_constraints CASCADE;

-- ============================================================================
-- EMPTY/UNIMPLEMENTED FEATURES
-- ============================================================================

-- Backlog feature was never implemented (no tools, no data)
DROP TABLE IF EXISTS backlog_items CASCADE;

-- Old sync metadata (UnifiedFileMonitor doesn't use this)
DROP TABLE IF EXISTS sync_metadata CASCADE;

-- Document tags feature never implemented
DROP TABLE IF EXISTS document_tags CASCADE;
DROP TABLE IF EXISTS approved_document_tags CASCADE;

-- Duplicate/incorrect validation tables (replaced by spec_*_validated tables)
DROP TABLE IF EXISTS approved_specification_requirements CASCADE;
DROP TABLE IF EXISTS approved_specification_constraints CASCADE;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    -- Count remaining tables (should be 18 after removing 8)
    SELECT COUNT(*) INTO remaining_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

    RAISE NOTICE '=== Database Cleanup Complete ===';
    RAISE NOTICE '';
    RAISE NOTICE 'Remaining tables: %', remaining_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Removed:';
    RAISE NOTICE '  - 2 legacy entity validation tables (759 old records)';
    RAISE NOTICE '  - 6 empty/unimplemented tables';
    RAISE NOTICE '';
    RAISE NOTICE 'Kept:';
    RAISE NOTICE '  - mcp_configs (used for MCP config sync)';
    RAISE NOTICE '  - specifications_validated system (empty is normal)';
    RAISE NOTICE '  - conversations system (used by frontend)';
END $$;
