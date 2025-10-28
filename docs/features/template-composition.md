# Template Composition Feature

**Status**: Implemented
**Version**: 2.0
**Added**: 2025-10-23
**Updated**: 2025-10-23 - Unlimited depth support

## Overview

Template composition allows you to **reference external task templates** from within sprint templates or task templates, enabling reuse of common task definitions across multiple sprints and contexts.

**✨ NEW in v2.0: Unlimited Composition Depth** - Templates can now reference other templates which themselves reference other templates, with unlimited nesting depth. Only circular references are prevented.

## Key Benefits

1. **Reusability** - Define common tasks once, use everywhere
2. **Consistency** - All sprints use the same task structure
3. **Maintainability** - Update task template once, affects all instances
4. **DRY Principle** - Don't repeat task definitions
5. **Composition** - Build complex templates from smaller reusable pieces
6. **✨ Unlimited Depth** - Compose templates to any depth (only cycles prevented)

## Syntax

### Inline Task Definition (Traditional)

```json
{
  "title": "Setup infrastructure",
  "description": "Configure servers and databases",
  "priority": "high"
}
```

### Template Reference (New)

```json
{
  "template_ref": "setup_infrastructure",
  "variables": {
    "environment": "production"
  }
}
```

### Template Reference with Field Overrides

```json
{
  "template_ref": "setup_infrastructure",
  "title": "Setup Production Infrastructure",  // Overrides template title
  "priority": "critical",  // Overrides template priority
  "variables": {
    "environment": "production",
    "region": "us-west-2"
  }
}
```

## Variable Resolution

Variables are resolved using a **cascading scope** system where the closest scope wins:

```
Sprint-level variables (lowest priority)
  ↓ (merge)
Referenced template defaults
  ↓ (merge)
Inline task variables (highest priority)
```

### Example

**Sprint Template:**
```json
{
  "variables": {"region": "us-east-1", "env": "staging"},
  "planning_tasks": [
    {
      "template_ref": "deploy_service",
      "variables": {"env": "production"}  // Overrides sprint's "staging"
    }
  ]
}
```

**Task Template (deploy_service):**
```json
{
  "metadata": {
    "variables": [
      {"name": "region", "default": "us-west-2"},
      {"name": "env", "default": "dev"}
    ]
  },
  "task_definition": {
    "title": "Deploy to {{env}} in {{region}}"
  }
}
```

**Result:**
- `env`: `"production"` (from inline variables - highest priority)
- `region`: `"us-east-1"` (from sprint variables)
- **Final title**: `"Deploy to production in us-east-1"`

## Field Overrides

Any field specified in the task reference **overrides** the corresponding field from the referenced template:

```json
{
  "template_ref": "code_review",
  "title": "Critical Security Review",  // Overrides template.task_definition.title
  "priority": "critical",  // Overrides template.task_definition.priority
  "notes": "Focus on authentication",  // Adds/overrides notes
  "variables": {
    "component": "Auth Module"
  }
}
```

## Use Cases

### 1. Common Sprint Tasks

Define tasks that appear in every sprint:

**Task Template (setup_infrastructure.json):**
```json
{
  "templates": {
    "setup_infrastructure": {
      "metadata": {
        "variables": [
          {"name": "environment", "required": true},
          {"name": "region", "default": "us-east-1"}
        ]
      },
      "task_definition": {
        "title": "Setup {{environment}} Infrastructure",
        "description": "Configure servers, databases, and networking",
        "priority": "high"
      }
    }
  }
}
```

**Sprint Template:**
```json
{
  "planning_tasks": [
    {
      "template_ref": "setup_infrastructure",
      "variables": {"environment": "staging"}
    }
  ]
}
```

### 2. Quality Assurance Tasks

Reuse testing and review tasks:

```json
{
  "milestone_tasks": [
    {
      "template_ref": "code_review",
      "variables": {"component": "Payment Gateway"}
    },
    {
      "template_ref": "security_audit",
      "priority": "critical"  // Override template priority
    }
  ]
}
```

### 3. Documentation Tasks

Standardize documentation requirements:

```json
{
  "planning_tasks": [
    {
      "template_ref": "documentation_update",
      "variables": {
        "feature_name": "User Dashboard",
        "doc_type": "API documentation"
      }
    }
  ]
}
```

