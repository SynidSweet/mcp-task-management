# MCP Tools Reference - Complete Overview

*Last updated: 2025-10-07*

This is the complete reference for all 35 MCP tools in the mcp-server-dev system. Tools are organized into 8 categories for easy navigation.

## 📚 Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| [System Tools](system-tools.md) | 3 tools | Project initialization, health checks, context loading |
| [Task Tools](task-tools.md) | 6 tools | Task CRUD operations, search, and dependency management |
| [Sprint Tools](sprint-tools.md) | 5 tools | Sprint management, task assignment, strategic context |
| [Journal Tools](journal-tools.md) | 3 tools | Session tracking, work history, discovery logging |
| [Git Tools](git-tools.md) | 2 tools | Git session management, commit workflows |
| [Specification Tools](specification-tools.md) | 10 tools | Entity hierarchy management, validation, bulk operations |
| [Template Tools](template-tools.md) | 6 tools | Task/sprint template management and instantiation |
| [Document Tools](document-tools.md) | 5 tools | Document management with approval workflows |

**Total: 35 tools** providing comprehensive task and project management capabilities.

## 🚀 Quick Start

### Basic Tool Usage Pattern

All MCP tools follow a consistent pattern:

```python
# Call pattern
mcp__claude-tasks__tool_name
  - parameter1: value1
  - parameter2: value2

# Example
mcp__claude-tasks__task_create
  - title: "Implement feature X"
  - priority: "high"
  - description: "Complete implementation of feature X"
```

### Common Return Format

All tools return a standardized response:

```python
{
    "status": "success" | "error",
    "message": "Human-readable message",
    # ... additional data fields
}
```

## 📋 Quick Reference Table

### System Tools (3)
- `system_set_project_directory` - Set working project directory
- `system_health_check` - Check system status and file existence
- `workflow_load_context` - Load project overview and context

### Task Tools (6)
- `task_create` - Create new task
- `task_update` - Update task fields (status, priority, notes, dependencies)
- `task_delete` - Delete tasks with cleanup
- `get_next_task_full` - Get optimal next task with full context
- `task_get` - Retrieve single task by ID
- `task_search` - Search tasks with filters

### Sprint Tools (5)
- `sprint_get_current` - Get active sprint with context
- `sprint_update_strategic_context` - Update sprint objectives and themes
- `sprint_add_task` - Add task to sprint
- `sprint_remove_task` - Remove task from sprint
- `sprint_update` - Update sprint fields

### Journal Tools (3)
- `journal_create_session` - Record work session
- `journal_get_recent` - Get recent sessions
- `journal_search` - Search journal entries

### Git Tools (2)
- `session_commit_start` - Start Git session branch
- `session_list_history` - List session history with file details

### Specification Tools (10)
- `specification_create_entity` - Create entity with display ID
- `specification_update_entity` - Update existing entity
- `specification_list_entities` - List with hierarchy control
- `specification_get_entity_children` - Get direct children
- `specification_delete_entity` - Delete with cascade option
- `specification_get_entities_bulk` - Get multiple entities
- `specification_get_entity_subtree` - Get entity tree
- `specification_register_project` - Register project in system
- `specification_get_machine_id` - Get current machine ID
- `specification_set_machine_id` - Set machine ID

### Template Tools (6)
- `template_list` - List task templates by scope
- `sprint_template_list` - List sprint templates by scope
- `template_get` - Get template definition
- `sprint_template_get` - Get sprint template definition
- `task_create_from_template` - Instantiate task from template
- `sprint_create_from_template` - Instantiate sprint from template

### Document Tools (5)
- `document_create` - Create document with hierarchy
- `document_update` - Update document fields
- `document_query` - Search/filter documents
- `document_get` - Get single document
- `document_delete` - Delete document

## 🎯 Common Usage Patterns

### Task Creation Workflow
```python
# 1. Create task
result = mcp__claude-tasks__task_create
  - title: "New feature"
  - priority: "high"

# 2. Add to sprint
mcp__claude-tasks__sprint_add_task
  - sprint_id: "SPRINT-001"
  - task_id: result["task"]["id"]

# 3. Update status
mcp__claude-tasks__task_update
  - task_id: result["task"]["id"]
  - status: "in_progress"
```

