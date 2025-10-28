# Template Tools (6 tools)

*Task and sprint template management and instantiation*

## Overview

Template tools manage reusable templates for tasks and sprints stored in normalized database tables (`template_tasks`, `template_sprints`) that mirror the structure of actual tasks and sprints.

**Key Features**:
- **Normalized Storage**: Templates stored in queryable database tables (not monolithic JSON)
- **Template Composition**: Templates can reference other templates for unlimited nesting
- **Entry Task Marking**: `is_entry_task` field distinguishes root templates from nested subtasks
- **Variable Substitution**: `{{variable}}` placeholders in all text fields
- **Hierarchy Support**: Parent-child relationships like actual tasks

## Tools

### 1. template_list

**Purpose**: List available task templates from normalized database.

**Parameters**:
- `scope` (string, optional): Scope filter (default: "all")
  - `all`: Both global and project templates
  - `global`: Global templates only
  - `project`: Project templates only
- `category` (string, optional): Filter by category (e.g., "infrastructure", "quality")
- `entry_tasks_only` (boolean, optional): If true, only show root templates (default: true)

**Returns**:
```python
{
    "status": "success",
    "templates": [
        {
            "name": "setup_infrastructure",  # template_id
            "display_name": "Infrastructure Setup",
            "description": "Standard infrastructure setup",
            "category": "infrastructure",
            "scope": "project",
            "variables_count": 2,
            "child_count": 0,
            "is_reference": false,
            "template_type": "task"
        }
    ],
    "count": 5,
    "scope": "all",
    "entry_tasks_only": true
}
```

**Usage Example**:
```python
# All entry templates
mcp__claude-tasks__template_list

# Infrastructure templates only
mcp__claude-tasks__template_list
  - category: "infrastructure"

# Include nested subtasks
mcp__claude-tasks__template_list
  - entry_tasks_only: false
```

---

### 2. sprint_template_list

**Purpose**: List available sprint templates by scope.

**Parameters**:
- `scope` (string, optional): Scope filter (default: "all")

**Returns**: List of sprint templates with metadata

**Usage**: Same as template_list but for sprints

---

### 3. template_get

**Purpose**: Get complete task template with optional reference/child resolution.

**Parameters**:
- `template_id` (string, required): Template ID to retrieve
- `resolve_references` (boolean, optional): Resolve template composition (default: true)
- `resolve_children` (boolean, optional): Include resolved children (default: true)

**Returns**:
```python
{
    "status": "success",
    "template_id": "quality_gate",
    "template": {
        "id": "uuid-xxx",
        "template_id": "quality_gate",
        "template_name": "Quality Gate",
        "description": "Multi-level quality checks",
        "category": "quality",
        "scope": "project",
        "is_entry_task": true,
        "title": "Quality Gate: {{component}}",
        "task_description": "Comprehensive quality checks for {{component}}",
        "priority": "high",
        "variables": [
            {
                "name": "component",
                "type": "string",
                "required": true,
                "description": "Component being checked"
            }
        ],
        "child_template_ids": ["quality_gate_ref_0", "quality_gate_child_1"],
        "references_template_id": null,
        "resolved_children": [
            {
                "template_id": "quality_gate_ref_0",
                "references_template_id": "code_review",
                "_is_reference": true,
                "_reference_to": "code_review"
            },
            {
                "template_id": "quality_gate_child_1",
                "title": "Security Scan: {{component}}",
                "is_entry_task": false
            }
        ]
    }
}
```

**Usage**:
```python
# Get with full resolution
mcp__claude-tasks__template_get
  - template_id: "quality_gate"

# Get without resolution (faster)
mcp__claude-tasks__template_get
  - template_id: "quality_gate"
  - resolve_references: false
  - resolve_children: false
```

---

### 4. sprint_template_get

**Purpose**: Get complete sprint template with optional task resolution.

**Parameters**:
- `template_id` (string, required): Sprint template ID
- `resolve_tasks` (boolean, optional): Resolve all assigned task templates (default: true)

**Returns**:
```python
{
    "status": "success",
    "template_id": "test_feature",
    "type": "sprint_template",
    "template": {
        "template_id": "test_feature",
        "template_name": "test_feature",
        "title": "{{feature_name}} Development Sprint",
        "sprint_description": "Sprint for developing {{feature_name}}",
        "focus": {
            "primary_objective": "Complete {{feature_name}} feature",
            "scope_boundaries": "Development, testing, deployment"
        },
        "variables": [
            {"name": "feature_name", "required": true},
            {"name": "environment", "default": "staging"}
        ],
        "task_ids": ["task1", "task2", "task3", "milestone1"],
        "resolved_tasks": [
            {
                "template_id": "task1",
                "title": "Setup {{environment}} Infrastructure",
                "references_template_id": "setup_infrastructure",
                ...
            },
            {...}
        ]
    }
}
```

**Usage**:
```python
# Get with task resolution
mcp__claude-tasks__sprint_template_get
  - template_id: "test_feature"

# Get without task resolution (faster)
mcp__claude-tasks__sprint_template_get
  - template_id: "test_feature"
  - resolve_tasks: false
```

---

### 5. task_create_from_template

**Purpose**: Create actual task(s) from template with variable substitution and hierarchy.

**Parameters**:
- `template_id` (string, required): Template ID to use
- `variables` (dict, optional): Variable values for substitution
- `sprint_id` (string, optional): Sprint to assign tasks to
- `priority_override` (string, optional): Override template priority

