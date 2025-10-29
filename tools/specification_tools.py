"""
MCP tools for specifications system integration - DISPLAY_ID BASED VERSION
Uses display_id for hierarchy management. Specification paths are calculated values derived from parent hierarchy.
"""

import os
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add constants to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from constants.entity_types import VALID_ENTITY_TYPES, validate_entity_type

# Validation handled automatically by auto-validation system

# Import SharedIdentifierManager for unique ID validation
try:
    from core.shared.shared_id_manager import SharedIdentifierManager
    SHARED_ID_MANAGER_AVAILABLE = True
except ImportError:
    SHARED_ID_MANAGER_AVAILABLE = False
    SharedIdentifierManager = None

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None
    create_client = None

# Import centralized machine ID management
from core.machine_id import get_machine_id


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class SpecificationError(Exception):
    """Base exception for specification operations."""
    pass


class ValidationError(SpecificationError):
    """Validation failed."""
    pass


class CircularReferenceError(SpecificationError):
    """Circular reference detected in hierarchy."""

    def __init__(self, message: str, cycle_path: List[str] = None):
        super().__init__(message)
        self.cycle_path = cycle_path or []


class DatabaseError(SpecificationError):
    """Database operation failed."""
    pass


class NotFoundError(SpecificationError):
    """Entity not found."""
    pass


# ============================================================================
# CONSTANTS
# ============================================================================

class SpecificationConstants:
    """Configuration constants for specification system."""

    # Hierarchy depth limits
    MAX_HIERARCHY_DEPTH_DISPLAY_ID = 20
    MAX_HIERARCHY_DEPTH_UUID = 100

    # Display ID validation
    DISPLAY_ID_MIN_LENGTH = 2
    DISPLAY_ID_MAX_LENGTH = 50
    DISPLAY_ID_PATTERN = r'^[a-zA-Z0-9_-]+$'

    # Database configuration
    SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

    # Query timeouts and limits
    DATABASE_QUERY_TIMEOUT = 5.0  # seconds
    DEFAULT_SEARCH_LIMIT = 50

    # Verbosity levels
    VERBOSITY_ULTRA_MINIMAL = "ultra_minimal"
    VERBOSITY_MINIMAL = "minimal"
    VERBOSITY_COMPACT = "compact"
    VERBOSITY_FULL = "full"

    # Query scopes
    SCOPE_ALL = "all"
    SCOPE_ROOT = "root"
    SCOPE_CHILDREN = "children"
    SCOPE_SUBTREE = "subtree"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_error_response(error: Exception, **kwargs) -> Dict[str, Any]:
    """Build standardized error response with type discrimination.

    Args:
        error: Exception instance
        **kwargs: Additional fields to include in response

    Returns:
        Standardized error response dictionary
    """
    response = {
        "status": "error",
        "error": str(error),
        "error_type": type(error).__name__
    }

    # Add cycle_path for CircularReferenceError
    if isinstance(error, CircularReferenceError) and error.cycle_path:
        response["cycle_path"] = error.cycle_path

    # Add any additional fields
    response.update(kwargs)

    return response


def build_success_response(message: str = None, **kwargs) -> Dict[str, Any]:
    """Build standardized success response.

    Args:
        message: Optional success message
        **kwargs: Data fields to include in response

    Returns:
        Standardized success response dictionary
    """
    response = {"status": "success"}

    if message:
        response["message"] = message

    response.update(kwargs)

    return response


def handle_supabase_result(result):
    """Handle both old and new Supabase client response formats."""
    try:
        # New client format - result is the response directly
        if hasattr(result, 'data'):
            return result.data, None
        # If it's just the data directly
        return result, None
    except Exception as e:
        return None, str(e)


def format_specifications_by_verbosity(specifications: List[Dict[str, Any]], verbosity: str) -> List:
    """Format specifications based on verbosity level.

    Args:
        specifications: List of specification dictionaries
        verbosity: Output detail level (ultra_minimal, minimal, compact, full)

    Returns:
        Formatted specifications list with display_id prioritized over UUID
    """
    if verbosity == SpecificationConstants.VERBOSITY_ULTRA_MINIMAL:
        return [
            f"{spec.get('display_id', 'NO_ID')}|{spec.get('specification_type', 'NO_TYPE')}|{spec.get('specification_name', 'NO_NAME')}"
            for spec in specifications
        ]
    elif verbosity == SpecificationConstants.VERBOSITY_MINIMAL:
        return [
            {
                "display_id": spec.get("display_id"),
                "specification_name": spec["specification_name"],
                "specification_type": spec["specification_type"],
                "parent_display_id": spec.get("parent_display_id"),
                "validation_status": spec.get("validation_status", "unknown")
            }
            for spec in specifications
        ]
    elif verbosity == SpecificationConstants.VERBOSITY_COMPACT:
        result = []
        for spec in specifications:
            entry = {
                "display_id": spec.get("display_id"),
                "specification_name": spec["specification_name"],
                "specification_type": spec["specification_type"],
                "parent_display_id": spec.get("parent_display_id"),
                "description": spec.get("description", ""),
                "approved": spec.get("approved", False),
                "validation_status": spec.get("validation_status", "unknown")
            }
            # Add validation hint if present
            if "validation_hint" in spec:
                entry["validation_hint"] = spec["validation_hint"]
            result.append(entry)
        return result
    else:  # full
        return specifications


