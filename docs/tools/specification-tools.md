# Specification Tools (10 tools)

*Entity hierarchy management, validation, and bulk operations*

## Overview

Specification tools manage entities using display ID-based hierarchies. All tools support both file and database operations with automatic synchronization.

## Key Concepts

### Display ID System
- Entities use human-readable `display_id` (e.g., "auth_module", "user_login")
- Hierarchy via `parent_display_id` (not parent_id)
- Paths calculated from hierarchy (e.g., "auth_module.user_login")

### Entity Types
Valid types: `module`, `feature`, `service`, `api`, `contract`, `component`, `screen`, `test`, `validator`, `orchestrator`, `database`

## Tools

### 1. specification_create_entity

**Purpose**: Create entity using display ID-based hierarchy.

**Parameters**:
- `entity_name` (string, required): Human-readable name
- `entity_type` (string, required): Entity type (see valid types above)
- `display_id` (string, required): Unique display ID (e.g., "user_auth")
- `parent_display_id` (string, optional): Parent entity display ID
- `description` (string, optional): Entity description
- `requirements` (list, optional): List of requirements
- `constraints` (list, optional): List of constraints

**Returns**:
```python
{
    "status": "success",
    "specification_id": "uuid-here",
    "display_id": "user_auth",
    "parent_display_id": "auth_module",
    "message": "Specification 'User Authentication' created with display ID 'user_auth'"
}
```

**Usage Example**:
```python
# Root entity
mcp__claude-tasks__specification_create_entity
  - entity_name: "User Module"
  - entity_type: "module"
  - display_id: "user_module"
  - description: "User management functionality"

# Child entity
mcp__claude-tasks__specification_create_entity
  - entity_name: "User Authentication"
  - entity_type: "feature"
  - display_id: "user_auth"
  - parent_display_id: "user_module"
  - requirements: ["OAuth 2.0 support", "Session management"]
```

---

### 2. specification_update_entity

**Purpose**: Update existing entity.

**Parameters**:
- `entity_id` (string, required): Entity UUID
- `entity_name` (string, optional): New name
- `display_id` (string, optional): New display ID
- `parent_display_id` (string, optional): New parent
- `description` (string, optional): New description
- `requirements` (list, optional): Updated requirements
- `constraints` (list, optional): Updated constraints

**Returns**: Updated entity object

**Usage**: Modify any entity field (partial updates supported)

---

### 3. specification_list_entities

**Purpose**: List entities with hierarchical depth control and smart verbosity.

**Parameters**:
- `project_id` (string, optional): Project ID (auto-detected if not provided)
- `include_unapproved` (bool, optional): Include unapproved entities (default: false)
- `verbosity` (string, optional): Output level (default: "full")
  - `ultra_minimal`: "path|type|name" format
  - `minimal`: id + core fields only
  - `compact`: No arrays (requirements/constraints)
  - `full`: Complete entity data
- `depth` (int, optional): Hierarchy depth (default: -1 = all)
  - `-1`: All levels
  - `0`: Root only
  - `1`: Root + children
  - `2`: Root + children + grandchildren
- `root_entity_id` (string, optional): Start from specific entity

**Returns**:
```python
{
    "status": "success",
    "specifications": [
        {
            "display_id": "user_module",
            "specification_name": "User Module",
            "specification_type": "module",
            "parent_display_id": null,
            "description": "User management functionality",
            "approved": false
        }
    ],
    "total_count": 15
}
```

**Usage Example**:
```python
# All entities
mcp__claude-tasks__specification_list_entities

# Root entities only
mcp__claude-tasks__specification_list_entities
  - depth: 0

# Minimal format for quick scan
mcp__claude-tasks__specification_list_entities
  - verbosity: "ultra_minimal"
```

---

### 4. specification_get_entity_children

**Purpose**: Get direct children of an entity.

**Parameters**:
- `parent_id` (string, required): Parent entity UUID

**Returns**: List of child entities

---

### 5. specification_delete_entity

**Purpose**: Delete entity with optional cascade to children.

**Parameters**:
- `entity_id` (string, required): Entity UUID to delete
- `cascade` (bool, optional): Delete children too (default: false)

**Returns**: Deletion confirmation

**Warning**: Cascade deletion is permanent and cannot be undone

---

### 6. specification_get_entities_bulk

**Purpose**: Get multiple entities by ID - perfect for targeted queries.

**Parameters**:
- `entity_ids` (list, required): List of entity UUIDs
- `verbosity` (string, optional): Output level (default: "compact")

**Returns**: List of requested entities

**Usage Example**:
```python
mcp__claude-tasks__specification_get_entities_bulk
  - entity_ids: ["uuid1", "uuid2", "uuid3"]
  - verbosity: "full"
```

---

### 7. specification_get_entity_subtree

**Purpose**: Get entity and descendants up to specified depth.

**Parameters**:
- `parent_id` (string, required): Root entity UUID
- `depth` (int, optional): Max depth from root (default: -1 = all)
- `verbosity` (string, optional): Output level (default: "minimal")

**Returns**: Entity tree structure

**Usage**: Explore branches of hierarchy

---

### 8. specification_register_project

**Purpose**: Register current project in specifications system database.

**Parameters**: None (uses current project directory)

**Returns**: Project registration confirmation

**Usage**: One-time setup per project

---

### 9. specification_get_machine_id

**Purpose**: Get current machine ID for specifications system.

**Parameters**: None

**Returns**:
```python
{
    "status": "success",
    "machine_id": "machine-123"
}
```

---

### 10. specification_set_machine_id

**Purpose**: Set machine ID by creating/updating configuration.

**Parameters**:
- `machine_id` (string, required): New machine ID

**Returns**: Confirmation

**Usage**: Configure multi-machine environments

## Common Workflows

### Building Entity Hierarchy
```python
# 1. Create root module
root = mcp__claude-tasks__specification_create_entity
  - entity_name: "Authentication System"
  - entity_type: "module"
  - display_id: "auth_system"

# 2. Create features
mcp__claude-tasks__specification_create_entity
  - entity_name: "User Login"
  - entity_type: "feature"
  - display_id: "user_login"
  - parent_display_id: "auth_system"

mcp__claude-tasks__specification_create_entity
  - entity_name: "Password Reset"
  - entity_type: "feature"
  - display_id: "password_reset"
  - parent_display_id: "auth_system"

# 3. Create components
mcp__claude-tasks__specification_create_entity
  - entity_name: "Login Form"
  - entity_type: "component"
  - display_id: "login_form"
  - parent_display_id: "user_login"
```

### Exploring Hierarchy
```python
# Get all root entities
roots = mcp__claude-tasks__specification_list_entities
  - depth: 0

# Get specific subtree
subtree = mcp__claude-tasks__specification_get_entity_subtree
  - parent_id: "auth_system_uuid"
  - depth: 2
  - verbosity: "full"

# Get children
children = mcp__claude-tasks__specification_get_entity_children
  - parent_id: "auth_system_uuid"
```

## Best Practices

1. **Use meaningful display IDs** - Lowercase, underscores, descriptive
2. **Plan hierarchy** - Design entity structure before creating
3. **Set requirements** - Document requirements at creation time
4. **Use appropriate types** - Match entity type to actual component type
5. **Leverage verbosity** - Use minimal output for large datasets
6. **Depth limits** - Use depth parameter to avoid overwhelming output
