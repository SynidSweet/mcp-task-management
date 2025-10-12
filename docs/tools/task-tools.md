# Task Tools (6 tools)

*Complete task lifecycle management - create, read, update, delete, search*

## Overview

Task tools provide comprehensive CRUD operations for task management. All tools operate on the local `tasks.json` file with automatic database synchronization via file monitor.

## Tools

### 1. task_create

**Purpose**: Create a new task with basic metadata.

**Parameters**:
- `title` (string, required): Task title
- `description` (string, optional): Detailed description (default: "")
- `priority` (string, optional): Priority level (default: "medium")
  - Valid values: `low`, `medium`, `high`, `critical`

**Returns**:
```python
{
    "status": "success",
    "task": {
        "id": "TASK-2025-001",
        "title": "Implement feature X",
        "description": "Complete implementation...",
        "priority": "high",
        "status": "pending",
        "created_at": "2025-10-07T20:15:30.123456Z",
        "updated_at": "2025-10-07T20:15:30.123456Z"
    },
    "message": "Task TASK-2025-001 created successfully"
}
```

**Usage Example**:
```python
# Minimal task
mcp__claude-tasks__task_create
  - title: "Fix authentication bug"

# Full task
mcp__claude-tasks__task_create
  - title: "Implement user dashboard"
  - description: "Create dashboard with user stats and recent activity"
  - priority: "high"
```

**Use Cases**:
- Creating new work items
- Capturing bug reports
- Planning features
- Breaking down large work into tasks

**Notes**:
- Task ID auto-generated (format: `TASK-YYYY-NNN`)
- Initial status always "pending"
- No due dates or assignees (simplified structure)
- Timestamps in UTC ISO format

---

### 2. task_update

**Purpose**: Update task fields including status, priority, notes, and dependencies.

**Parameters**:
- `task_id` (string, required): Task ID to update
- `status` (string, optional): New status
  - Valid values: `pending`, `in_progress`, `completed`, `blocked`
- `priority` (string, optional): New priority
  - Valid values: `low`, `medium`, `high`, `critical`
- `notes` (string, optional): Additional notes
- `dependencies` (string, optional): Dependency specification
  - Format: `"blocked_by:TASK-001,TASK-002;blocks:TASK-003"`

**Returns**:
```python
{
    "status": "success",
    "task": {
        "id": "TASK-2025-001",
        "title": "...",
        "status": "in_progress",
        "priority": "critical",
        "notes": "Updated notes",
        "dependencies": {
            "blocked_by": ["TASK-001", "TASK-002"],
            "blocks": ["TASK-003"],
            "related": []
        },
        "updated_at": "2025-10-07T20:30:45.654321Z",
        "completed_at": "2025-10-07T21:00:00.000000Z"  // Only if status="completed"
    },
    "message": "Task TASK-2025-001 updated successfully"
}
```

**Usage Example**:
```python
# Update status
mcp__claude-tasks__task_update
  - task_id: "TASK-2025-001"
  - status: "in_progress"

# Update priority and add notes
mcp__claude-tasks__task_update
  - task_id: "TASK-2025-001"
  - priority: "critical"
  - notes: "Blocking production deployment"

# Add dependencies
mcp__claude-tasks__task_update
  - task_id: "TASK-2025-003"
  - dependencies: "blocked_by:TASK-2025-001,TASK-2025-002"
```

**Use Cases**:
- Marking tasks in progress
- Completing tasks
- Escalating priority
- Setting up task dependencies
- Adding progress notes

**Notes**:
- Only updates provided fields (partial update)
- Automatically sets `completed_at` when status changes to "completed"
- Dependencies support three types: `blocked_by`, `blocks`, `related`
- Invalid status/priority returns error

---

### 3. task_delete

**Purpose**: Delete one or more tasks with comprehensive cleanup.

**Parameters**:
- `task_ids` (string, required): Comma-separated task IDs

**Returns**:
```python
{
    "status": "success",
    "message": "Bulk deleted 2 tasks",
    "deleted_tasks": [
        {"id": "TASK-2025-001", "title": "Old task 1"},
        {"id": "TASK-2025-002", "title": "Old task 2"}
    ],
    "deleted_count": 2,
    "not_found": [],
    "cleanup_stats": {
        "dependency_cleanups": 3,
        "sprint_cleanups": 1
    },
    "warning": "Tasks permanently deleted - this action cannot be undone"
}
```