## Validation Rules

The data integrity checker validates template references with these rules:

### 1. Referenced Template Must Exist

**Invalid:**
```json
{
  "template_ref": "non_existent_template"  // ❌ Template not found
}
```

**Error:**
```
CRITICAL: Template 'my_sprint' references non-existent template 'non_existent_template'
Fix: Create template 'non_existent_template' or remove reference
```

### 2. No Circular References

**✨ NEW: Unlimited Depth Composition Supported!**

Templates can now reference other templates which themselves reference other templates, with **unlimited depth**. The only restriction is **no circular references** (Template A → Template B → Template A).

**Valid - Multi-Level Composition:**
```json
// Template A (references B)
{
  "subtasks": [
    {"template_ref": "template_b"}  // ✓ OK
  ]
}

// Template B (references C)
{
  "subtasks": [
    {"template_ref": "template_c"}  // ✓ OK - unlimited depth!
  ]
}

// Template C (references D)
{
  "subtasks": [
    {"template_ref": "template_d"}  // ✓ Still OK!
  ]
}

// Template D (base template)
{
  "task_definition": {
    "title": "Base Task",
    "description": "..."
  }
}
```

**Invalid - Circular Reference:**
```json
// Template A → Template B → Template A (cycle!)
{
  "planning_tasks": [
    {"template_ref": "template_b"}
  ]
}

// Template B references back to A
{
  "subtasks": [
    {"template_ref": "template_a"}  // ❌ Circular reference!
  ]
}
```

**Error:**
```
CRITICAL: Circular reference detected: template_a → template_b → template_a
Fix: Break the cycle by removing one of the template references in the chain
```

**How Cycle Detection Works:**
- Uses graph-based DFS algorithm during validation
- Runtime detection using visited set during resolution
- Both prevent infinite loops while allowing unlimited depth

## Resolution Algorithm

When a `template_ref` is encountered during sprint or task creation:

1. **Load Referenced Template**
   - Search project templates first
   - Fall back to global templates
   - Raise error if not found

2. **Merge Variables**
   - Start with parent (sprint/task) variables
   - Add template defaults (if not already set)
   - Override with inline variables

3. **Apply Variable Substitution**
   - Replace `{{variable_name}}` with values
   - Recursively process all strings in template

4. **Apply Field Overrides**
   - Copy inline fields (except `template_ref`, `variables`)
   - Override template fields with same names

5. **Return Resolved Task Definition**

## Implementation Details

### Code Location

- **Resolution Function**: `tools/template_tools.py:318` (`_resolve_task_reference`)
- **Sprint Integration**: `tools/template_tools.py:686-697`
- **Task Integration**: `tools/template_tools.py:103-116`
- **Validation**: `check_data_integrity.py:507-584`

### Resolution Timing

Template references are resolved **at task creation time** (lazy resolution), not at template load time. This ensures:
- Always uses most current version of referenced template
- Variables are properly scoped from parent context
- Errors are caught during actual usage, not template definition

### Error Handling

```python
try:
    resolved = await _resolve_task_reference(task_def, parent_vars, pm)
except ValueError as e:
    # Template not found
    logger.error(f"Template reference failed: {e}")
    raise
```

## Testing

Run the template composition test suite:

```bash
python3 test_template_composition.py
```

**Tests cover:**
1. Basic template reference resolution
2. Variable cascading from parent to child
3. Field overrides
4. Sprint template integration
5. Error handling for missing templates

## Examples

### Complete Example: Feature Development Sprint

**Task Templates (`task_templates.json`):**
```json
{
  "templates": {
    "setup_infrastructure": {
      "metadata": {
        "variables": [
          {"name": "environment", "required": true},
          {"name": "region", "default": "us-east-1"}
        ]
      },
      "task_definition": {
        "title": "Setup {{environment}} Infrastructure in {{region}}",
        "description": "Configure servers, databases, and networking",
        "priority": "high"
      }
    },
    "code_review": {
      "metadata": {
        "variables": [
          {"name": "component", "required": true}
        ]
      },
      "task_definition": {
        "title": "Code Review: {{component}}",
        "description": "Comprehensive code review",
        "priority": "medium"
      }
    },
    "documentation_update": {
      "metadata": {
        "variables": [
          {"name": "feature_name", "required": true},
          {"name": "doc_type", "default": "user guide"}
        ]
      },
      "task_definition": {
        "title": "Update {{doc_type}} for {{feature_name}}",
        "description": "Update documentation",
        "priority": "medium"
      }
    }
  }
}
```

