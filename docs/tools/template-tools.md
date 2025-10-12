# Template Tools (6 tools)

*Task and sprint template management and instantiation*

## Overview

Template tools manage reusable templates for tasks and sprints, supporting variable substitution and scope-based organization (global/project).

## Tools

### 1. template_list

**Purpose**: List available task templates by scope.

**Parameters**:
- `scope` (string, optional): Scope filter (default: "all")
  - `all`: Both global and project templates
  - `global`: Global templates only
  - `project`: Project templates only

**Returns**:
```python
{
    "status": "success",
    "templates": [
        {
            "template_name": "feature-implementation",
            "scope": "global",
            "metadata": {
                "description": "Standard feature implementation template",
                "variables": [
                    {"name": "feature_name", "required": true},
                    {"name": "complexity", "default": "medium"}
                ]
            }
        }
    ],
    "total_count": 5
}
```

**Usage Example**:
```python
# All templates
mcp__claude-tasks__template_list

# Project templates only
mcp__claude-tasks__template_list
  - scope: "project"
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

**Purpose**: Get complete template definition with metadata.

**Parameters**:
- `template_name` (string, required): Template name

**Returns**:
```python
{
    "status": "success",
    "template": {
        "template_name": "feature-implementation",
        "scope": "global",
        "metadata": {
            "description": "Feature implementation workflow",
            "variables": [
                {
                    "name": "feature_name",
                    "description": "Name of feature",
                    "required": true
                },
                {
                    "name": "priority",
                    "description": "Task priority",
                    "default": "medium"
                }
            ]
        },
        "task_definition": {
            "title": "{{feature_name}} Implementation",
            "description": "Implement {{feature_name}}",
            "priority": "{{priority}}",
            "subtasks": [...]
        }
    }
}
```

**Usage**: `mcp__claude-tasks__template_get --template_name "feature-implementation"`

---

### 4. sprint_template_get

**Purpose**: Get complete sprint template definition.

**Parameters**:
- `template_name` (string, required): Sprint template name

**Returns**: Sprint template with metadata and variables

**Usage**: Same as template_get but for sprints

---

### 5. task_create_from_template

**Purpose**: Create task hierarchy from template with variable substitution.

**Parameters**:
- `template_name` (string, required): Template to use
- `variables` (dict, optional): Variable values for substitution
- `sprint_id` (string, optional): Sprint to assign task to
- `priority_override` (string, optional): Override template priority

**Returns**:
```python
{
    "status": "success",
    "template_name": "feature-implementation",
    "processed_template": {
        "task_definition": {
            "title": "User Dashboard Implementation",
            "description": "Implement User Dashboard feature",
            "priority": "high",
            "subtasks": [...]
        }
    },
    "variables_applied": {
        "feature_name": "User Dashboard",
        "priority": "high"
    },
    "message": "Successfully processed template 'feature-implementation' with 2 variables"
}
```

**Usage Example**:
```python
# Basic usage
mcp__claude-tasks__task_create_from_template
  - template_name: "feature-implementation"
  - variables: {"feature_name": "User Dashboard", "priority": "high"}

# With sprint assignment
mcp__claude-tasks__task_create_from_template
  - template_name: "bug-fix"
  - variables: {"bug_id": "BUG-123", "severity": "critical"}
  - sprint_id: "SPRINT-2025-Q4-01"
  - priority_override: "critical"
```

**Use Cases**:
- Creating consistent task structures
- Generating task hierarchies from templates
- Standardizing workflows

**Notes**:
- Returns error if required variables missing
- Template variables use `{{variable_name}}` syntax
- Supports nested task hierarchies

---

### 6. sprint_create_from_template

**Purpose**: Create sprint from template with variable substitution.

**Parameters**:
- `template_name` (string, required): Sprint template name
- `variables` (dict, optional): Variable values
- `start_date` (string, optional): Sprint start date override
- `duration_override` (string, optional): Sprint duration override

**Returns**: Processed sprint template with variables applied

**Usage Example**:
```python
mcp__claude-tasks__sprint_create_from_template
  - template_name: "security-sprint"
  - variables: {"quarter": "Q4", "year": "2025"}
  - start_date: "2025-10-01"
  - duration_override: "2 weeks"
```

**Use Cases**:
- Creating sprints from standard templates
- Maintaining sprint structure consistency
- Automating sprint creation

## Common Workflows

### Task Creation from Template
```python
# 1. List available templates
templates = mcp__claude-tasks__template_list

# 2. Get template details
template = mcp__claude-tasks__template_get
  - template_name: "feature-implementation"

# 3. Review required variables
variables = template["template"]["metadata"]["variables"]

# 4. Create task from template
result = mcp__claude-tasks__task_create_from_template
  - template_name: "feature-implementation"
  - variables: {
      "feature_name": "User Profile",
      "complexity": "high",
      "estimated_hours": "40"
    }
  - sprint_id: "SPRINT-2025-Q4-01"
```

### Sprint Creation from Template
```python
# 1. Get sprint template
template = mcp__claude-tasks__sprint_template_get
  - template_name: "feature-sprint"

# 2. Create sprint with variables
sprint = mcp__claude-tasks__sprint_create_from_template
  - template_name: "feature-sprint"
  - variables: {
      "sprint_number": "4",
      "focus_area": "Authentication"
    }
  - start_date: "2025-10-15"
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

## Template Locations

- **Global**: `~/.claude/.claude-tasks/templates/task_templates.json`
- **Project**: `.claude-tasks/templates/task_templates.json`

Templates are stored in dual storage format (JSON files + database sync).
