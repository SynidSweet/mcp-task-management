# Document Tools (5 tools)

*Document management with hierarchical organization and approval workflows*

## Overview

Document tools manage project documentation with parent-child hierarchies, approval workflows, and scope-based organization (project/global). All operations are file-based with automatic database sync.

## Key Concepts

### Document Hierarchy
- Documents use `parent_id` for hierarchy (UUID-based)
- Calculated paths (e.g., "Architecture.Database.Schema")
- Automatic level depth calculation

### Approval Workflow
- Documents start as `approved: false`
- Editing creates "current" version
- Approval promotes current to approved version

### Document Scopes
- `project`: Project-specific documentation
- `global`: Cross-project documentation

## Tools

### 1. document_create

**Purpose**: Create new document with scope support and parent_id hierarchy.

**Parameters**:
- `document_title` (string, required): Document title
- `document_type` (string, required): Document type (e.g., "guide", "reference", "specification")
- `parent_id` (string, optional): Parent document UUID
- `description` (string, optional): Document description
- `status` (string, optional): Document status (default: "draft")
- `priority` (string, optional): Priority (default: "medium")
- `sections` (list, optional): Document sections with content
- `scope` (string, optional): Scope (default: "project")

**Returns**:
```python
{
    "status": "success",
    "document_id": "uuid-here",
    "calculated_path": "Architecture.Database",
    "document_title": "Database Schema",
    "document_type": "specification",
    "parent_id": "parent-uuid",
    "machine_id": "machine-123",
    "sections_added": 3,
    "scope": "project",
    "message": "Document 'Database Schema' created in project scope"
}
```

**Usage Example**:
```python
# Root document
mcp__claude-tasks__document_create
  - document_title: "Architecture Guide"
  - document_type: "guide"
  - description: "System architecture documentation"
  - sections: [
      {"title": "Overview", "content": "System overview..."},
      {"title": "Components", "content": "Key components..."}
    ]

# Child document
mcp__claude-tasks__document_create
  - document_title: "Database Design"
  - document_type: "specification"
  - parent_id: "architecture-guide-uuid"
  - description: "Database schema and design decisions"
```

---

### 2. document_update

**Purpose**: Update existing document fields.

**Parameters**:
- `document_path` (string, required): Document path or ID
- `document_title` (string, optional): New title
- `description` (string, optional): New description
- `status` (string, optional): New status
- `priority` (string, optional): New priority
- `sections` (list, optional): Updated sections

**Returns**: Updated document object

**Usage Example**:
```python
mcp__claude-tasks__document_update
  - document_path: "Architecture.Database"
  - status: "review"
  - sections: [
      {"title": "Schema", "content": "Updated schema..."}
    ]
```

**Notes**:
- Updates create "current" version (not approved until explicitly approved)
- Partial updates supported
- Path can be calculated path or document UUID

---

### 3. document_query

**Purpose**: Search and filter documents with comprehensive criteria.

**Parameters**:
- `query` (string, optional): Text search in title/description
- `document_type` (string, optional): Filter by type
- `scope` (string, optional): Filter by scope (project/global/all)
- `status` (string, optional): Filter by status
- `include_unapproved` (bool, optional): Include unapproved docs (default: false)
- `limit` (int, optional): Maximum results (default: 50)

**Returns**:
```python
{
    "status": "success",
    "documents": [
        {
            "id": "uuid",
            "document_title": "Architecture Guide",
            "document_type": "guide",
            "calculated_path": "Architecture",
            "status": "published",
            "priority": "high",
            "scope": "project",
            "approved": true,
            "sections_count": 5
        }
    ],
    "total_matches": 12
}
```

**Usage Example**:
```python
# Search by text
mcp__claude-tasks__document_query
  - query: "database"

# Filter by type and scope
mcp__claude-tasks__document_query
  - document_type: "specification"
  - scope: "project"

# Get all drafts
mcp__claude-tasks__document_query
  - status: "draft"
  - include_unapproved: true
```

---

### 4. document_get

**Purpose**: Get single document with full details.

**Parameters**:
- `document_id` (string, optional): Document UUID
- `document_path` (string, optional): Document path
- `display_id` (string, optional): Display ID

**Returns**: Complete document object with all sections

**Usage Example**:
```python
# By UUID
mcp__claude-tasks__document_get
  - document_id: "uuid-here"

# By path
mcp__claude-tasks__document_get
  - document_path: "Architecture.Database"
```

---

### 5. document_delete

**Purpose**: Delete document (soft delete with flag).

**Parameters**:
- `document_path` (string, required): Document path or ID
- `deletion_reason` (string, optional): Reason for deletion

**Returns**: Deletion confirmation

**Notes**:
- Soft delete (marks as deleted, doesn't remove)
- Can be restored if needed
- Cleans up references

## Common Workflows

### Creating Documentation Hierarchy
```python
# 1. Create root documentation
root = mcp__claude-tasks__document_create
  - document_title: "Project Documentation"
  - document_type: "guide"
  - scope: "project"

# 2. Create sections
arch = mcp__claude-tasks__document_create
  - document_title: "Architecture"
  - document_type: "guide"
  - parent_id: root["document_id"]

# 3. Create detailed specs
mcp__claude-tasks__document_create
  - document_title: "Database Schema"
  - document_type: "specification"
  - parent_id: arch["document_id"]
  - sections: [
      {"title": "Tables", "content": "Table definitions..."},
      {"title": "Relationships", "content": "FK relationships..."}
    ]
```

### Document Approval Workflow
```python
# 1. Create draft
doc = mcp__claude-tasks__document_create
  - document_title: "API Guide"
  - document_type: "guide"
  - status: "draft"

# 2. Update content
mcp__claude-tasks__document_update
  - document_path: doc["calculated_path"]
  - sections: [{"title": "Endpoints", "content": "..."}]
  - status: "review"

# 3. Approve (requires separate approval tool)
# mcp__claude-tasks__document_save_changes
#   - document_path: doc["calculated_path"]
```

### Finding Documents
```python
# Search for specifications
specs = mcp__claude-tasks__document_query
  - document_type: "specification"
  - scope: "project"

# Get specific document
doc = mcp__claude-tasks__document_get
  - document_path: "Architecture.Database.Schema"

# List all guides
guides = mcp__claude-tasks__document_query
  - document_type: "guide"
  - limit: 100
```

## Document Structure

### Minimal Document
```python
{
    "document_title": "Guide Name",
    "document_type": "guide"
}
```

### Complete Document
```python
{
    "document_title": "Complete Guide",
    "document_type": "guide",
    "parent_id": "parent-uuid",
    "description": "Detailed guide description",
    "status": "published",
    "priority": "high",
    "scope": "project",
    "sections": [
        {
            "title": "Introduction",
            "content": "Guide introduction...",
            "order": 1
        },
        {
            "title": "Usage",
            "content": "How to use...",
            "order": 2
        }
    ]
}
```

## Best Practices

1. **Organize hierarchically** - Use parent_id to create logical structure
2. **Use meaningful types** - Choose appropriate document_type
3. **Write clear descriptions** - Help with searchability
4. **Manage sections** - Break content into logical sections
5. **Set appropriate scope** - Project vs global based on reusability
6. **Track status** - Use status field for workflow management
7. **Version control** - Use approval workflow for important docs

## Performance Notes

- Document queries are file-based (fast)
- Large section content may impact load time
- Use query filters to reduce result sets
- Approval workflow prevents accidental overwrites
