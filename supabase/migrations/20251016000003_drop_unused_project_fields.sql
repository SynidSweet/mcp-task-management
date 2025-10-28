-- Drop unused duplicate project fields
-- In early dev - no backwards compatibility needed

-- Drop project_path (unused - NULL everywhere, code uses 'path')
ALTER TABLE projects DROP COLUMN IF EXISTS project_path;

-- Drop project_name (unused - NULL everywhere, code uses 'name')
ALTER TABLE projects DROP COLUMN IF EXISTS project_name;

-- Update comments
COMMENT ON COLUMN projects.path IS 'Project filesystem path (UNIQUE identifier)';
COMMENT ON COLUMN projects.name IS 'Project name';
