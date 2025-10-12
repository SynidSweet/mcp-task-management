-- Requirements System Schema - Optimized for incremental updates
-- Each entity is a separate row for fine-grained change tracking

-- Projects table (reuse existing)
-- Already exists from main schema

-- Entities table - each entity is a separate row
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL, -- Machine-specific entity state
    entity_path TEXT NOT NULL, -- e.g. "user_management.authentication.login_screen"
    entity_name TEXT NOT NULL, -- e.g. "login_screen"
    entity_type TEXT NOT NULL, -- module, screen, component, feature, etc.
    description TEXT,
    approved BOOLEAN DEFAULT false,
    parent_id UUID REFERENCES entities(id) ON DELETE CASCADE, -- Direct parent reference
    level_depth INTEGER DEFAULT 0, -- 0 = root, 1 = child, 2 = grandchild, etc.
    sort_order INTEGER DEFAULT 0, -- Order within siblings
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    UNIQUE(project_id, machine_id, entity_path)
);

-- Requirements table - each requirement is a separate row
CREATE TABLE IF NOT EXISTS entity_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    requirement_text TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Constraints table - each constraint is a separate row  
CREATE TABLE IF NOT EXISTS entity_constraints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    constraint_text TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Resources table - each resource is a separate row
CREATE TABLE IF NOT EXISTS entity_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL, -- 'screenshots', 'wireframes', 'documentation', 'api_specs', 'design_tokens'
    resource_url TEXT NOT NULL,
    resource_name TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data schema table - input/output schemas for entities
CREATE TABLE IF NOT EXISTS entity_data_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    schema_type TEXT NOT NULL, -- 'input', 'output'
    schema_definition TEXT NOT NULL, -- JSON schema or text description
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dependencies table - entity dependencies
CREATE TABLE IF NOT EXISTS entity_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    depends_on_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    dependency_type TEXT DEFAULT 'requires', -- 'requires', 'blocks', 'relates_to'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_id, depends_on_entity_id)
);

-- UI state table - collapse/expand states per machine
CREATE TABLE IF NOT EXISTS entity_ui_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL,
    entity_path TEXT NOT NULL,
    is_collapsed BOOLEAN DEFAULT false,
    is_selected BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, machine_id, entity_path)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_project_machine ON entities(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_entities_parent ON entities(parent_id);
CREATE INDEX IF NOT EXISTS idx_entities_path ON entities(entity_path);
CREATE INDEX IF NOT EXISTS idx_requirements_entity ON entity_requirements(entity_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_constraints_entity ON entity_constraints(entity_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_resources_entity ON entity_resources(entity_id, resource_type);
CREATE INDEX IF NOT EXISTS idx_ui_state_machine ON entity_ui_state(project_id, machine_id);

-- Functions for entity management

-- Function to get complete entity tree for a project/machine
CREATE OR REPLACE FUNCTION get_entity_tree(p_project_id UUID, p_machine_id TEXT)
RETURNS TABLE (
    entity_id UUID,
    entity_path TEXT,
    entity_name TEXT,
    entity_type TEXT,
    description TEXT,
    approved BOOLEAN,
    parent_id UUID,
    level_depth INTEGER,
    sort_order INTEGER,
    requirements TEXT[], -- Array of requirement texts
    constraints TEXT[], -- Array of constraint texts
    is_collapsed BOOLEAN,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.entity_path,
        e.entity_name,
        e.entity_type,
        e.description,
        e.approved,
        e.parent_id,
        e.level_depth,
        e.sort_order,
        COALESCE(ARRAY_AGG(DISTINCT r.requirement_text ORDER BY r.sort_order) FILTER (WHERE r.requirement_text IS NOT NULL), '{}'),
        COALESCE(ARRAY_AGG(DISTINCT c.constraint_text ORDER BY c.sort_order) FILTER (WHERE c.constraint_text IS NOT NULL), '{}'),
        COALESCE(ui.is_collapsed, false),
        e.updated_at
    FROM entities e
    LEFT JOIN entity_requirements r ON e.id = r.entity_id
    LEFT JOIN entity_constraints c ON e.id = c.entity_id  
    LEFT JOIN entity_ui_state ui ON e.project_id = ui.project_id AND e.machine_id = ui.machine_id AND e.entity_path = ui.entity_path
    WHERE e.project_id = p_project_id AND e.machine_id = p_machine_id
    GROUP BY e.id, e.entity_path, e.entity_name, e.entity_type, e.description, e.approved, e.parent_id, e.level_depth, e.sort_order, ui.is_collapsed, e.updated_at
    ORDER BY e.level_depth, e.sort_order;
END;
$$ LANGUAGE plpgsql;

-- Function to create or update an entity with all its data
CREATE OR REPLACE FUNCTION upsert_entity(
    p_project_id UUID,
    p_machine_id TEXT,
    p_entity_path TEXT,
    p_entity_name TEXT,
    p_entity_type TEXT,
    p_description TEXT,
    p_approved BOOLEAN,
    p_parent_path TEXT DEFAULT NULL,
    p_requirements TEXT[] DEFAULT '{}',
    p_constraints TEXT[] DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    entity_uuid UUID;
    parent_uuid UUID;
    req_text TEXT;
    const_text TEXT;
    depth_level INTEGER;
BEGIN
    -- Calculate depth level from path
    depth_level := ARRAY_LENGTH(STRING_TO_ARRAY(p_entity_path, '.'), 1) - 1;
    
    -- Get parent ID if parent_path is provided
    IF p_parent_path IS NOT NULL THEN
        SELECT id INTO parent_uuid FROM entities 
        WHERE project_id = p_project_id AND machine_id = p_machine_id AND entity_path = p_parent_path;
    END IF;
    
    -- Insert or update entity
    INSERT INTO entities (
        project_id, machine_id, entity_path, entity_name, entity_type, 
        description, approved, parent_id, level_depth
    ) VALUES (
        p_project_id, p_machine_id, p_entity_path, p_entity_name, p_entity_type,
        p_description, p_approved, parent_uuid, depth_level
    ) ON CONFLICT (project_id, machine_id, entity_path) DO UPDATE SET
        entity_name = EXCLUDED.entity_name,
        entity_type = EXCLUDED.entity_type,
        description = EXCLUDED.description,
        approved = EXCLUDED.approved,
        parent_id = EXCLUDED.parent_id,
        level_depth = EXCLUDED.level_depth,
        updated_at = NOW(),
        version = entities.version + 1
    RETURNING id INTO entity_uuid;
    
    -- Clear and re-add requirements
    DELETE FROM entity_requirements WHERE entity_id = entity_uuid;
    FOREACH req_text IN ARRAY p_requirements LOOP
        INSERT INTO entity_requirements (entity_id, requirement_text, sort_order)
        VALUES (entity_uuid, req_text, ARRAY_POSITION(p_requirements, req_text));
    END LOOP;
    
    -- Clear and re-add constraints
    DELETE FROM entity_constraints WHERE entity_id = entity_uuid;
    FOREACH const_text IN ARRAY p_constraints LOOP
        INSERT INTO entity_constraints (entity_id, constraint_text, sort_order)
        VALUES (entity_uuid, const_text, ARRAY_POSITION(p_constraints, const_text));
    END LOOP;
    
    RETURN entity_uuid;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_requirements_updated_at BEFORE UPDATE ON entity_requirements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_constraints_updated_at BEFORE UPDATE ON entity_constraints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();