**Sprint Template (`sprint_templates.json`):**
```json
{
  "templates": {
    "feature_sprint": {
      "metadata": {
        "variables": [
          {"name": "feature_name", "required": true},
          {"name": "environment", "default": "staging"}
        ]
      },
      "sprint_definition": {
        "title": "{{feature_name}} Development Sprint",
        "description": "Complete {{feature_name}} feature",
        "focus": {
          "primary_objective": "Deliver {{feature_name}}"
        }
      },
      "planning_tasks": [
        {
          "template_id": "infra",
          "template_ref": "setup_infrastructure",
          "variables": {
            "environment": "{{environment}}",
            "region": "us-west-2"
          }
        },
        {
          "template_id": "implement",
          "title": "Implement {{feature_name}}",
          "description": "Core implementation",
          "priority": "critical",
          "dependencies": ["@infra"]
        },
        {
          "template_id": "review",
          "template_ref": "code_review",
          "variables": {"component": "{{feature_name}}"},
          "dependencies": ["@implement"]
        }
      ],
      "milestone_tasks": [
        {
          "template_ref": "documentation_update",
          "variables": {
            "feature_name": "{{feature_name}}",
            "doc_type": "API documentation"
          }
        }
      ]
    }
  }
}
```

**Usage:**
```python
# Create sprint from template
result = await sprint_create_from_template(
    template_name="feature_sprint",
    variables={
        "feature_name": "User Dashboard",
        "environment": "production"
    },
    start_date="2025-11-01"
)

# Result: Sprint with 4 tasks created
# - Setup production Infrastructure in us-west-2
# - Implement User Dashboard
# - Code Review: User Dashboard
# - Update API documentation for User Dashboard
```

## Best Practices

1. **Create Atomic Templates** - Each task template should represent a single, reusable concept
2. **Use Clear Variable Names** - Make template variables self-documenting
3. **Provide Defaults** - Add sensible defaults for optional variables
4. **Document Templates** - Add clear descriptions in metadata
5. **Test Compositions** - Run `test_template_composition.py` after creating new templates
6. **Validate Regularly** - Run `check_data_integrity.py` to catch reference issues
7. **Version Templates** - Increment version number when making breaking changes

## Migration Guide

### Converting Inline Tasks to Template References

**Before (Inline):**
```json
{
  "planning_tasks": [
    {
      "title": "Setup staging Infrastructure",
      "description": "Configure servers...",
      "priority": "high"
    },
    {
      "title": "Setup production Infrastructure",
      "description": "Configure servers...",
      "priority": "high"
    }
  ]
}
```

**After (Template Composition):**

1. Create reusable task template:
```json
// task_templates.json
{
  "templates": {
    "setup_infrastructure": {
      "metadata": {
        "variables": [{"name": "environment", "required": true}]
      },
      "task_definition": {
        "title": "Setup {{environment}} Infrastructure",
        "description": "Configure servers...",
        "priority": "high"
      }
    }
  }
}
```

2. Update sprint template to use reference:
```json
{
  "planning_tasks": [
    {
      "template_ref": "setup_infrastructure",
      "variables": {"environment": "staging"}
    },
    {
      "template_ref": "setup_infrastructure",
      "variables": {"environment": "production"}
    }
  ]
}
```

## Limitations

1. **No Circular References** - Templates cannot reference each other in a cycle (validated at check time)
2. **Same Template Type** - Task templates for tasks, sprint templates for sprints
3. **File System Source** - Templates loaded from JSON files, not database
4. **No Cross-Branch Cycles** - While depth is unlimited, cycles anywhere in the composition tree are prevented

## Future Enhancements

Potential future improvements:
- Template versioning and compatibility checks
- Template inheritance (extend vs reference)
- Conditional template inclusion
- Template library marketplace
- Visual template composition editor

## See Also

- [Template Tools Documentation](../tools/template-tools.md)
- [Data Integrity Checker](../specifications/data-integrity-checker.md)
- [Sprint Template Creation Guide](../development/sprint-templates.md)
- [Task Template Best Practices](../development/task-templates.md)