**Returns**:
```python
{
    "status": "success",
    "template_id": "quality_gate",
    "created_tasks": [
        {
            "id": "TASK-2025-042",
            "title": "Quality Gate: API Module",
            "description": "Comprehensive quality checks for API Module",
            "priority": "high",
            "status": "pending",
            "child_task_ids": ["TASK-2025-043", "TASK-2025-044"],
            ...
        },
        {
            "id": "TASK-2025-043",
            "title": "Code Review: API Module",
            "parent_task_id": "TASK-2025-042",
            ...
        },
        {
            "id": "TASK-2025-044",
            "title": "Security Scan: API Module",
            "parent_task_id": "TASK-2025-042",
            ...
        }
    ],
    "tasks_count": 3,
    "variables_applied": {"component": "API Module"},
    "message": "Successfully created 3 task(s) from template 'quality_gate'"
}
```

**Usage Example**:
```python
# Create tasks from template
mcp__claude-tasks__task_create_from_template
  - template_id: "code_review"
  - variables: {"component": "Authentication"}

# With sprint assignment
mcp__claude-tasks__task_create_from_template
  - template_id: "quality_gate"
  - variables: {"component": "API Gateway"}
  - sprint_id: "SPRINT-20251026_120000"
  - priority_override: "critical"
```

**Behavior**:
- Creates actual task records in tasks table
- Resolves all template references recursively
- Creates child tasks for templates with hierarchy
- Substitutes all `{{variable}}` placeholders
- Returns error if required variables missing

---

### 6. sprint_create_from_template

**Purpose**: Create actual sprint and all associated tasks from template.

**Parameters**:
- `template_id` (string, required): Sprint template ID
- `variables` (dict, optional): Variable values
- `start_date` (string, optional): Sprint start date override
- `duration_override` (string, optional): Sprint duration override

**Returns**:
```python
{
    "status": "success",
    "sprint": {
        "id": "SPRINT-20251026_120000",
        "title": "User Authentication Development Sprint",
        "description": "Sprint for developing User Authentication feature",
        "status": "planning",
        "task_ids": ["TASK-2025-050", "TASK-2025-051", "TASK-2025-052"],
        "focus": {
            "primary_objective": "Complete User Authentication feature",
            "scope_boundaries": "Development, testing, deployment to staging"
        },
        ...
    },
    "created_tasks": [
        {"id": "TASK-2025-050", "title": "Setup staging Infrastructure", ...},
        {"id": "TASK-2025-051", "title": "Implement User Authentication", ...},
        {"id": "TASK-2025-052", "title": "Code Review: User Authentication", ...}
    ],
    "tasks_count": 3,
    "variables_applied": {"feature_name": "User Authentication", "environment": "staging"},
    "message": "Sprint 'User Authentication Development Sprint' created successfully from template with 3 tasks"
}
```

**Usage Example**:
```python
# Create sprint with tasks
mcp__claude-tasks__sprint_create_from_template
  - template_id: "test_feature"
  - variables: {"feature_name": "User Authentication", "environment": "staging"}
  - start_date: "2025-11-01"
```

**Behavior**:
- Creates actual sprint record in sprints table
- Resolves all template tasks (planning + milestone)
- Creates all tasks with hierarchy and dependencies
- Assigns all tasks to the created sprint
- Substitutes all `{{variable}}` placeholders

## Common Workflows

### Task Creation from Template
```python
# 1. List available templates
templates = mcp__claude-tasks__template_list
  - entry_tasks_only: true

# 2. Get template details
template = mcp__claude-tasks__template_get
  - template_id: "code_review"

# 3. Review required variables
variables = template["template"]["variables"]

# 4. Create actual tasks from template
result = mcp__claude-tasks__task_create_from_template
  - template_id: "code_review"
  - variables: {
      "component": "User Profile",
      "estimated_hours": "40"
    }
  - sprint_id: "SPRINT-2025-Q4-01"
```

### Sprint Creation from Template
```python
# 1. Get sprint template
template = mcp__claude-tasks__sprint_template_get
  - template_id: "test_feature"

# 2. Review required variables
variables = template["template"]["variables"]

# 3. Create actual sprint with tasks
result = mcp__claude-tasks__sprint_create_from_template
  - template_id: "test_feature"
  - variables: {
      "feature_name": "User Authentication",
      "environment": "staging"
    }
  - start_date: "2025-11-01"

# Result contains:
# - sprint: Created sprint record
# - created_tasks: All tasks created from template
# - tasks_count: Total number of tasks
```

## Template Variable System

### Variable Definition
```python
{
    "name": "feature_name",
    "description": "Name of the feature to implement",
    "required": true,
    "default": null
}
```

### Variable Usage in Templates
```python
{
    "title": "{{feature_name}} Implementation",
    "description": "Implement the {{feature_name}} feature with {{complexity}} complexity"
}
```

### Variable Substitution
- Required variables must be provided
- Optional variables use default if not provided
- Variables use `{{name}}` syntax
- Supports nested object references

## Best Practices

1. **Define clear variables** - Document variable purpose and requirements
2. **Use defaults** - Provide sensible defaults for optional variables
3. **Validate early** - Check required variables before processing
4. **Version templates** - Maintain template versions for consistency
5. **Scope appropriately** - Use global for common patterns, project for specific workflows
6. **Test templates** - Verify template output before use

## Template Storage

**Database Tables** (Primary Storage):
- `template_tasks` - Task templates with hierarchy and composition
- `template_sprints` - Sprint templates with task assignments

**File Sync**: Currently templates are stored in database only. File sync to/from local JSON files is planned for future implementation.

**Query Templates Directly**:
```sql
-- List all entry task templates
SELECT template_id, template_name, category
FROM template_tasks
WHERE is_entry_task = true;

-- Get template with children
SELECT * FROM template_tasks WHERE template_id = 'quality_gate';
```