class SpecificationQueryBuilder:
    """Fluent builder for Supabase specification queries."""

    def __init__(self, client, project_id: str, machine_id: str):
        """Initialize query builder with client and scope."""
        self.client = client
        self.project_id = project_id
        self.machine_id = machine_id
        self.query = None

    def base_query(self, select_fields: str = '*'):
        """Initialize base query with project/machine scope."""
        self.query = (self.client.table('specifications')
            .select(select_fields)
            .eq('project_id', self.project_id)
            .eq('machine_id', self.machine_id))
        return self

    def filter_by_parent(self, parent_id: str):
        """Filter by parent_id."""
        if self.query and parent_id:
            self.query = self.query.eq('parent_id', parent_id)
        return self

    def filter_by_approval(self, include_unapproved: bool = False, approved: bool = None):
        """Apply approval filter logic."""
        if self.query:
            if not include_unapproved and approved is None:
                self.query = self.query.eq('approved', True)
            elif approved is not None:
                self.query = self.query.eq('approved', approved)
        return self

    def filter_by_entity_id(self, entity_id: str):
        """Filter by entity UUID."""
        if self.query and entity_id:
            self.query = self.query.eq('id', entity_id)
        return self

    def filter_by_display_id(self, display_id: str):
        """Filter by display_id."""
        if self.query and display_id:
            self.query = self.query.eq('display_id', display_id)
        return self

    def filter_by_ids(self, entity_ids: List[str]):
        """Filter by multiple IDs using IN clause. Supports mixed UUID/display_id lists."""
        if self.query and entity_ids:
            # Separate UUIDs from display_ids
            uuids = [id for id in entity_ids if is_uuid_format(id)]
            display_ids = [id for id in entity_ids if not is_uuid_format(id)]

            # Build OR condition for both types
            if uuids and display_ids:
                # Mixed list - need OR condition
                self.query = self.query.or_(f"id.in.({','.join(uuids)}),display_id.in.({','.join(display_ids)})")
            elif uuids:
                # Only UUIDs
                self.query = self.query.in_('id', uuids)
            elif display_ids:
                # Only display_ids
                self.query = self.query.in_('display_id', display_ids)
        return self

    def execute(self):
        """Execute the built query."""
        return self.query.execute() if self.query else None


def build_specification_record(
    specification_id: str,
    project_id: str,
    machine_id: str,
    specification_name: str,
    specification_type: str,
    display_id: str,
    parent_display_id: str,
    description: str
) -> Dict[str, Any]:
    """Build specification record dictionary for database insertion."""
    return {
        'id': specification_id,
        'project_id': project_id,
        'machine_id': machine_id,
        'specification_name': specification_name,
        'specification_type': specification_type,
        'display_id': display_id,
        'parent_display_id': parent_display_id,
        'description': description or '',
        'approved': False,
        'implemented': False,
        'validated': False,
        'level_depth': 0,
        'sort_order': 0,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }


def add_requirements_and_constraints(
    client,
    specification_id: str,
    requirements: List[str] = None,
    constraints: List[str] = None
) -> tuple[int, int]:
    """Add requirements and constraints to specification.

    Returns:
        (requirements_added, constraints_added)
    """
    requirements_added = 0
    constraints_added = 0

    if requirements:
        for requirement in requirements:
            req_record = {
                'specification_id': specification_id,
                'requirement_text': requirement,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            client.table('specification_requirements').insert(req_record).execute()
            requirements_added += 1

    if constraints:
        for constraint in constraints:
            const_record = {
                'specification_id': specification_id,
                'constraint_text': constraint,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            client.table('specification_constraints').insert(const_record).execute()
            constraints_added += 1

    return requirements_added, constraints_added


def load_local_specifications_fallback(
    project_manager,
    include_unapproved: bool = False,
    approved: bool = None
) -> tuple[List[Dict], str]:
    """Load specifications from local file with approval filters.

    Returns:
        (specifications_list, storage_type)
    """
    try:
        specifications_file = project_manager.get_data_file('specifications')
        if not specifications_file.exists():
            # Create empty file
            local_data = {
                "specification": [],
                "metadata": {"created_at": datetime.now(timezone.utc).isoformat()}
            }
            with open(specifications_file, 'w') as f:
                json.dump(local_data, f, indent=2)
            return [], "local_created"

        with open(specifications_file, 'r') as f:
            local_data = json.load(f)

        local_specifications = local_data.get('specification', local_data.get('specifications', []))

        # Apply approval filters
        filtered = []
        for spec in local_specifications:
            if not include_unapproved and not spec.get('approved', False):
                continue
            if approved is not None and spec.get('approved', False) != approved:
                continue
            filtered.append(spec)

        return filtered, "local_fallback"
    except Exception as e:
        raise Exception(f"Local fallback failed: {e}")


def is_uuid_format(identifier: str) -> bool:
    """Check if string is UUID format (8-4-4-4-12 hex pattern)."""
    if not identifier:
        return False
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, identifier, re.IGNORECASE))

def resolve_specification_id(identifier: str, project_id: str, machine_id: str) -> tuple[str, str]:
    """Resolve identifier to UUID and display_id.

    Args:
        identifier: Either UUID or display_id
        project_id: Project scope
        machine_id: Machine scope

    Returns:
        (uuid, error) - UUID if found, error message if not
    """
    if not identifier:
        return None, "Identifier is required"

    try:
        client, error = get_supabase_client()
        if error:
            return None, f"Database connection error: {error}"

        # If it's a UUID, query by id
        if is_uuid_format(identifier):
            result = client.table('specifications').select('id').eq('id', identifier).eq('project_id', project_id).eq('machine_id', machine_id).execute()
        else:
            # Otherwise treat as display_id
            result = client.table('specifications').select('id').eq('display_id', identifier).eq('project_id', project_id).eq('machine_id', machine_id).execute()

        if not result.data or len(result.data) == 0:
            return None, f"Specification '{identifier}' not found"

        return result.data[0]['id'], None

    except Exception as e:
        return None, f"Lookup error: {str(e)}"

def validate_display_id_format(display_id: str) -> tuple[bool, str]:
    """Validate display ID format requirements."""
    if not display_id or not display_id.strip():
        return False, "Display ID is required and cannot be empty"

    display_id = display_id.strip()

    # Check format
    if not re.match(SpecificationConstants.DISPLAY_ID_PATTERN, display_id):
        return False, "Display ID can only contain letters, numbers, underscores, and hyphens"

    # Check length
    if len(display_id) < SpecificationConstants.DISPLAY_ID_MIN_LENGTH:
        return False, f"Display ID must be at least {SpecificationConstants.DISPLAY_ID_MIN_LENGTH} characters"

    if len(display_id) > SpecificationConstants.DISPLAY_ID_MAX_LENGTH:
        return False, f"Display ID cannot exceed {SpecificationConstants.DISPLAY_ID_MAX_LENGTH} characters"

    return True, ""

