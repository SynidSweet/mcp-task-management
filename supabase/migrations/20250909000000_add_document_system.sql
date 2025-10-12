-- Document Management System Migration
-- This migration adds a complete document management system with shared ID management
-- for both documents and entities, enabling cross-references and unified display IDs.

-- ====================================================================
-- PART 1: SHARED ID MANAGEMENT SYSTEM
-- ====================================================================

-- System identifiers table - manages unique display IDs across documents and entities
CREATE TABLE IF NOT EXISTS system_identifiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL,
    display_id TEXT NOT NULL, -- Human-readable ID (e.g., "USER-001", "DOC-005", "AUTH-123")
    entity_type TEXT NOT NULL CHECK (entity_type IN ('entity', 'document')),
    entity_uuid UUID NOT NULL, -- References either entities.id or documents.id
    sequence_number INTEGER NOT NULL, -- For auto-generated IDs within project
    is_auto_generated BOOLEAN DEFAULT true, -- Whether ID was auto-generated or manually assigned
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, machine_id, display_id), -- Ensure unique display IDs per project/machine
    UNIQUE(project_id, machine_id, entity_type, entity_uuid) -- One display_id per entity
);

-- ====================================================================
-- PART 2: DOCUMENT MANAGEMENT TABLES
-- ====================================================================

-- Main documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL,
    document_path TEXT NOT NULL, -- Hierarchical path like "user_guide.authentication.login_process"
    document_title TEXT NOT NULL,
    document_type TEXT NOT NULL, -- 'guide', 'specification', 'api_doc', 'requirements', 'design'
    description TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'approved', 'archived')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    parent_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    level_depth INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    
    -- Approval system fields
    approved BOOLEAN DEFAULT false,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    approval_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    
    UNIQUE(project_id, machine_id, document_path)
);

-- Document sections table - stores current document content
CREATE TABLE IF NOT EXISTS document_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL, -- 'overview', 'content', 'examples', 'api_endpoints', 'constraints'
    section_title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_format TEXT DEFAULT 'markdown' CHECK (content_format IN ('markdown', 'html', 'json', 'yaml', 'text')),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Approved document sections table - stores approved versions
CREATE TABLE IF NOT EXISTS approved_document_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL,
    section_title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_format TEXT DEFAULT 'markdown',
    sort_order INTEGER DEFAULT 0,
    approved_by TEXT,
    approved_at TIMESTAMPTZ DEFAULT NOW(),
    approval_notes TEXT,
    original_section_id UUID REFERENCES document_sections(id), -- Links to current version
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================================================
-- PART 3: CROSS-REFERENCE SYSTEM
-- ====================================================================

-- Cross-references table - links documents to entities and vice versa
CREATE TABLE IF NOT EXISTS cross_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('entity', 'document')),
    source_id UUID NOT NULL, -- References either entities.id or documents.id
    target_type TEXT NOT NULL CHECK (target_type IN ('entity', 'document')),
    target_id UUID NOT NULL, -- References either entities.id or documents.id
    reference_type TEXT DEFAULT 'relates_to' CHECK (reference_type IN (
        'relates_to', 'documents', 'specifies', 'implements', 'depends_on', 'blocks', 'validates'
    )),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    UNIQUE(source_type, source_id, target_type, target_id, reference_type)
);

-- ====================================================================
-- PART 4: MIGRATE EXISTING ENTITIES TO SHARED ID SYSTEM
-- ====================================================================

-- Add display_id column to entities table if it doesn't exist
ALTER TABLE entities ADD COLUMN IF NOT EXISTS display_id TEXT;

