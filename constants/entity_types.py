"""
Entity Types Configuration

Central definition of all valid entity types used across the MCP tools.
This ensures consistency with the frontend dropdown and provides a single
source of truth for validation.
"""

VALID_ENTITY_TYPES = [
    'module',
    'feature', 
    'service',
    'api',
    'contract',
    'component',
    'screen',
    'test',
    'validator',
    'orchestrator',
    'database'
]

ENTITY_TYPE_DESCRIPTIONS = {
    'module': 'High-level system modules or packages',
    'feature': 'User-facing features or functionality',
    'service': 'Backend services or microservices',
    'api': 'API endpoints or interfaces',
    'contract': 'Data contracts or interface definitions',
    'component': 'UI components or reusable code components',
    'screen': 'User interface screens or pages',
    'test': 'Test suites, test cases, or testing utilities',
    'validator': 'Validation logic or validation components',
    'orchestrator': 'Workflow orchestrators or coordination logic',
    'database': 'Database schemas, tables, or data storage'
}

def validate_entity_type(entity_type: str) -> tuple[bool, str]:
    """
    Validate if a given entity type is valid.
    
    Args:
        entity_type: The entity type to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if entity_type not in VALID_ENTITY_TYPES:
        return False, f"Invalid entity_type '{entity_type}'. Valid values: {', '.join(VALID_ENTITY_TYPES)}"
    return True, ""

def get_entity_type_description(entity_type: str) -> str:
    """
    Get the description for a given entity type.
    
    Args:
        entity_type: The entity type to describe
        
    Returns:
        Description string, or the entity type itself if not found
    """
    return ENTITY_TYPE_DESCRIPTIONS.get(entity_type, entity_type)