**Usage Example**:
```python
# Delete single task
mcp__claude-tasks__task_delete
  - task_ids: "TASK-2025-001"

# Delete multiple tasks
mcp__claude-tasks__task_delete
  - task_ids: "TASK-2025-001,TASK-2025-002,TASK-2025-003"
```

**Use Cases**:
- Removing obsolete tasks
- Cleaning up duplicates
- Bulk cleanup operations

**Notes**:
- **Permanent deletion** - no recovery possible
- Automatically removes task from sprints
- Cleans up dependencies in other tasks
- Returns list of tasks that weren't found
- Supports bulk operations (comma-separated IDs)

---

### 4. get_next_task_full

**Purpose**: Get the optimal next task to work on with complete execution context.

**Parameters**: None

**Returns**:
```python
{
    "status": "success",
    "pipeline_status": "ready",
    "selected_task": {
        "id": "TASK-2025-001",
        "title": "Implement authentication",
        "description": "...",
        "priority": "high",
        "complexity": "medium",
        "phase": "implementation",
        "estimated_hours": 8,
        "template_id": "feature-impl",
        "template_name": "Feature Implementation",
        "task_type": "feature",
        "tags": ["auth", "security"],
        "dependencies_completed": 2,
        "blocks_count": 3,
        "created_at": "2025-10-01T10:00:00Z",
        "sprint_id": "SPRINT-2025-Q4-01"
    },
    "sprint_context": {
        "has_active_sprint": true,
        "sprint_title": "Q4 Security Sprint",
        "primary_objective": "Implement core security features",
        "scope_boundaries": "Authentication and authorization only",
        "strategic_direction": "Security-first approach",
        "architectural_themes": "Zero-trust architecture"
    },
    "execution_readiness": {
        "dependency_status": "clear",
        "ready_tasks_count": 5,
        "pending_tasks_count": 12,
        "blocking_dependencies": [],
        "pipeline_position": "Task 1 of 5 ready"
    },
    "agent_guidance": {
        "mission": "Execute this scoped task exactly to its defined boundaries",
        "role": "Crucial pipeline component - other agents depend on your precise execution",
        "scope_adherence": "No scope creep - complete task as specified",
        "quality_focus": "Follow established patterns and documentation rules",
        "completion_workflow": "Use task completion workflow for validation and documentation"
    }
}
```

**Usage Example**:
```python
# Get next task
next_task = mcp__claude-tasks__get_next_task_full

if next_task["pipeline_status"] == "ready":
    task_id = next_task["selected_task"]["id"]
    # Work on task...
else:
    # No tasks ready (dependencies blocking)
    print(next_task["blocking_info"])
```

**Use Cases**:
- Agent task selection
- Autonomous workflow execution
- Task prioritization
- Dependency-aware scheduling

**Notes**:
- Returns highest priority task with cleared dependencies
- Includes full sprint context for alignment
- Provides agent guidance for proper execution
- Returns `pipeline_status: "standby"` if no tasks ready

---

### 5. task_get

**Purpose**: Retrieve a single task with full details by ID.

**Parameters**:
- `task_id` (string, required): Task ID to retrieve

**Returns**:
```python
{
    "status": "success",
    "task": {
        "id": "TASK-2025-001",
        "title": "Implement feature",
        "description": "Full description...",
        "priority": "high",
        "status": "in_progress",
        "dependencies": {
            "blocked_by": [],
            "blocks": ["TASK-2025-002"],
            "related": []
        },
        "sprint_id": "SPRINT-2025-Q4-01",
        "created_at": "2025-10-01T10:00:00Z",
        "updated_at": "2025-10-07T20:15:30Z"
    }
}
```

**Usage Example**:
```python
mcp__claude-tasks__task_get
  - task_id: "TASK-2025-001"
```

**Use Cases**:
- Getting task details
- Verifying task existence
- Checking task status
- Retrieving full task data

