-- Drop deprecated templates table
-- The old monolithic templates table has been replaced by normalized
-- template_tasks and template_sprints tables
--
-- Migration date: 2025-10-26
-- Related migration: 20251026000000_normalize_template_storage.sql

-- Drop the old templates table
DROP TABLE IF EXISTS templates CASCADE;

-- Drop related table if exists
DROP TABLE IF EXISTS template_versions CASCADE;
DROP TABLE IF EXISTS template_collections CASCADE;

-- Migration complete
-- All template data is now in template_tasks and template_sprints tables
