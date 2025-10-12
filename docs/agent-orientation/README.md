# Agent Orientation Guide

*Welcome to the MCP Task & Sprint Management System*

## What Is This System?

This is a **Model Context Protocol (MCP)** server that provides task and sprint management for AI agents working in Claude Code. The system enables structured project management through 84+ MCP tools for:

- **Tasks**: Create, update, track, and complete work items
- **Sprints**: Organize tasks into logical work groups
- **Journal**: Record work sessions and discoveries
- **Specifications**: Define requirements and system architecture
- **Documents**: Create and organize project documentation
- **Git Sessions**: Track work with Git integration

## Core Concepts

### 1. MCP Tools

All operations use MCP tools prefixed with `mcp__claude-tasks__`:

```python
# Example: Create a task
mcp__claude-tasks__task_create
  - title: "Implement user authentication"
  - priority: "high"
  - description: "Add OAuth2 login flow"
```

### 2. Project Isolation

Each project has its own task database in `.claude-tasks/data/`:
- `tasks.json` - All tasks
- `sprints.json` - Sprint information
- `journal.json` - Work session history
- `requirements.json` - Requirements entities
- `documents.json` - Project documentation

### 3. Bidirectional Sync

The system automatically synchronizes between:
- **Local files** - For MCP tool operations
- **Supabase database** - For UI access and cross-machine sync
- **File monitor** - Prevents sync loops with hash tracking

## Key Agent Workflows

### Task Workflow
```
1. Create task: mcp__claude-tasks__task_create
2. Get next task: mcp__claude-tasks__get_next_tasks
3. Update status: mcp__claude-tasks__task_update
4. Complete task: mcp__claude-tasks__task_update (status: "completed")
```

### Sprint Workflow
```
1. Get current: mcp__claude-tasks__sprint_get_current
2. Add tasks: mcp__claude-tasks__sprint_add_task
3. Track progress: Check task counts and status
```

### Journal Workflow
```
1. Start session: Record session start
2. Work on tasks: Track changes
3. Create session: mcp__claude-tasks__journal_create_session
4. Search history: mcp__claude-tasks__journal_search
```

### Specification Workflow
```
1. Create entity: mcp__claude-tasks__requirements_create_entity
2. Query entities: mcp__claude-tasks__requirements_list_entities
3. Update entity: mcp__claude-tasks__requirements_update_entity
4. Validate implementation: Check approval status
```

### Document Workflow
```
1. Create document: mcp__claude-tasks__document_create
2. Update content: mcp__claude-tasks__document_update_content
3. Add references: mcp__claude-tasks__document_add_reference
4. Mark as implemented: mcp__claude-tasks__document_set_implemented_status
```

## When to Use Which Tools

### System Initialization
- **Always first**: `system_set_project_directory(".")` or rely on auto-detection
- **Check health**: `system_health_check()` to verify setup

### Task Management
- **Creating work**: `task_create()` for new tasks
- **Finding work**: `get_next_tasks()` for recommendations
- **Updating progress**: `task_update()` for status changes
- **Searching**: `task_search()` when looking for specific tasks

### Sprint Management
- **Current sprint**: `sprint_get_current()` to understand context
- **Adding tasks**: `sprint_add_task()` to organize work
- **Checking blockers**: `sprint_check_blockers()` to find issues

### Work History
- **Session recording**: `journal_create_session()` after significant work
- **Recent work**: `journal_get_recent()` to review history
- **Search patterns**: `journal_search()` to find specific work

### Requirements
- **Define structure**: `requirements_create_entity()` for architecture
- **Query hierarchy**: `requirements_list_entities()` to understand system
- **Track implementation**: `requirements_update_entity()` for progress

### Documentation
- **Create guides**: `document_create()` for new documentation
- **Organize content**: Use parent_id hierarchy for structure
- **Track status**: Use implemented/validated flags

## Error Handling for Agents

### Common Errors

**Project Not Initialized**
```python
{
  "status": "error",
  "error": "No project directory set",
  "solution": "Use system_set_project_directory first"
}
```
**Action**: Call `system_set_project_directory(".")`

**Invalid Parameters**
```python
{
  "status": "error",
  "error": "Invalid priority: urgent. Must be one of: low, medium, high, critical"
}
```
**Action**: Use valid enum values

**Task Not Found**
```python
{
  "status": "error",
  "error": "Task TASK-2025-999 not found"
}
```
**Action**: Verify task ID exists with `task_search()`

### Error Recovery Pattern

```python
# 1. Try operation
result = mcp__claude-tasks__task_update(
    task_id="TASK-2025-001",
    status="completed"
)

# 2. Check result
if result.get("status") == "error":
    # 3. Handle error
    if "not found" in result.get("error", ""):
        # Search for correct task
        search_result = mcp__claude-tasks__task_search(query="...")
        # Use found task ID
    elif "Invalid" in result.get("error", ""):
        # Use correct parameters
        pass
```

## Best Practices for Agents

### 1. Always Check Project Initialization
```python
# First action in any workflow
health = mcp__claude-tasks__system_health_check()
if health.get("status") != "success":
    # Initialize project
    init = mcp__claude-tasks__system_set_project_directory(".")
```

