-- Normalize Template Storage
-- Migrate from single templates table with JSONB to normalized template_tasks and template_sprints tables
-- that mirror the structure of actual tasks and sprints tables

-- ============================================================================
-- TEMPLATE TASKS TABLE
-- ============================================================================

CREATE TABLE template_tasks (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id TEXT NOT NULL,  -- User-facing ID (e.g., "setup_infrastructure")

    -- Ownership
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT,

    -- Template Metadata
    template_name TEXT NOT NULL,
    description TEXT,
    category TEXT,  -- infrastructure, quality, documentation, etc.
    scope TEXT NOT NULL DEFAULT 'project',  -- 'global' or 'project'
    is_global BOOLEAN DEFAULT false,
    version TEXT DEFAULT '1.0',

    -- Entry Task Marking (KEY FEATURE)
    -- true  = Shows in template listings, can be assigned to sprints
    -- false = Nested subtask, only exists as part of parent template
    is_entry_task BOOLEAN DEFAULT true,

    -- Task Definition (matches tasks table fields)
    title TEXT NOT NULL,
    task_description TEXT,
    priority TEXT DEFAULT 'medium',
    notes TEXT,

    -- Template-Specific: Variables
    -- [{name: "environment", type: "string", required: true, default: "dev"}, ...]
    variables JSONB DEFAULT '[]',

    -- Hierarchy (same as tasks table)
    parent_template_id TEXT,  -- Parent template_id for nested tasks
    child_template_ids JSONB DEFAULT '[]',  -- Array of child template_ids

    -- Template Composition (KEY FEATURE)
    -- If this task IS a reference to another template
    references_template_id TEXT,
    -- Variable overrides when referencing
    override_variables JSONB DEFAULT '{}',

    -- Dependencies (same structure as tasks.dependencies)
    dependencies JSONB DEFAULT '{"blocks": [], "blocked_by": [], "related": []}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT template_tasks_unique UNIQUE(template_id, project_id, scope),
    CONSTRAINT template_tasks_scope_check CHECK (scope IN ('global', 'project')),
    CONSTRAINT template_tasks_priority_check CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

-- Indexes for template_tasks
CREATE INDEX idx_template_tasks_template_id ON template_tasks(template_id);
CREATE INDEX idx_template_tasks_project_id ON template_tasks(project_id);
CREATE INDEX idx_template_tasks_scope ON template_tasks(scope);
CREATE INDEX idx_template_tasks_category ON template_tasks(category);
CREATE INDEX idx_template_tasks_is_entry ON template_tasks(is_entry_task);
CREATE INDEX idx_template_tasks_parent ON template_tasks(parent_template_id);
CREATE INDEX idx_template_tasks_references ON template_tasks(references_template_id);

-- Comments for template_tasks
COMMENT ON TABLE template_tasks IS 'Task templates that mirror tasks table structure with template-specific features';
COMMENT ON COLUMN template_tasks.template_id IS 'User-facing template identifier (e.g., "setup_infrastructure")';
COMMENT ON COLUMN template_tasks.is_entry_task IS 'true = root template shown in listings, false = nested subtask only';
COMMENT ON COLUMN template_tasks.references_template_id IS 'Points to another template_id if this is a reference/composition';
COMMENT ON COLUMN template_tasks.override_variables IS 'Variable overrides when this task references another template';
COMMENT ON COLUMN template_tasks.variables IS 'Variable definitions for this template: [{name, type, required, default}, ...]';

-- ============================================================================
-- TEMPLATE SPRINTS TABLE
-- ============================================================================

CREATE TABLE template_sprints (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id TEXT NOT NULL,  -- User-facing ID (e.g., "feature_development")

    -- Ownership
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT,

    -- Template Metadata
    template_name TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'sprint',
    scope TEXT NOT NULL DEFAULT 'project',
    is_global BOOLEAN DEFAULT false,
    version TEXT DEFAULT '1.0',

    -- Sprint Definition (matches sprints table fields)
    title TEXT NOT NULL,
    sprint_description TEXT,
    start_date DATE,  -- Can be null for dynamic sprints
    end_date DATE,
    focus JSONB DEFAULT '{}',  -- {primary_objective, scope_boundaries}

    -- Template-Specific: Variables
    variables JSONB DEFAULT '[]',  -- [{name, type, required, default}, ...]

    -- Task Assignments (same as sprints.task_ids)
    planning_task_ids JSONB DEFAULT '[]',  -- Array of template_task.template_ids
    milestone_task_ids JSONB DEFAULT '[]',  -- Array of template_task.template_ids

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT template_sprints_unique UNIQUE(template_id, project_id, scope),
    CONSTRAINT template_sprints_scope_check CHECK (scope IN ('global', 'project'))
);

-- Indexes for template_sprints
CREATE INDEX idx_template_sprints_template_id ON template_sprints(template_id);
CREATE INDEX idx_template_sprints_project_id ON template_sprints(project_id);
CREATE INDEX idx_template_sprints_scope ON template_sprints(scope);

-- Comments for template_sprints
COMMENT ON TABLE template_sprints IS 'Sprint templates that mirror sprints table structure with template-specific features';
COMMENT ON COLUMN template_sprints.template_id IS 'User-facing template identifier (e.g., "feature_development")';
COMMENT ON COLUMN template_sprints.variables IS 'Variable definitions for this template: [{name, type, required, default}, ...]';
COMMENT ON COLUMN template_sprints.planning_task_ids IS 'Array of template_task.template_ids for planning phase';
COMMENT ON COLUMN template_sprints.milestone_task_ids IS 'Array of template_task.template_ids for milestones';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger for template_tasks timestamp updates
DROP TRIGGER IF EXISTS update_template_tasks_updated_at ON template_tasks;
CREATE TRIGGER update_template_tasks_updated_at
    BEFORE UPDATE ON template_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for template_sprints timestamp updates
DROP TRIGGER IF EXISTS update_template_sprints_updated_at ON template_sprints;
CREATE TRIGGER update_template_sprints_updated_at
    BEFORE UPDATE ON template_sprints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS
ALTER TABLE template_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_sprints ENABLE ROW LEVEL SECURITY;

-- Policies (allow all for now, can tighten later with auth)
DROP POLICY IF EXISTS "Allow all operations on template_tasks" ON template_tasks;
CREATE POLICY "Allow all operations on template_tasks" ON template_tasks FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on template_sprints" ON template_sprints;
CREATE POLICY "Allow all operations on template_sprints" ON template_sprints FOR ALL USING (true);

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================

-- This migration creates new normalized tables for templates.
-- The old 'templates' table is NOT modified and remains as a backup.
--
-- Next steps:
-- 1. Run data migration script to populate new tables from existing templates
-- 2. Update template tools to use new schema
-- 3. Update file monitor for bidirectional sync
-- 4. After validation period, optionally rename 'templates' to 'templates_deprecated'
--
-- Rollback: DROP TABLE template_sprints; DROP TABLE template_tasks;
