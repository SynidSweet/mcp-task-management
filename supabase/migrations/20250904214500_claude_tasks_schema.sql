
-- Supabase Schema for Claude Tasks MCP System
-- This schema supports multi-project task management with sync capabilities

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table for multi-project isolation
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    machine_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks table with JSONB for flexibility (preserves existing structure)
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    hash TEXT -- For conflict detection
);

-- Sprints table
CREATE TABLE IF NOT EXISTS sprints (
    id TEXT PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    hash TEXT
);

-- Journal sessions
CREATE TABLE IF NOT EXISTS journal_sessions (
    id TEXT PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    session_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backlog items (separate from tasks for better organization)
CREATE TABLE IF NOT EXISTS backlog_items (
    id TEXT PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

-- Sync metadata for conflict resolution and sync tracking
CREATE TABLE IF NOT EXISTS sync_metadata (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    local_hash TEXT,
    remote_hash TEXT,
    local_timestamp TIMESTAMPTZ,
    remote_timestamp TIMESTAMPTZ,
    last_sync TIMESTAMPTZ DEFAULT NOW(),
    conflict_resolution TEXT, -- 'local_wins', 'remote_wins', 'merged'
    PRIMARY KEY (entity_type, entity_id, project_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sprints_project_id ON sprints(project_id);
CREATE INDEX IF NOT EXISTS idx_journal_project_id ON journal_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_journal_created_at ON journal_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backlog_project_id ON backlog_items(project_id);
CREATE INDEX IF NOT EXISTS idx_sync_metadata_project ON sync_metadata(project_id, entity_type);

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
DROP TRIGGER IF EXISTS update_sprints_updated_at ON sprints;
CREATE TRIGGER update_sprints_updated_at BEFORE UPDATE ON sprints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_journal_updated_at ON journal_sessions;
CREATE TRIGGER update_journal_updated_at BEFORE UPDATE ON journal_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_backlog_updated_at ON backlog_items;
CREATE TRIGGER update_backlog_updated_at BEFORE UPDATE ON backlog_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies for multi-project isolation
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE sprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE backlog_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata ENABLE ROW LEVEL SECURITY;

-- For now, allow all operations (you can tighten this later with auth)
DROP POLICY IF EXISTS "Allow all operations on projects" ON projects;
CREATE POLICY "Allow all operations on projects" ON projects FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on tasks" ON tasks;
CREATE POLICY "Allow all operations on tasks" ON tasks FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on sprints" ON sprints;
CREATE POLICY "Allow all operations on sprints" ON sprints FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on journal" ON journal_sessions;
CREATE POLICY "Allow all operations on journal" ON journal_sessions FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on backlog" ON backlog_items;
CREATE POLICY "Allow all operations on backlog" ON backlog_items FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on sync_metadata" ON sync_metadata;
CREATE POLICY "Allow all operations on sync_metadata" ON sync_metadata FOR ALL USING (true);

-- Views for easier querying
DROP VIEW IF EXISTS project_summary;
CREATE VIEW project_summary AS
SELECT 
    p.id,
    p.name,
    p.path,
    COUNT(DISTINCT t.id) as task_count,
    COUNT(DISTINCT s.id) as sprint_count,
    COUNT(DISTINCT j.id) as session_count,
    p.updated_at
FROM projects p
LEFT JOIN tasks t ON p.id = t.project_id
LEFT JOIN sprints s ON p.id = s.project_id  
LEFT JOIN journal_sessions j ON p.id = j.project_id
GROUP BY p.id, p.name, p.path, p.updated_at;

-- Function to get or create project
CREATE OR REPLACE FUNCTION get_or_create_project(project_path TEXT, project_name TEXT DEFAULT NULL)
RETURNS UUID AS $$
DECLARE
    project_id UUID;
    default_name TEXT;
BEGIN
    -- Try to find existing project
    SELECT id INTO project_id FROM projects WHERE path = project_path;
    
    IF project_id IS NULL THEN
        -- Create new project
        default_name := COALESCE(project_name, split_part(project_path, '/', -1));
        INSERT INTO projects (path, name) VALUES (project_path, default_name) RETURNING id INTO project_id;
    END IF;
    
    RETURN project_id;
END;
$$ LANGUAGE plpgsql;
