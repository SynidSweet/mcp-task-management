-- Migration: Fix get_or_create_project to include machine_id
-- Date: 2025-10-28
-- Purpose: Update RPC function to accept and use machine_id for proper project isolation

-- Drop old function
DROP FUNCTION IF EXISTS get_or_create_project(TEXT, TEXT);

-- Recreate with machine_id parameter
CREATE OR REPLACE FUNCTION get_or_create_project(
    project_path TEXT,
    project_name TEXT DEFAULT NULL,
    p_machine_id TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    project_id UUID;
    default_name TEXT;
BEGIN
    -- Try to find existing project by path and machine_id
    -- If machine_id is NULL, match on path only (backward compatibility)
    SELECT id INTO project_id
    FROM projects
    WHERE path = project_path
      AND (p_machine_id IS NULL OR machine_id = p_machine_id);

    IF project_id IS NULL THEN
        -- Create new project with machine_id
        default_name := COALESCE(project_name, split_part(project_path, '/', -1));
        INSERT INTO projects (path, name, machine_id)
        VALUES (project_path, default_name, p_machine_id)
        RETURNING id INTO project_id;
    ELSIF p_machine_id IS NOT NULL THEN
        -- Update existing project with machine_id if it was NULL
        UPDATE projects
        SET machine_id = p_machine_id
        WHERE id = project_id AND machine_id IS NULL;
    END IF;

    RETURN project_id;
END;
$$ LANGUAGE plpgsql;

-- Add comment
COMMENT ON FUNCTION get_or_create_project IS 'Get or create project with machine_id for proper isolation. Updated 2025-10-28 to fix machine_id handling.';
