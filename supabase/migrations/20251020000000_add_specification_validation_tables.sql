-- Add specification validation system with parallel validated tables
--
-- Purpose: Support AI agent suggestions vs human-validated specifications
--
-- Design: Mirror tables for validated state
--   - specifications_validated: Exact mirror of specifications table
--   - specification_requirements_validated: Simple copy of requirements
--   - specification_constraints_validated: Simple copy of constraints
--
-- Usage:
--   - AI agents write to main tables (suggestions)
--   - Frontend writes to validated tables (human approval)
--   - MCP tools query both to show validation status
--
-- Created: 2025-10-20

-- ============================================================================
-- 1. specifications_validated - Exact mirror of specifications table
-- ============================================================================

CREATE TABLE IF NOT EXISTS specifications_validated (
  -- Primary key (same UUID as specifications.id)
  id UUID PRIMARY KEY,

  -- Project isolation
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  machine_id TEXT NOT NULL,

  -- Core specification fields (validated snapshot)
  specification_name TEXT NOT NULL,
  specification_type TEXT NOT NULL,
  description TEXT DEFAULT '',

  -- Dual-ID system (validated snapshot)
  display_id TEXT NOT NULL,
  parent_display_id TEXT,
  parent_id UUID,  -- FK to parent specification (validated)

  -- Hierarchy fields
  level_depth INTEGER DEFAULT 0,
  sort_order INTEGER DEFAULT 0,

  -- Status fields (always true in validated table)
  approved BOOLEAN DEFAULT true,
  implemented BOOLEAN DEFAULT false,
  validated BOOLEAN DEFAULT true,

  -- Version tracking
  version INTEGER DEFAULT 1,

  -- Validation metadata
  validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  validated_by TEXT,  -- Optional: user identifier who validated

  -- Original timestamps (copied from main table)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for specifications_validated
CREATE INDEX IF NOT EXISTS idx_specifications_validated_project
  ON specifications_validated(project_id, machine_id);

CREATE INDEX IF NOT EXISTS idx_specifications_validated_display_id
  ON specifications_validated(display_id);

CREATE INDEX IF NOT EXISTS idx_specifications_validated_parent
  ON specifications_validated(parent_id);

CREATE INDEX IF NOT EXISTS idx_specifications_validated_type
  ON specifications_validated(specification_type);

CREATE INDEX IF NOT EXISTS idx_specifications_validated_validated_at
  ON specifications_validated(validated_at);

-- Comments
COMMENT ON TABLE specifications_validated IS
  'Validated specifications snapshots - contains last human-approved version';

COMMENT ON COLUMN specifications_validated.id IS
  'Same UUID as specifications.id - links to current version';

COMMENT ON COLUMN specifications_validated.validated_at IS
  'Timestamp when human validated this version';

COMMENT ON COLUMN specifications_validated.validated_by IS
  'Optional identifier for user who validated (e.g., email or username)';


-- ============================================================================
-- 2. specification_requirements_validated - Simple copy, no FK linkage
-- ============================================================================

CREATE TABLE IF NOT EXISTS specification_requirements_validated (
  -- New UUID for each validated requirement (not linked to original)
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- References validated specification
  specification_id UUID NOT NULL REFERENCES specifications_validated(id) ON DELETE CASCADE,

  -- Requirement content
  requirement_text TEXT NOT NULL,

  -- Validation timestamp
  validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Original timestamp
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for specification_requirements_validated
CREATE INDEX IF NOT EXISTS idx_spec_requirements_validated_spec_id
  ON specification_requirements_validated(specification_id);

CREATE INDEX IF NOT EXISTS idx_spec_requirements_validated_validated_at
  ON specification_requirements_validated(validated_at);

-- Comments
COMMENT ON TABLE specification_requirements_validated IS
  'Validated requirements - simple copy for diff comparison in frontend';

COMMENT ON COLUMN specification_requirements_validated.id IS
  'New UUID (not linked to original requirement IDs) - used for simple storage only';


-- ============================================================================
-- 3. specification_constraints_validated - Simple copy, no FK linkage
-- ============================================================================

CREATE TABLE IF NOT EXISTS specification_constraints_validated (
  -- New UUID for each validated constraint (not linked to original)
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- References validated specification
  specification_id UUID NOT NULL REFERENCES specifications_validated(id) ON DELETE CASCADE,

  -- Constraint content
  constraint_text TEXT NOT NULL,

  -- Validation timestamp
  validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Original timestamp
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for specification_constraints_validated
CREATE INDEX IF NOT EXISTS idx_spec_constraints_validated_spec_id
  ON specification_constraints_validated(specification_id);

CREATE INDEX IF NOT EXISTS idx_spec_constraints_validated_validated_at
  ON specification_constraints_validated(validated_at);

-- Comments
COMMENT ON TABLE specification_constraints_validated IS
  'Validated constraints - simple copy for diff comparison in frontend';

COMMENT ON COLUMN specification_constraints_validated.id IS
  'New UUID (not linked to original constraint IDs) - used for simple storage only';


-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Summary of changes:
-- ✓ Created specifications_validated (exact mirror)
-- ✓ Created specification_requirements_validated (simple copy)
-- ✓ Created specification_constraints_validated (simple copy)
-- ✓ Added indexes for performance
-- ✓ Added comments for documentation
--
-- Next steps:
-- 1. Run this migration in Supabase SQL Editor
-- 2. Update MCP tools to query both tables
-- 3. Frontend implements validation workflow