### 2. Search Before Creating
```python
# Avoid duplicates
search_result = mcp__claude-tasks__task_search(
    query="authentication",
    status="pending"
)

if search_result.get("tasks"):
    # Task exists, update it
else:
    # Create new task
```

### 3. Use Sprints for Context
```python
# Understand current work focus
sprint = mcp__claude-tasks__sprint_get_current()
sprint_objective = sprint.get("sprint", {}).get("primary_objective", "")

# Align new tasks with sprint objective
```

### 4. Record Significant Work
```python
# After completing multiple tasks
journal_entry = mcp__claude-tasks__journal_create_session(
    session_type="carry-on",
    duration_minutes=45,
    tasks_worked=[
        {
            "task_id": "TASK-2025-001",
            "status_change": "completed",
            "work_summary": "Implemented OAuth2 flow"
        }
    ],
    key_achievements=["Authentication system working"],
    discoveries=["Need to add refresh token handling"]
)
```

### 5. Validate Before Complex Operations
```python
# Check task exists before updating
task = mcp__claude-tasks__task_get(task_id="TASK-2025-001")
if task.get("status") == "success":
    # Proceed with update
    pass
```

### 6. Keep Operations Simple
```python
# Good: Single responsibility
mcp__claude-tasks__task_create(title="Fix bug", priority="high")
mcp__claude-tasks__sprint_add_task(sprint_id="...", task_id="...")

# Avoid: Trying to do too much in one operation
# (The system doesn't support this)
```

### 7. Handle Both Success and Error
```python
result = mcp__claude-tasks__task_create(title="New task")

if result.get("status") == "success":
    task_id = result.get("task", {}).get("id")
    # Continue with task_id
else:
    error_msg = result.get("error")
    # Handle error appropriately
```

### 8. Use Appropriate Search Tools
```python
# For broad search (title, description, tags)
mcp__claude-tasks__task_search(query="authentication")

# For specific task
mcp__claude-tasks__task_get(task_id="TASK-2025-001")

# For work recommendations
mcp__claude-tasks__get_next_tasks(criteria="priority,dependencies")
```

## Common Agent Patterns

### Pattern 1: Autonomous Development Cycle
```python
# 1. Check sprint context
sprint = mcp__claude-tasks__sprint_get_current()

# 2. Get next task
tasks = mcp__claude-tasks__get_next_tasks(limit=5)
next_task = tasks.get("recommended_tasks", [])[0]

# 3. Work on task
# ... implementation work ...

# 4. Update status
mcp__claude-tasks__task_update(
    task_id=next_task["id"],
    status="in_progress"
)

# 5. Complete task
mcp__claude-tasks__task_update(
    task_id=next_task["id"],
    status="completed"
)

# 6. Record session
mcp__claude-tasks__journal_create_session(...)
```

### Pattern 2: Investigation and Analysis
```python
# 1. Search for related tasks
results = mcp__claude-tasks__task_search(
    query="performance",
    status="pending"
)

# 2. Analyze patterns
# ... investigation ...

# 3. Create new tasks based on findings
mcp__claude-tasks__task_create(
    title="Optimize database queries",
    priority="high",
    description="Found N+1 query patterns"
)
```

### Pattern 3: Documentation Creation
```python
# 1. Create document structure
doc = mcp__claude-tasks__document_create(
    document_title="API Reference",
    document_type="api_docs",
    description="REST API endpoint documentation"
)

# 2. Add sections with content
mcp__claude-tasks__document_update_content(
    document_path=doc.get("document", {}).get("document_path"),
    sections=[
        {
            "title": "Authentication",
            "content": "..."
        },
        {
            "title": "Endpoints",
            "content": "..."
        }
    ]
)

# 3. Link to requirements
mcp__claude-tasks__document_add_reference(
    source_type="document",
    source_path=doc_path,
    target_type="requirements",
    target_path="api/authentication",
    reference_type="implements"
)
```

## Quick Reference

### Essential Tools
- `system_set_project_directory(project_dir)` - Initialize
- `task_create(title, priority, description)` - New task
- `task_update(task_id, status, priority)` - Update task
- `get_next_tasks(limit, criteria)` - Get recommendations
- `sprint_get_current()` - Current sprint context
- `journal_create_session(...)` - Record work

### Valid Enums
- **Priority**: `low`, `medium`, `high`, `critical`
- **Status**: `pending`, `in_progress`, `completed`, `blocked`
- **Session Type**: `carry-on`, `investigation`, `documentation`
- **Status Change**: `started`, `completed`, `blocked`, `progressed`, `abandoned`

### File Locations
- Project data: `.claude-tasks/data/*.json`
- Logs: `.claude-tasks/logs/`
- Backups: `.claude-tasks/backups/`

## Next Steps

1. **Read workflow patterns**: See `workflow.md` for detailed workflows
2. **Review best practices**: See `best-practices.md` for development guidelines
3. **Check tool reference**: See `/docs/tools/` for complete tool documentation
4. **Test with examples**: Try the patterns above in your project

## Getting Help

- **System health**: `system_health_check()` for diagnostics
- **Recent work**: `journal_get_recent()` for context
- **Documentation**: Check `/docs/` directory for detailed guides
- **Architecture**: See `/docs/architecture/` for system design

---

*This guide is for AI agents. For human developers, see the main README.*