**Notes**:
- Returns error if task not found
- Includes all task fields
- Fast lookup by ID

---

### 6. task_search

**Purpose**: Search and filter tasks with comprehensive criteria.

**Parameters**:
- `query` (string, optional): Text search in title/description (default: "")
- `status` (string, optional): Filter by status (default: "")
- `priority` (string, optional): Filter by priority (default: "")
- `limit` (string, optional): Maximum results (default: "50")
- `sprint_id` (string, optional): Filter by sprint (default: "")
- `tags` (string, optional): Filter by tags (default: "")

**Returns**:
```python
{
    "status": "success",
    "tasks": [
        {
            "id": "TASK-2025-001",
            "title": "...",
            "status": "pending",
            "priority": "high",
            // ... full task data
        },
        // ... more tasks
    ],
    "total_matches": 12
}
```

**Usage Example**:
```python
# Search by text
mcp__claude-tasks__task_search
  - query: "authentication"

# Filter by status and priority
mcp__claude-tasks__task_search
  - status: "pending"
  - priority: "high"

# Find sprint tasks
mcp__claude-tasks__task_search
  - sprint_id: "SPRINT-2025-Q4-01"
  - limit: "10"

# Complex search
mcp__claude-tasks__task_search
  - query: "bug"
  - status: "pending"
  - priority: "critical"
  - limit: "20"
```

**Use Cases**:
- Finding tasks by keyword
- Listing pending work
- Sprint task review
- Priority-based filtering
- Text search in descriptions

**Notes**:
- All filters are optional (can combine)
- Query searches both title and description
- Case-insensitive text search
- Default limit prevents overwhelming results

## Common Workflows

### Task Creation and Assignment
```python
# 1. Create task
result = mcp__claude-tasks__task_create
  - title: "Implement feature X"
  - priority: "high"

task_id = result["task"]["id"]

# 2. Add to sprint
mcp__claude-tasks__sprint_add_task
  - sprint_id: "SPRINT-2025-Q4-01"
  - task_id: task_id

# 3. Start work
mcp__claude-tasks__task_update
  - task_id: task_id
  - status: "in_progress"
```

### Task Completion Workflow
```python
# 1. Complete work
mcp__claude-tasks__task_update
  - task_id: "TASK-2025-001"
  - status: "completed"
  - notes: "Implemented and tested"

# 2. Record session
mcp__claude-tasks__journal_create_session
  - session_type: "development"
  - duration_minutes: 180
  - tasks_worked: "TASK-2025-001"
  - key_achievements: "Feature complete with tests"
```

### Dependency Management
```python
# Set up task chain
mcp__claude-tasks__task_update
  - task_id: "TASK-2025-002"
  - dependencies: "blocked_by:TASK-2025-001"

mcp__claude-tasks__task_update
  - task_id: "TASK-2025-003"
  - dependencies: "blocked_by:TASK-2025-002"

# Get next ready task
next_task = mcp__claude-tasks__get_next_task_full
```

## Error Handling

**Invalid Priority**:
```python
{
    "status": "error",
    "error": "Invalid priority: urgent. Must be one of: low, medium, high, critical"
}
```

**Task Not Found**:
```python
{
    "status": "error",
    "error": "Task TASK-2025-999 not found"
}
```

**Invalid Dependency Format**:
```python
{
    "status": "error",
    "error": "Invalid dependency type: depends_on. Must be: blocks, blocked_by, related"
}
```

## Performance Characteristics

| Tool | Typical Time | Notes |
|------|-------------|-------|
| task_create | < 5ms | Simple file append |
| task_update | < 10ms | File read + write |
| task_delete | < 15ms | Multiple file updates |
| get_next_task_full | < 20ms | Complex filtering |
| task_get | < 5ms | Simple lookup |
| task_search | < 30ms | Depends on dataset size |

## Best Practices

1. **Use meaningful titles** - Clear, descriptive task names
2. **Set appropriate priorities** - Reserve "critical" for truly urgent work
3. **Track dependencies** - Use dependency management for task ordering
4. **Update status regularly** - Keep task status current
5. **Search before creating** - Avoid duplicate tasks
6. **Use get_next_task_full** - Let the system recommend optimal next task
