-- Add Templates Schema for Claude Tasks MCP System
-- This migration adds the missing templates tables to support dual storage

-- Template tables for dual storage support
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    template_type TEXT NOT NULL, -- 'task_templates', 'documentation_templates', etc.
    scope TEXT NOT NULL DEFAULT 'project', -- 'project' or 'global'
    is_global BOOLEAN DEFAULT false,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    hash TEXT -- For conflict detection
);

-- Template versions for version history (future feature)
CREATE TABLE IF NOT EXISTS template_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id TEXT NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT
);

-- Template collections (for organizing templates)
CREATE TABLE IF NOT EXISTS template_collections (
    id TEXT PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    scope TEXT NOT NULL DEFAULT 'project',
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    hash TEXT
);

-- Template indexes for performance
CREATE INDEX IF NOT EXISTS idx_templates_project_id ON templates(project_id);
CREATE INDEX IF NOT EXISTS idx_templates_type_scope ON templates(template_type, scope);
CREATE INDEX IF NOT EXISTS idx_templates_updated_at ON templates(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_templates_global ON templates(is_global) WHERE is_global = true;
CREATE INDEX IF NOT EXISTS idx_template_versions_template_id ON template_versions(template_id);
CREATE INDEX IF NOT EXISTS idx_template_versions_created_at ON template_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_template_collections_project_id ON template_collections(project_id);
CREATE INDEX IF NOT EXISTS idx_template_collections_scope ON template_collections(scope);

-- Template triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_templates_updated_at ON templates;
CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_template_collections_updated_at ON template_collections;
CREATE TRIGGER update_template_collections_updated_at BEFORE UPDATE ON template_collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Template table RLS
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_collections ENABLE ROW LEVEL SECURITY;

-- Template table policies
DROP POLICY IF EXISTS "Allow all operations on templates" ON templates;
CREATE POLICY "Allow all operations on templates" ON templates FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on template_versions" ON template_versions;
CREATE POLICY "Allow all operations on template_versions" ON template_versions FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on template_collections" ON template_collections;
CREATE POLICY "Allow all operations on template_collections" ON template_collections FOR ALL USING (true);

-- Update the project_summary view to include template counts
DROP VIEW IF EXISTS project_summary;
CREATE VIEW project_summary AS
SELECT 
    p.id,
    p.name,
    p.path,
    COUNT(DISTINCT t.id) as task_count,
    COUNT(DISTINCT s.id) as sprint_count,
    COUNT(DISTINCT j.id) as session_count,
    COUNT(DISTINCT tmpl.id) as template_count,
    COUNT(DISTINCT tc.id) as collection_count,
    p.updated_at
FROM projects p
LEFT JOIN tasks t ON p.id = t.project_id
LEFT JOIN sprints s ON p.id = s.project_id  
LEFT JOIN journal_sessions j ON p.id = j.project_id
LEFT JOIN templates tmpl ON p.id = tmpl.project_id
LEFT JOIN template_collections tc ON p.id = tc.project_id
GROUP BY p.id, p.name, p.path, p.updated_at;

-- Add template-related entries to sync_metadata table for templates
-- This ensures templates participate in dual storage sync
-- (No additional tables needed - sync_metadata already supports arbitrary entity types)