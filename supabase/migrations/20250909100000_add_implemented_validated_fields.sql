-- Add implemented and validated fields to entities and documents
-- Migration to add AI agent-managed status fields alongside user-managed approved field

-- ====================================================================
-- PART 1: ADD FIELDS TO ENTITIES TABLE
-- ====================================================================

-- Add implemented and validated fields to entities table
ALTER TABLE entities ADD COLUMN IF NOT EXISTS implemented BOOLEAN DEFAULT false;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS implemented_at TIMESTAMPTZ;

ALTER TABLE entities ADD COLUMN IF NOT EXISTS validated BOOLEAN DEFAULT false;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS validated_at TIMESTAMPTZ;

-- Create indexes for performance on the new fields
CREATE INDEX IF NOT EXISTS idx_entities_implemented ON entities(implemented);
CREATE INDEX IF NOT EXISTS idx_entities_validated ON entities(validated);

-- ====================================================================
-- PART 2: ADD FIELDS TO DOCUMENTS TABLE
-- ====================================================================

-- Add implemented and validated fields to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS implemented BOOLEAN DEFAULT false;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS implemented_at TIMESTAMPTZ;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS validated BOOLEAN DEFAULT false;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS validated_at TIMESTAMPTZ;

-- Create indexes for performance on the new fields
CREATE INDEX IF NOT EXISTS idx_documents_implemented ON documents(implemented);
CREATE INDEX IF NOT EXISTS idx_documents_validated ON documents(validated);

-- ====================================================================
-- PART 3: UPDATE VIEWS AND FUNCTIONS
-- ====================================================================

-- Update any existing views that select from entities table
-- (Add if any views exist that need updating)

-- Function to set implemented status for entities
CREATE OR REPLACE FUNCTION set_entity_implemented_status(
    p_entity_id UUID,
    p_implemented BOOLEAN
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE entities 
    SET 
        implemented = p_implemented,
        implemented_at = CASE WHEN p_implemented THEN NOW() ELSE NULL END,
        updated_at = NOW()
    WHERE id = p_entity_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to set validated status for entities
CREATE OR REPLACE FUNCTION set_entity_validated_status(
    p_entity_id UUID,
    p_validated BOOLEAN
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE entities 
    SET 
        validated = p_validated,
        validated_at = CASE WHEN p_validated THEN NOW() ELSE NULL END,
        updated_at = NOW()
    WHERE id = p_entity_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to set implemented status for documents
CREATE OR REPLACE FUNCTION set_document_implemented_status(
    p_document_id UUID,
    p_implemented BOOLEAN
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE documents 
    SET 
        implemented = p_implemented,
        implemented_at = CASE WHEN p_implemented THEN NOW() ELSE NULL END,
        updated_at = NOW()
    WHERE id = p_document_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to set validated status for documents
CREATE OR REPLACE FUNCTION set_document_validated_status(
    p_document_id UUID,
    p_validated BOOLEAN
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE documents 
    SET 
        validated = p_validated,
        validated_at = CASE WHEN p_validated THEN NOW() ELSE NULL END,
        updated_at = NOW()
    WHERE id = p_document_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================
-- PART 4: ADD COMMENTS FOR DOCUMENTATION
-- ====================================================================

COMMENT ON COLUMN entities.approved IS 'User-managed field for approving suggested additions from management frontend';
COMMENT ON COLUMN entities.implemented IS 'AI agent-managed field indicating implementation completion';
COMMENT ON COLUMN entities.validated IS 'AI agent-managed field indicating validation completion';

COMMENT ON COLUMN documents.approved IS 'User-managed field for approving suggested additions from management frontend';
COMMENT ON COLUMN documents.implemented IS 'AI agent-managed field indicating implementation completion';
COMMENT ON COLUMN documents.validated IS 'AI agent-managed field indicating validation completion';