def validate_display_id_uniqueness(display_id: str, project_id: str, machine_id: str, exclude_entity_id: str = None) -> tuple[bool, str]:
    """Validate display ID uniqueness within project/machine scope."""
    try:
        client, error = get_supabase_client()
        if error:
            return False, f"Database connection error: {error}"
        
        # Query for existing specifications with this display_id in the same project/machine
        query = client.table('specifications').select('id').eq('project_id', project_id).eq('machine_id', machine_id).eq('display_id', display_id)
        
        # Exclude current entity if updating
        if exclude_entity_id:
            query = query.neq('id', exclude_entity_id)
        
        result = query.execute()

        # Handle both old and new Supabase client response formats
        data, error = handle_supabase_result(result)
        if error:
            return False, f"Database query error: {error}"

        if data and len(data) > 0:
            return False, f"Display ID '{display_id}' already exists in this project/machine combination"
        
        return True, ""
        
    except Exception as e:
        return False, f"Uniqueness validation error: {str(e)}"

def validate_parent_display_id_exists(parent_display_id: str, project_id: str, machine_id: str) -> tuple[bool, str]:
    """Validate that parent display ID exists in the same project/machine."""
    if not parent_display_id or not parent_display_id.strip():
        return True, ""  # No parent is valid (root entity)
    
    try:
        client, error = get_supabase_client()
        if error:
            return False, f"Database connection error: {error}"
        
        # Find parent specification by display_id
        result = client.table('specifications').select('id, specification_name').eq('project_id', project_id).eq('machine_id', machine_id).eq('display_id', parent_display_id).execute()
        
        if not result.data or len(result.data) == 0:
            return False, f"Parent display ID '{parent_display_id}' not found in this project/machine"
        
        return True, ""
        
    except Exception as e:
        return False, f"Parent validation error: {str(e)}"

def check_display_id_circular_reference(display_id: str, parent_display_id: str, project_id: str, machine_id: str) -> tuple[bool, str, list]:
    """Check for circular references in display ID hierarchy.

    Wrapper for detect_circular_hierarchy using display_id lookup.
    """
    return detect_circular_hierarchy(display_id, parent_display_id, project_id, machine_id, 'display_id')


def detect_circular_hierarchy(
    entity_id: str,
    parent_id: str,
    project_id: str,
    machine_id: str,
    lookup_field: str = 'id'
) -> tuple[bool, str, list]:
    """Generic circular reference detection for any ID type.

    Args:
        entity_id: Entity being checked (UUID or display_id)
        parent_id: Parent entity (UUID or display_id)
        project_id: Project scope
        machine_id: Machine scope
        lookup_field: Field to use for lookups ('id' for UUID, 'display_id' for display IDs)

    Returns:
        (is_circular, error_message, cycle_path)
    """
    if not parent_id:
        return False, "", []

    if entity_id == parent_id:
        return True, "Entity cannot be its own parent", [entity_id, parent_id]

    try:
        client, error = get_supabase_client()
        if error:
            return True, f"Database connection failed: {error}", []

        # Select appropriate constants based on lookup field
        max_depth = (SpecificationConstants.MAX_HIERARCHY_DEPTH_DISPLAY_ID
                    if lookup_field == 'display_id'
                    else SpecificationConstants.MAX_HIERARCHY_DEPTH_UUID)

        # Build parent chain upward
        visited = set()
        chain = []
        current = parent_id

        # Determine parent field name based on lookup field
        parent_field = f'parent_{lookup_field}' if lookup_field == 'display_id' else 'parent_id'

        while current and current not in visited:
            # Prevent infinite loops
            if len(chain) >= max_depth:
                return True, f"Hierarchy depth limit exceeded (>{max_depth})", chain

            visited.add(current)
            chain.append(current)

            # Check if we've encountered the entity_id (circular reference)
            if current == entity_id:
                chain.append(entity_id)
                return True, f"Circular reference detected: '{entity_id}' would become its own ancestor", chain

            # Get parent using appropriate field
            result = (client.table('specifications')
                .select(parent_field)
                .eq(lookup_field, current)
                .eq('project_id', project_id)
                .eq('machine_id', machine_id)
                .execute())

            if not hasattr(result, 'data') or not result.data:
                break

            current = result.data[0].get(parent_field)

        return False, "", []

    except Exception as e:
        return True, f"Error during circular reference detection: {str(e)}", []


def get_supabase_client():
    """Get Supabase client with credentials for specification sync."""
    try:
        if not SUPABASE_AVAILABLE:
            return None, "Supabase library not available"

        client = create_client(SpecificationConstants.SUPABASE_URL, SpecificationConstants.SUPABASE_KEY)
        return client, None
    except Exception as e:
        return None, str(e)

def get_or_create_project_id(project_manager):
    """Get or create project ID using file-based project identification.

    NEW: Uses .claude-tasks/data/project_id file for cross-machine identification.
    Same repo on different machines = same project_id (from file).

    Args:
        project_manager: ProjectManager instance (not just path)

    Returns:
        Tuple of (project_id: str, error: str|None)
    """
    client, error = get_supabase_client()
    if error:
        return None, f"Supabase client error: {error}"

    try:
        # 1. Get project_id from file (or generate new one)
        project_id = project_manager.get_or_generate_project_id()

        # 2. Get machine_id for this computer
        try:
            machine_id = get_machine_id()
        except Exception as e:
            return None, f"Machine ID error: {e}"

        # 3. Check if this machine already registered for this project
        result = client.table('projects').select('*')\
            .eq('id', project_id)\
            .eq('machine_id', machine_id)\
            .execute()

        if result.data and len(result.data) > 0:
            # Machine already registered, check if path changed
            existing = result.data[0]
            current_path = str(project_manager.project_path)

            if existing['path'] != current_path:
                # Path changed on this machine, update it
                client.table('projects').update({
                    'path': current_path,
                    'updated_at': 'NOW()'
                }).eq('id', project_id).eq('machine_id', machine_id).execute()

            return project_id, None

        # 4. This machine not yet registered for this project, create entry
        project_name = os.path.basename(str(project_manager.project_path))
        new_record = {
            'id': project_id,  # From project_id file
            'machine_id': machine_id,
            'path': str(project_manager.project_path),
            'name': project_name
        }

        result = client.table('projects').insert(new_record).execute()

        if result.data and len(result.data) > 0:
            return project_id, None
        else:
            return None, "Failed to create project record"

    except Exception as e:
        return None, f"Project error: {str(e)}"