### Session Tracking Workflow
```python
# 1. Start Git session
mcp__claude-tasks__session_commit_start
  - task_id: "TASK-001"
  - message: "Starting feature work"

# 2. Work on task...

# 3. Record session
mcp__claude-tasks__journal_create_session
  - session_type: "development"
  - duration_minutes: 120
  - tasks_worked: "TASK-001"
  - key_achievements: "Implemented core feature"
```

### Entity Hierarchy Creation
```python
# 1. Create root entity
mcp__claude-tasks__specification_create_entity
  - entity_name: "User Module"
  - entity_type: "module"
  - display_id: "user_module"

# 2. Create child entity
mcp__claude-tasks__specification_create_entity
  - entity_name: "Authentication"
  - entity_type: "feature"
  - display_id: "auth"
  - parent_display_id: "user_module"
```

## 📖 Parameter Conventions

### Common Parameters Across Tools

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | required | Human-readable title |
| `description` | string | "" | Detailed description |
| `priority` | string | "medium" | One of: low, medium, high, critical |
| `status` | string | "pending" | One of: pending, in_progress, completed, blocked |
| `limit` | string | varies | Maximum results to return |
| `query` | string | "" | Search query text |

### Priority Values
- `critical` - Urgent, blocking work
- `high` - Important, should be done soon
- `medium` - Normal priority
- `low` - Nice to have

### Status Values
- `pending` - Not started
- `in_progress` - Currently working
- `completed` - Finished
- `blocked` - Waiting on dependencies

## 🔧 Return Format Standards

### Success Response
```python
{
    "status": "success",
    "message": "Operation completed",
    # Data fields vary by tool
    "task": {...},      # For task operations
    "sprint": {...},    # For sprint operations
    "session": {...}    # For journal operations
}
```

### Error Response
```python
{
    "status": "error",
    "error": "Error description",
    "details": "Additional context"
}
```

## 📚 Detailed Documentation

For complete documentation on each tool including parameters, return values, and usage examples, see the category-specific documentation:

- **[System Tools](system-tools.md)** - Project setup and health monitoring
- **[Task Tools](task-tools.md)** - Task lifecycle management
- **[Sprint Tools](sprint-tools.md)** - Sprint planning and execution
- **[Journal Tools](journal-tools.md)** - Work session tracking
- **[Git Tools](git-tools.md)** - Version control workflows
- **[Specification Tools](specification-tools.md)** - Entity hierarchy management
- **[Template Tools](template-tools.md)** - Reusable task/sprint templates
- **[Document Tools](document-tools.md)** - Documentation management

## 🚨 Important Notes

### Project Initialization Required
Most tools require a project directory to be set. Use `system_set_project_directory` first:

```python
mcp__claude-tasks__system_set_project_directory
  - project_dir: "/path/to/project"
```

### File-Based Operations
All MCP tools operate on local JSON files in `.claude-tasks/data/`. Changes are:
- Immediately visible to all tools
- Automatically synced to database by file monitor
- Atomic (file locking prevents conflicts)

### Tool Naming Convention
All tools follow the pattern: `mcp__claude-tasks__<category>_<action>`

## 💡 Best Practices

1. **Always check tool responses** - Verify `status: "success"` before proceeding
2. **Use appropriate priorities** - Reserve `critical` for truly urgent work
3. **Track sessions** - Record work in journal for better project visibility
4. **Follow workflows** - Use Git session tools for proper version control
5. **Leverage templates** - Create reusable templates for common task patterns

## 🔗 Related Documentation

- **Server Architecture**: `/mcp-server-dev/CLAUDE.md`
- **Bidirectional Sync**: `/mcp-server-dev/BIDIRECTIONAL_SYNC_IMPLEMENTATION.md`
- **Database Schema**: `/docs/database/SCHEMA_REFERENCE.md`
- **Main System Docs**: `/task-sprint-system/CLAUDE.md`