-- Function to generate next display ID for a project/machine/type combination
CREATE OR REPLACE FUNCTION generate_next_display_id(
    p_project_id UUID,
    p_machine_id TEXT,
    p_entity_type TEXT,
    p_prefix TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    next_sequence INTEGER;
    display_id_result TEXT;
    default_prefix TEXT;
BEGIN
    -- Set default prefix based on entity type
    default_prefix := CASE 
        WHEN p_entity_type = 'document' THEN 'DOC'
        WHEN p_entity_type = 'entity' THEN 'ENT'
        ELSE 'ID'
    END;
    
    -- Get next sequence number for this project/machine/type
    SELECT COALESCE(MAX(sequence_number), 0) + 1 INTO next_sequence
    FROM system_identifiers 
    WHERE project_id = p_project_id 
    AND machine_id = p_machine_id
    AND entity_type = p_entity_type;
    
    -- Generate display ID
    display_id_result := COALESCE(p_prefix, default_prefix) || '-' || LPAD(next_sequence::TEXT, 3, '0');
    
    RETURN display_id_result;
END;
$$ LANGUAGE plpgsql;

-- Function to assign display ID to an entity or document
CREATE OR REPLACE FUNCTION assign_display_id(
    p_project_id UUID,
    p_machine_id TEXT,
    p_entity_type TEXT,
    p_entity_uuid UUID,
    p_custom_display_id TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    generated_display_id TEXT;
    final_display_id TEXT;
    sequence_num INTEGER;
BEGIN
    -- Check if entity already has a display ID
    SELECT display_id INTO final_display_id 
    FROM system_identifiers 
    WHERE project_id = p_project_id 
    AND machine_id = p_machine_id 
    AND entity_type = p_entity_type 
    AND entity_uuid = p_entity_uuid;
    
    IF final_display_id IS NOT NULL THEN
        RETURN final_display_id;
    END IF;
    
    -- Generate or use custom display ID
    IF p_custom_display_id IS NOT NULL THEN
        final_display_id := p_custom_display_id;
        sequence_num := COALESCE(
            (SELECT MAX(sequence_number) FROM system_identifiers 
             WHERE project_id = p_project_id AND machine_id = p_machine_id AND entity_type = p_entity_type), 
            0
        ) + 1;
    ELSE
        final_display_id := generate_next_display_id(p_project_id, p_machine_id, p_entity_type);
        sequence_num := SUBSTRING(final_display_id FROM '\-(\d+)$')::INTEGER;
    END IF;
    
    -- Insert into system_identifiers
    INSERT INTO system_identifiers (
        project_id, machine_id, display_id, entity_type, entity_uuid, 
        sequence_number, is_auto_generated
    ) VALUES (
        p_project_id, p_machine_id, final_display_id, p_entity_type, p_entity_uuid,
        sequence_num, p_custom_display_id IS NULL
    );
    
    RETURN final_display_id;
END;
$$ LANGUAGE plpgsql;

-- Migrate existing entities to use shared display ID system
DO $$
DECLARE
    entity_record RECORD;
    generated_display_id TEXT;
BEGIN
    -- For each existing entity, assign a display ID
    FOR entity_record IN 
        SELECT id, project_id, machine_id, entity_path, display_id
        FROM entities 
        WHERE display_id IS NULL OR display_id = ''
    LOOP
        -- Generate display ID from entity_path (last component) or auto-generate
        IF entity_record.entity_path IS NOT NULL AND entity_record.entity_path != '' THEN
            IF entity_record.entity_path LIKE '%.%' THEN
                generated_display_id := UPPER(SPLIT_PART(entity_record.entity_path, '.', -1));
            ELSE
                generated_display_id := UPPER(entity_record.entity_path);
            END IF;
            
            -- Ensure uniqueness by checking existing display IDs
            WHILE EXISTS (
                SELECT 1 FROM system_identifiers 
                WHERE project_id = entity_record.project_id 
                AND machine_id = entity_record.machine_id 
                AND display_id = generated_display_id
            ) LOOP
                generated_display_id := generated_display_id || '_' || 
                    (SELECT COUNT(*) + 1 FROM system_identifiers 
                     WHERE display_id LIKE generated_display_id || '%');
            END LOOP;
        ELSE
            -- Auto-generate if no entity_path
            generated_display_id := generate_next_display_id(
                entity_record.project_id, 
                entity_record.machine_id, 
                'entity'
            );
        END IF;
        
        -- Assign the display ID
        generated_display_id := assign_display_id(
            entity_record.project_id,
            entity_record.machine_id,
            'entity',
            entity_record.id,
            generated_display_id
        );
        
        -- Update the entity with the display ID
        UPDATE entities 
        SET display_id = generated_display_id
        WHERE id = entity_record.id;
    END LOOP;
END $$;

-- ====================================================================
-- PART 5: INDEXES FOR PERFORMANCE
-- ====================================================================

-- System identifiers indexes
CREATE INDEX IF NOT EXISTS idx_system_identifiers_project_machine ON system_identifiers(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_system_identifiers_display_id ON system_identifiers(project_id, machine_id, display_id);
CREATE INDEX IF NOT EXISTS idx_system_identifiers_entity_type ON system_identifiers(entity_type);
CREATE INDEX IF NOT EXISTS idx_system_identifiers_entity_uuid ON system_identifiers(entity_uuid);

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_project_machine ON documents(project_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent_id);
CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(document_path);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_approved ON documents(approved);

-- Document sections indexes
CREATE INDEX IF NOT EXISTS idx_document_sections_document ON document_sections(document_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_document_sections_type ON document_sections(document_id, section_type);

-- Approved document sections indexes
CREATE INDEX IF NOT EXISTS idx_approved_sections_document ON approved_document_sections(document_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_approved_sections_original ON approved_document_sections(original_section_id);

-- Cross-references indexes
CREATE INDEX IF NOT EXISTS idx_cross_references_source ON cross_references(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_cross_references_target ON cross_references(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_cross_references_type ON cross_references(reference_type);
CREATE INDEX IF NOT EXISTS idx_cross_references_project ON cross_references(project_id, machine_id);

-- Update existing entity indexes to include display_id
CREATE INDEX IF NOT EXISTS idx_entities_display_id ON entities(project_id, machine_id, display_id);

-- ====================================================================
-- PART 6: FUNCTIONS FOR DOCUMENT MANAGEMENT
-- ====================================================================

-- Function to get document tree with sections
CREATE OR REPLACE FUNCTION get_document_tree(p_project_id UUID, p_machine_id TEXT)
RETURNS TABLE (
    document_id UUID,
    document_path TEXT,
    document_title TEXT,
    document_type TEXT,
    description TEXT,
    status TEXT,
    approved BOOLEAN,
    display_id TEXT,
    parent_id UUID,
    level_depth INTEGER,
    sort_order INTEGER,
    sections JSONB,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.document_path,
        d.document_title,
        d.document_type,
        d.description,
        d.status,
        d.approved,
        si.display_id,
        d.parent_id,
        d.level_depth,
        d.sort_order,
        COALESCE(
            JSON_AGG(
                JSON_BUILD_OBJECT(
                    'id', ds.id,
                    'section_type', ds.section_type,
                    'section_title', ds.section_title,
                    'content', ds.content,
                    'content_format', ds.content_format,
                    'sort_order', ds.sort_order
                ) ORDER BY ds.sort_order
            ) FILTER (WHERE ds.id IS NOT NULL), 
            '[]'::jsonb
        ) as sections,
        d.updated_at
    FROM documents d
    LEFT JOIN document_sections ds ON d.id = ds.document_id
    LEFT JOIN system_identifiers si ON d.id = si.entity_uuid AND si.entity_type = 'document'
    WHERE d.project_id = p_project_id AND d.machine_id = p_machine_id
    GROUP BY d.id, d.document_path, d.document_title, d.document_type, d.description, 
             d.status, d.approved, si.display_id, d.parent_id, d.level_depth, d.sort_order, d.updated_at
    ORDER BY d.level_depth, d.sort_order;
END;
$$ LANGUAGE plpgsql;

-- Function to create or update document with sections
CREATE OR REPLACE FUNCTION upsert_document(
    p_project_id UUID,
    p_machine_id TEXT,
    p_document_path TEXT,
    p_document_title TEXT,
    p_document_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_status TEXT DEFAULT 'draft',
    p_priority TEXT DEFAULT 'medium',
    p_parent_path TEXT DEFAULT NULL,
    p_sections JSONB DEFAULT '[]'
) RETURNS UUID AS $$
DECLARE
    document_uuid UUID;
    parent_uuid UUID;
    section_data JSONB;
    depth_level INTEGER;
    assigned_display_id TEXT;
BEGIN
    -- Calculate depth level from path
    depth_level := ARRAY_LENGTH(STRING_TO_ARRAY(p_document_path, '.'), 1) - 1;
    
    -- Get parent ID if parent_path is provided
    IF p_parent_path IS NOT NULL THEN
        SELECT id INTO parent_uuid FROM documents 
        WHERE project_id = p_project_id AND machine_id = p_machine_id AND document_path = p_parent_path;
    END IF;
    
    -- Insert or update document
    INSERT INTO documents (
        project_id, machine_id, document_path, document_title, document_type,
        description, status, priority, parent_id, level_depth
    ) VALUES (
        p_project_id, p_machine_id, p_document_path, p_document_title, p_document_type,
        p_description, p_status, p_priority, parent_uuid, depth_level
    ) ON CONFLICT (project_id, machine_id, document_path) DO UPDATE SET
        document_title = EXCLUDED.document_title,
        document_type = EXCLUDED.document_type,
        description = EXCLUDED.description,
        status = EXCLUDED.status,
        priority = EXCLUDED.priority,
        parent_id = EXCLUDED.parent_id,
        level_depth = EXCLUDED.level_depth,
        updated_at = NOW(),
        version = documents.version + 1
    RETURNING id INTO document_uuid;
    
    -- Assign display ID if not already assigned
    assigned_display_id := assign_display_id(p_project_id, p_machine_id, 'document', document_uuid);
    
    -- Clear and re-add sections if provided
    IF p_sections IS NOT NULL AND jsonb_array_length(p_sections) > 0 THEN
        DELETE FROM document_sections WHERE document_id = document_uuid;
        
        FOR section_data IN SELECT * FROM jsonb_array_elements(p_sections) LOOP
            INSERT INTO document_sections (
                document_id, section_type, section_title, content, 
                content_format, sort_order
            ) VALUES (
                document_uuid,
                section_data->>'section_type',
                section_data->>'section_title',
                section_data->>'content',
                COALESCE(section_data->>'content_format', 'markdown'),
                COALESCE((section_data->>'sort_order')::INTEGER, 0)
            );
        END LOOP;
    END IF;
    
    RETURN document_uuid;
END;
$$ LANGUAGE plpgsql;

-- Function to get cross-references for an entity or document
CREATE OR REPLACE FUNCTION get_cross_references(
    p_entity_type TEXT,
    p_entity_id UUID,
    p_project_id UUID DEFAULT NULL,
    p_machine_id TEXT DEFAULT NULL
) RETURNS TABLE (
    reference_id UUID,
    reference_type TEXT,
    target_type TEXT,
    target_id UUID,
    target_display_id TEXT,
    target_title TEXT,
    description TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cr.id,
        cr.reference_type,
        cr.target_type,
        cr.target_id,
        si.display_id,
        CASE 
            WHEN cr.target_type = 'entity' THEN e.entity_name
            WHEN cr.target_type = 'document' THEN d.document_title
        END as target_title,
        cr.description,
        cr.created_at
    FROM cross_references cr
    LEFT JOIN system_identifiers si ON cr.target_id = si.entity_uuid 
        AND si.entity_type = cr.target_type
    LEFT JOIN entities e ON cr.target_type = 'entity' AND cr.target_id = e.id
    LEFT JOIN documents d ON cr.target_type = 'document' AND cr.target_id = d.id
    WHERE cr.source_type = p_entity_type AND cr.source_id = p_entity_id
    AND (p_project_id IS NULL OR cr.project_id = p_project_id)
    AND (p_machine_id IS NULL OR cr.machine_id = p_machine_id)
    ORDER BY cr.reference_type, si.display_id;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================
-- PART 7: TRIGGERS AND CONSTRAINTS
-- ====================================================================

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_system_identifiers_updated_at BEFORE UPDATE ON system_identifiers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_sections_updated_at BEFORE UPDATE ON document_sections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================
-- PART 8: ROW LEVEL SECURITY
-- ====================================================================

-- Enable RLS for new tables
ALTER TABLE system_identifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE approved_document_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE cross_references ENABLE ROW LEVEL SECURITY;

-- Allow all operations policies (can be tightened later with auth)
CREATE POLICY "Allow all operations on system_identifiers" ON system_identifiers FOR ALL USING (true);
CREATE POLICY "Allow all operations on documents" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all operations on document_sections" ON document_sections FOR ALL USING (true);
CREATE POLICY "Allow all operations on approved_document_sections" ON approved_document_sections FOR ALL USING (true);
CREATE POLICY "Allow all operations on cross_references" ON cross_references FOR ALL USING (true);

-- ====================================================================
-- MIGRATION COMPLETE
-- ====================================================================

-- Add comment to track migration completion
COMMENT ON TABLE system_identifiers IS 'Document Management System Migration - Shared ID management for documents and entities';
COMMENT ON TABLE documents IS 'Document Management System Migration - Main documents table with approval system';
COMMENT ON TABLE document_sections IS 'Document Management System Migration - Current document content sections';
COMMENT ON TABLE approved_document_sections IS 'Document Management System Migration - Approved document content versions';
COMMENT ON TABLE cross_references IS 'Document Management System Migration - Cross-references between documents and entities';