def validate_parent_exists(parent_id, project_id, machine_id):
    """Validate that parent specification exists in the database."""
    if not parent_id:
        return True, ""  # No parent is valid

    try:
        client, error = get_supabase_client()
        if error:
            return False, f"Database connection error: {error}"

        result = client.table('specifications').select('id, specification_name').eq('id', parent_id).eq('project_id', project_id).eq('machine_id', machine_id).execute()

        if hasattr(result, 'data') and result.data:
            return True, ""
        else:
            return False, f"Parent specification {parent_id} not found in project"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def filter_specifications_by_depth(specifications, depth, root_specification_id=None):
    """Filter specifications by hierarchical depth from roots or a specific starting specification."""

    if depth < 0:  # No depth limit
        return specifications

    # Build parent-child mapping
    children_map = {}
    specification_map = {s['id']: s for s in specifications}

    for specification in specifications:
        parent_id = specification.get('parent_id')
        if parent_id:
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(specification['id'])

    # Find starting specifications
    if root_specification_id:
        # Start from specific specification
        if root_specification_id not in specification_map:
            return []
        starting_specifications = [root_specification_id]
    else:
        # Start from true roots (specifications with no parent)
        starting_specifications = [s['id'] for s in specifications if not s.get('parent_id')]

    # Collect specifications at each depth level
    result_ids = set()
    current_level = starting_specifications

    for current_depth in range(depth + 1):
        if not current_level:
            break

        # Add current level specifications to result
        result_ids.update(current_level)

        # Prepare next level (children of current level)
        if current_depth < depth:
            next_level = []
            for specification_id in current_level:
                if specification_id in children_map:
                    next_level.extend(children_map[specification_id])
            current_level = next_level
        else:
            break

    # Return filtered specifications in original order
    return [s for s in specifications if s['id'] in result_ids]


def detect_circular_reference(specification_id, new_parent_id, project_id, machine_id):
    """Detect circular references in parent-child hierarchy using UUID.

    Wrapper for detect_circular_hierarchy using UUID lookup.
    Returns (is_circular, error_message, path_to_cycle).
    """
    is_circular, error, path = detect_circular_hierarchy(specification_id, new_parent_id, project_id, machine_id, 'id')
    # Convert empty string to None for backward compatibility
    return is_circular, error if error else None, path


# ============================================================================
# VALIDATION STATUS HELPERS
# ============================================================================

def calculate_validation_status(current_spec: Dict, validated_spec: Dict) -> str:
    """Calculate validation status for a specification.

    Compares current (AI suggested) vs validated (human approved) versions.

    Args:
        current_spec: Current specification record
        validated_spec: Validated specification record (or None)

    Returns:
        "new" - No validated record exists (never approved)
        "validated" - Validated record exists and matches current
        "modified" - Validated record exists but current has changes
    """
    if not validated_spec:
        return "new"

    # Compare key fields that AI agents can modify
    key_fields = [
        'specification_name',
        'description',
        'specification_type',
        'display_id',
        'parent_display_id'
    ]

    for field in key_fields:
        current_val = current_spec.get(field)
        validated_val = validated_spec.get(field)
        if current_val != validated_val:
            return "modified"

    return "validated"


def fetch_validated_specifications(
    client,
    project_id: str,
    machine_id: str,
    specification_ids: List[str] = None
) -> Dict[str, Dict]:
    """Fetch validated specifications and build lookup map.

    Args:
        client: Supabase client
        project_id: Project scope
        machine_id: Machine scope
        specification_ids: Optional list of specific IDs to fetch

    Returns:
        Dictionary mapping specification UUID -> validated record
    """
    try:
        query = (client.table('specifications_validated')
            .select('*')
            .eq('project_id', project_id)
            .eq('machine_id', machine_id))

        if specification_ids:
            query = query.in_('id', specification_ids)

        result = query.execute()

        if hasattr(result, 'data') and result.data:
            return {v['id']: v for v in result.data}

        return {}
    except Exception as e:
        # Silently fail - validation status is optional enhancement
        print(f"Warning: Could not fetch validated specifications: {e}")
        return {}


def enhance_with_validation_status(
    specifications: List[Dict],
    validated_map: Dict[str, Dict],
    verbosity: str = "minimal"
) -> List[Dict]:
    """Add validation status to specification records.

    Modifies specifications in-place to add validation metadata.

    Args:
        specifications: List of current specifications
        validated_map: Map of UUID -> validated specification
        verbosity: Output detail level

    Returns:
        Enhanced specifications list
    """
    for spec in specifications:
        spec_id = spec.get('id')
        validated_spec = validated_map.get(spec_id)

        # Calculate status
        status = calculate_validation_status(spec, validated_spec)
        spec['validation_status'] = status

        # Add hint for modified specs (compact mode and above)
        if verbosity in ['compact', 'full'] and status == 'modified':
            spec['validation_hint'] = 'Has unvalidated changes'

        # Add validated snapshot for full mode
        if verbosity == 'full' and validated_spec:
            spec['validated_snapshot'] = {
                'specification_name': validated_spec.get('specification_name'),
                'description': validated_spec.get('description'),
                'display_id': validated_spec.get('display_id'),
                'parent_display_id': validated_spec.get('parent_display_id'),
                'validated_at': validated_spec.get('validated_at'),
                'validated_by': validated_spec.get('validated_by')
            }

    return specifications


def register_specification_tools(mcp, project_manager, tool_filter=None):
    """Register parent_id-based specifications system tools with MCP infrastructure."""

    @mcp.tool()
    async def specification_create(
        specification_name: str,
        specification_type: str,
        display_id: str,
        parent_display_id: str = None,
        description: str = "",
        requirements: List[str] = None,
        constraints: List[str] = None
    ) -> Dict[str, Any]:
        """SUGGEST a new specification for user validation.

        ⚠️ IMPORTANT: All specifications created by AI agents are SUGGESTIONS that
        require human validation before implementation. The specification will be
        marked as unapproved and validation_status="new" until validated by a user
        in the frontend.

        Args:
            specification_name: Human-readable name for the specification
            specification_type: Type of specification. Valid values: module, feature, service, api, contract, component, screen, test, validator, orchestrator, database. Use 'module' for high-level packages, 'feature' for user functionality, 'service' for backend services, 'api' for endpoints, 'contract' for data contracts, 'component' for reusable code/UI, 'screen' for UI pages, 'test' for testing, 'validator' for validation logic, 'orchestrator' for workflows, 'database' for data storage.
            display_id: REQUIRED unique display ID for the specification (e.g., 'api_gateway', 'user_auth')
            parent_display_id: Optional parent specification display ID for hierarchy. Leave empty for root-level specifications.
            description: Optional description of the specification
            requirements: List of requirements for the specification
            constraints: List of constraints for the specification

        Returns:
            Dict with status and suggested specification information
        """
        if not project_manager.is_initialized():
            return build_error_response(ValidationError("No project directory set"))

        # Validate specification_type against allowed values
        is_valid, error_message = validate_entity_type(specification_type)
        if not is_valid:
            return build_error_response(ValidationError(error_message))

        try:
            # Get or create project ID for database operations
            project_id, project_error = get_or_create_project_id(project_manager)
            if project_error:
                return build_error_response(DatabaseError(f"Project setup failed: {project_error}"))

            machine_id = get_machine_id()

            # Validate display_id format and requirements
            format_valid, format_error = validate_display_id_format(display_id)
            if not format_valid:
                return build_error_response(ValidationError(f"Display ID validation failed: {format_error}"))

            # Validate display_id uniqueness within project/machine scope
            unique_valid, unique_error = validate_display_id_uniqueness(display_id, project_id, machine_id)
            if not unique_valid:
                return build_error_response(ValidationError(f"Display ID validation failed: {unique_error}"))

            # Validate parent display ID exists and resolve to UUID if provided
            parent_uuid = None
            if parent_display_id:
                parent_valid, parent_error = validate_parent_display_id_exists(parent_display_id, project_id, machine_id)
                if not parent_valid:
                    return build_error_response(ValidationError(f"Parent validation failed: {parent_error}"))

                # Check for circular references
                circular, circular_error, cycle_path = check_display_id_circular_reference(display_id, parent_display_id, project_id, machine_id)
                if circular:
                    return build_error_response(
                        CircularReferenceError(f"Circular reference prevented: {circular_error}", cycle_path)
                    )

                # Look up parent UUID for database FK relationship
                parent_uuid, lookup_error = resolve_specification_id(parent_display_id, project_id, machine_id)
                if lookup_error:
                    return build_error_response(DatabaseError(f"Parent UUID lookup failed: {lookup_error}"))

            # Generate UUID for database storage (internal)
            actual_specification_id = str(uuid.uuid4())

            # Connect to Supabase for specification creation
            client, client_error = get_supabase_client()
            if client_error:
                return build_error_response(DatabaseError(f"Database connection failed: {client_error}"))

            try:
                # Build specification record
                specification_record = build_specification_record(
                    actual_specification_id, project_id, machine_id, specification_name,
                    specification_type, display_id, parent_display_id, description
                )

                # Set parent_id UUID for database foreign key integrity
                specification_record['parent_id'] = parent_uuid

                # Insert specification into database
                result = client.table('specifications').insert(specification_record).execute()

                # Handle response
                data, error = handle_supabase_result(result)
                if error:
                    return build_error_response(DatabaseError(f"Database error: {error}"))

                if not data or len(data) == 0:
                    return build_error_response(DatabaseError("Specification creation failed - no data returned"))

                created_specification = data[0]

                # Add requirements and constraints
                requirements_added, constraints_added = add_requirements_and_constraints(
                    client, actual_specification_id, requirements, constraints
                )

                # Return success with display ID-based information
                return {
                    "status": "success",
                    "specification_id": actual_specification_id,
                    "specification_name": specification_name,
                    "display_id": display_id,
                    "parent_display_id": parent_display_id,
                    "specification_type": specification_type,
                    "machine_id": machine_id,
                    "requirements_added": requirements_added,
                    "constraints_added": constraints_added,
                    "message": f"Specification '{specification_name}' suggested (pending user validation)",
                    "reminder": "⚠️ This is a suggestion. A user must validate in the frontend before implementation.",
                    "validation_status": "new",
                    "database_synced": True
                }
                        
            except Exception as db_error:
                return build_error_response(DatabaseError(f"Database operation failed: {str(db_error)}"))

        except Exception as e:
            return build_error_response(SpecificationError(str(e)))

    @mcp.tool()
    async def specification_update(
        specification_id: str,
        specification_name: str = None,
        display_id: str = None,
        description: str = None,
        requirements: List[str] = None,
        constraints: List[str] = None,
        parent_display_id: str = None
    ) -> Dict[str, Any]:
        """SUGGEST updates to an existing specification for user validation.

        ⚠️ IMPORTANT: All updates made by AI agents are SUGGESTIONS that require
        human validation. The specification will be marked validation_status="modified"
        if it was previously validated, indicating it has unvalidated changes.

        Accepts UUID or display_id for specification_id parameter.
        """
        if not project_manager.is_initialized():
            return build_error_response(ValidationError("No project directory set"))

        try:
            # Get project context
            project_id, project_error = get_or_create_project_id(project_manager)
            if project_error:
                return build_error_response(DatabaseError(f"Project setup failed: {project_error}"))

            machine_id = get_machine_id()

            # Resolve specification_id to UUID (accepts both UUID and display_id)
            resolved_uuid, resolve_error = resolve_specification_id(specification_id, project_id, machine_id)
            if resolve_error:
                return build_error_response(NotFoundError(f"Specification '{specification_id}' not found: {resolve_error}"))

            # Look up parent UUID if parent_display_id is being changed
            parent_uuid = None
            if parent_display_id is not None:  # Allow empty string to clear parent
                if parent_display_id and parent_display_id != "":
                    valid_parent, parent_error = validate_parent_display_id_exists(parent_display_id, project_id, machine_id)
                    if not valid_parent:
                        return build_error_response(ValidationError(f"Parent validation failed: {parent_error}"))

                    # Check for circular references
                    is_circular, circular_error, cycle_path = check_display_id_circular_reference(display_id or "", parent_display_id, project_id, machine_id)
                    if is_circular:
                        return build_error_response(
                            CircularReferenceError(f"Circular reference prevented: {circular_error}", cycle_path)
                        )

                    # Resolve parent display_id to UUID
                    parent_uuid, lookup_error = resolve_specification_id(parent_display_id, project_id, machine_id)
                    if lookup_error:
                        return build_error_response(DatabaseError(f"Parent UUID lookup failed: {lookup_error}"))
                # else: parent_display_id is empty string, will set parent_uuid to None below

            client, error = get_supabase_client()
            if error:
                return build_error_response(DatabaseError(f"Database connection failed: {error}"))

            # Get current specification for path calculation (use resolved UUID)
            current_result = client.table('specifications').select('*').eq('id', resolved_uuid).eq('project_id', project_id).eq('machine_id', machine_id).execute()

            if not hasattr(current_result, 'data') or not current_result.data:
                return build_error_response(NotFoundError(f"Specification {specification_id} not found"))

            current_specification = current_result.data[0]

            # Build update data - only include fields that are provided
            update_data = {
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            if specification_name is not None:
                update_data['specification_name'] = specification_name
            if display_id is not None:
                update_data['display_id'] = display_id
            if description is not None:
                update_data['description'] = description
            if requirements is not None:
                update_data['requirements'] = requirements
            if constraints is not None:
                update_data['constraints'] = constraints
            if parent_display_id is not None:
                update_data['parent_display_id'] = parent_display_id if parent_display_id != "" else None
                # Also update parent_id UUID for database FK integrity
                update_data['parent_id'] = parent_uuid

            # Update in database (use resolved UUID)
            result = client.table('specifications').update(update_data).eq('id', resolved_uuid).eq('project_id', project_id).eq('machine_id', machine_id).execute()

            if hasattr(result, 'data') and result.data:
                return {
                    "status": "success",
                    "specification_id": specification_id,
                    "updated_fields": list(update_data.keys()),
                    "message": f"Specification updates suggested (pending user validation)",
                    "reminder": "⚠️ Changes are suggestions. User must re-validate in the frontend."
                }
            else:
                return build_error_response(DatabaseError("Update failed - no rows affected"))

        except Exception as e:
            return build_error_response(SpecificationError(str(e)))

    @mcp.tool()
    async def specification_delete(
        specification_id: str,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """SUGGEST deletion of a specification for user validation.

        ⚠️ IMPORTANT: Deletion requests from AI agents are SUGGESTIONS. A user
        must approve the deletion in the frontend. Consider whether this specification
        has been validated and is actively used before suggesting deletion.

        Accepts UUID or display_id for specification_id parameter.
        """
        if not project_manager.is_initialized():
            return build_error_response(ValidationError("No project directory set"))

        try:
            # Get project context
            project_id, project_error = get_or_create_project_id(project_manager)
            if project_error:
                return build_error_response(DatabaseError(f"Project setup failed: {project_error}"))

            machine_id = get_machine_id()

            # Resolve specification_id to UUID (accepts both UUID and display_id)
            resolved_uuid, resolve_error = resolve_specification_id(specification_id, project_id, machine_id)
            if resolve_error:
                return build_error_response(NotFoundError(f"Specification '{specification_id}' not found: {resolve_error}"))

            client, error = get_supabase_client()
            if error:
                return build_error_response(DatabaseError(f"Database connection failed: {error}"))

            if cascade:
                # Get all descendants first (use resolved UUID)
                all_specifications_result = client.table('specifications').select('id, parent_id, specification_name').eq('project_id', project_id).eq('machine_id', machine_id).execute()

                if hasattr(all_specifications_result, 'data') and all_specifications_result.data:
                    # Build hierarchy to find all descendants
                    specification_map = {s['id']: s for s in all_specifications_result.data}
                    to_delete = [resolved_uuid]

                    # Recursively find children
                    def find_children(parent_id):
                        children = [s['id'] for s in all_specifications_result.data if s.get('parent_id') == parent_id]
                        for child_id in children:
                            to_delete.append(child_id)
                            find_children(child_id)  # Recurse

                    find_children(resolved_uuid)

                    # Delete all specifications in the hierarchy
                    delete_result = client.table('specifications').delete().in_('id', to_delete).eq('project_id', project_id).eq('machine_id', machine_id).execute()

                    return {
                        "status": "success",
                        "deleted_specification_ids": to_delete,
                        "deleted_count": len(to_delete),
                        "cascade": True,
                        "message": f"Deletion of specification and {len(to_delete)-1} descendants suggested",
                        "reminder": "⚠️ Deletion is a suggestion. User must approve in the frontend."
                    }
                else:
                    return build_error_response(DatabaseError("Could not fetch specifications for cascade delete"))
            else:
                # Check if specification has children (use resolved UUID)
                children_result = client.table('specifications').select('id').eq('parent_id', resolved_uuid).eq('project_id', project_id).eq('machine_id', machine_id).execute()

                if hasattr(children_result, 'data') and children_result.data:
                    return {
                        "status": "error",
                        "error": f"Cannot delete specification with {len(children_result.data)} children. Use cascade=true to delete children as well."
                    }

                # Delete single specification (use resolved UUID)
                result = client.table('specifications').delete().eq('id', resolved_uuid).eq('project_id', project_id).eq('machine_id', machine_id).execute()

                return {
                    "status": "success",
                    "deleted_specification_id": specification_id,
                    "cascade": False,
                    "message": "Specification deletion suggested (pending user approval)",
                    "reminder": "⚠️ Deletion is a suggestion. User must approve in the frontend."
                }

        except Exception as e:
            return build_error_response(SpecificationError(str(e)))

    # ============================================================================
    # QUERY TOOLS (Consolidated from 4 legacy tools)
    # ============================================================================

    @mcp.tool()
    async def specification_query(
        scope: str = "all",
        parent_id: str = None,
        depth: int = -1,
        entity_type: str = None,
        include_unapproved: bool = False,
        approved: bool = None,
        verbosity: str = "minimal"
    ) -> Dict[str, Any]:
        """Query specifications with hierarchical exploration and smart filtering.

        Args:
            scope: Query mode - "all" (project-wide), "root" (no parent), "children" (direct children), "subtree" (full branch)
            parent_id: Parent display_id (or UUID) for "children" or "subtree" scope
            depth: Hierarchy depth (-1=unlimited, 0=current level, N=N+1 levels)
            entity_type: Filter by type (api, module, component, etc.)
            include_unapproved: Include unapproved entities (default: False)
            approved: Explicit approval filter (True=approved only, False=unapproved only, None=both)
            verbosity: Output detail level ("ultra_minimal", "minimal", "compact", "full")

        Scope Modes:
            - "all": All entities in project (respects depth from roots)
            - "root": Only root entities (no parent)
            - "children": Direct children of parent_id (single level)
            - "subtree": Full subtree from parent_id (respects depth)

        Verbosity Levels:
            - ultra_minimal: "path|type|name" (94.9% token reduction)
            - minimal: id+core fields (60% reduction)
            - compact: core+status, no arrays (40% reduction)
            - full: complete entity with all fields

        Examples:
            # Initial overview (ultra-efficient)
            specification_query(scope="root", verbosity="ultra_minimal")

            # Explore authentication branch (2 levels deep)
            specification_query(scope="subtree", parent_id="user_management", depth=2, verbosity="minimal")

            # Get direct children with full details
            specification_query(scope="children", parent_id="api_gateway", verbosity="full")
        """
        if not project_manager.is_initialized():
            return build_error_response(ValidationError("No project directory set"))

        # Validate scope parameter
        valid_scopes = [
            SpecificationConstants.SCOPE_ALL,
            SpecificationConstants.SCOPE_ROOT,
            SpecificationConstants.SCOPE_CHILDREN,
            SpecificationConstants.SCOPE_SUBTREE
        ]
        if scope not in valid_scopes:
            return build_error_response(
                ValidationError(f"Invalid scope '{scope}'. Must be one of: {', '.join(valid_scopes)}")
            )

        # Validate scope-specific requirements
        if scope in [SpecificationConstants.SCOPE_CHILDREN, SpecificationConstants.SCOPE_SUBTREE] and not parent_id:
            return build_error_response(
                ValidationError(f"scope='{scope}' requires parent_id parameter")
            )

        if scope in [SpecificationConstants.SCOPE_ALL, SpecificationConstants.SCOPE_ROOT] and parent_id:
            return build_error_response(
                ValidationError(f"scope='{scope}' does not accept parent_id parameter")
            )

        try:
            # Get project context
            project_id, project_error = get_or_create_project_id(project_manager)
            if project_error:
                return build_error_response(DatabaseError(f"Project setup failed: {project_error}"))

            machine_id = get_machine_id()

            # Resolve parent_id to UUID if provided (accepts display_id or UUID)
            resolved_parent_uuid = None
            if parent_id and scope in [SpecificationConstants.SCOPE_CHILDREN, SpecificationConstants.SCOPE_SUBTREE]:
                resolved_parent_uuid, resolve_error = resolve_specification_id(parent_id, project_id, machine_id)
                if resolve_error:
                    return build_error_response(NotFoundError(f"Parent specification '{parent_id}' not found: {resolve_error}"))

            # Try Supabase with timeout protection, add local fallback
            specifications = []
            storage_type = "unknown"

            try:
                client, error = get_supabase_client()
                if error:
                    raise Exception(f"Database connection failed: {error}")

                # Build query using QueryBuilder
                builder = SpecificationQueryBuilder(client, project_id, machine_id)
                builder.base_query()

                # Apply scope-specific filters (use resolved UUID)
                if scope == SpecificationConstants.SCOPE_CHILDREN:
                    builder.filter_by_parent(resolved_parent_uuid)

                # Apply approval filter
                builder.filter_by_approval(include_unapproved, approved)

                # Execute with timeout protection
                import asyncio
                def execute_query():
                    return builder.execute()

                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, execute_query),
                    timeout=SpecificationConstants.DATABASE_QUERY_TIMEOUT
                )

                specifications = result.data or []
                storage_type = "supabase_primary"

            except (asyncio.TimeoutError, Exception) as e:
                print(f"Supabase unavailable ({str(e)}), using local fallback")

                # Use helper for local fallback
                try:
                    specifications, storage_type = load_local_specifications_fallback(
                        project_manager, include_unapproved, approved
                    )
                    print(f"✅ Local fallback: Found {len(specifications)} specifications")
                except Exception as local_e:
                    print(f"❌ Local fallback failed: {local_e}")
                    return build_error_response(DatabaseError(f"Both remote and local storage failed: {local_e}"))

            # Apply entity_type filter
            if entity_type:
                specifications = [s for s in specifications if s.get('specification_type') == entity_type]

            # Apply scope-based filtering
            if scope == SpecificationConstants.SCOPE_ROOT:
                # Only entities with no parent
                specifications = [s for s in specifications if not s.get('parent_id')]

            elif scope == SpecificationConstants.SCOPE_SUBTREE:
                # Get subtree from parent_id (use resolved UUID)
                specifications = filter_specifications_by_depth(specifications, depth, resolved_parent_uuid)

            elif scope == SpecificationConstants.SCOPE_ALL:
                # Filter by depth from roots
                if depth >= 0:
                    specifications = filter_specifications_by_depth(specifications, depth, None)

            # scope == "children" already filtered by query above

            # Enhance with validation status (fetch validated versions)
            if specifications and storage_type == "supabase_primary":
                try:
                    spec_ids = [s['id'] for s in specifications]
                    validated_map = fetch_validated_specifications(
                        client, project_id, machine_id, spec_ids
                    )
                    specifications = enhance_with_validation_status(
                        specifications, validated_map, verbosity
                    )
                except Exception as e:
                    # Silently continue without validation status on error
                    print(f"Warning: Could not enhance with validation status: {e}")

            # Format based on verbosity
            formatted_specifications = format_specifications_by_verbosity(specifications, verbosity)

            return {
                "status": "success",
                "specifications": formatted_specifications,
                "total_count": len(formatted_specifications),
                "scope": scope,
                "depth_filter": depth,
                "approved_only": not include_unapproved and approved is None,
                "verbosity": verbosity,
                "storage_type": storage_type
            }

        except Exception as e:
            return build_error_response(SpecificationError(str(e)))

    @mcp.tool()
    async def specification_get(
        specification_ids: List[str] = None,
        specification_id: str = None,
        display_id: str = None,
        search_query: str = None,
        specification_type: str = None,
        verbosity: str = "compact",
        limit: int = 50
    ) -> Dict[str, Any]:
        """Retrieve specific specifications by ID or search.

        Args:
            specification_ids: Batch fetch multiple specifications by UUID/display_id list
            specification_id: Single specification by UUID
            display_id: Single specification by display_id
            search_query: Text search in name/description
            specification_type: Filter by type (when searching)
            verbosity: Output detail level ("minimal", "compact", "full")
            limit: Max results for search (default: 50)

        Retrieval Modes (mutually exclusive):
            - specification_ids: Batch fetch multiple specifications
            - specification_id: Get one specification by UUID
            - display_id: Get one specification by display_id
            - search_query: Find specifications by text match

        Examples:
            # Batch retrieve specific specifications
            specification_get(specification_ids=["user_auth", "api_gateway"], verbosity="compact")

            # Get single specification by display_id
            specification_get(display_id="user_authentication", verbosity="full")

            # Search for security components
            specification_get(search_query="authentication security", specification_type="component", limit=20)
        """
        if not project_manager.is_initialized():
            return build_error_response(ValidationError("No project directory set"))

        # Count how many retrieval modes specified
        modes_specified = sum([
            specification_ids is not None,
            specification_id is not None,
            display_id is not None,
            search_query is not None
        ])

        if modes_specified == 0:
            return build_error_response(
                ValidationError("Must specify one of: specification_ids, specification_id, display_id, search_query")
            )

        if modes_specified > 1:
            return build_error_response(
                ValidationError("Specify only one of: specification_ids, specification_id, display_id, search_query")
            )

        try:
            # Get project context
            project_id, project_error = get_or_create_project_id(project_manager)
            if project_error:
                return build_error_response(DatabaseError(f"Project setup failed: {project_error}"))

            machine_id = get_machine_id()
            client, error = get_supabase_client()
            if error:
                return build_error_response(DatabaseError(f"Database connection failed: {error}"))

            specifications = []
            missing_ids = []
            match_count = 0

            # Build query using QueryBuilder
            builder = SpecificationQueryBuilder(client, project_id, machine_id)

            # Execute appropriate query based on retrieval mode
            if specification_ids:
                # Batch retrieval
                result = builder.base_query().filter_by_ids(specification_ids).execute()

                if hasattr(result, 'data'):
                    specifications = result.data or []
                    found_ids = [s['id'] for s in specifications]
                    missing_ids = [id for id in specification_ids if id not in found_ids]

            elif specification_id:
                # Single specification by UUID
                result = builder.base_query().filter_by_entity_id(specification_id).execute()

                if hasattr(result, 'data') and result.data:
                    specifications = result.data

            elif display_id:
                # Single specification by display_id
                result = builder.base_query().filter_by_display_id(display_id).execute()

                if hasattr(result, 'data') and result.data:
                    specifications = result.data

            elif search_query:
                # Text search in name and description
                result = builder.base_query().execute()

                if hasattr(result, 'data'):
                    all_specs = result.data or []

                    # Filter by search query (case-insensitive)
                    search_lower = search_query.lower()
                    for spec in all_specs:
                        name_match = search_lower in spec.get('specification_name', '').lower()
                        desc_match = search_lower in spec.get('description', '').lower()

                        if name_match or desc_match:
                            # Apply specification_type filter if specified
                            if specification_type and spec.get('specification_type') != specification_type:
                                continue

                            specifications.append(spec)

                    match_count = len(specifications)

                    # Apply limit
                    specifications = specifications[:limit]

            # Enhance with validation status (fetch validated versions)
            if specifications:
                try:
                    spec_ids = [s['id'] for s in specifications]
                    validated_map = fetch_validated_specifications(
                        client, project_id, machine_id, spec_ids
                    )
                    specifications = enhance_with_validation_status(
                        specifications, validated_map, verbosity
                    )
                except Exception as e:
                    # Silently continue without validation status on error
                    print(f"Warning: Could not enhance with validation status: {e}")

            # Format based on verbosity
            formatted_specifications = format_specifications_by_verbosity(specifications, verbosity)

            # Build response based on retrieval mode
            response = {
                "status": "success",
                "specifications": formatted_specifications,
                "verbosity": verbosity
            }

            if specification_ids:
                response["found_count"] = len(specifications)
                response["requested_count"] = len(specification_ids)
                response["missing_ids"] = missing_ids

            elif search_query:
                response["match_count"] = match_count
                response["query"] = search_query
                response["limit"] = limit
                response["returned_count"] = len(formatted_specifications)

            return response

        except Exception as e:
            return build_error_response(SpecificationError(str(e)))
