# Sprint Tools (5 tools)

*Sprint management, task assignment, and strategic context*

## Overview

Sprint tools manage sprints and their relationship to tasks. All operations are file-based on `sprints.json` with automatic database sync.

## Tools

### 1. sprint_get_current

**Purpose**: Get the currently active sprint with full context.

**Parameters**: None

**Returns**:
```python
{
    "status": "success",
    "current_sprint": {
        "id": "SPRINT-2025-Q4-01",
        "title": "Security Sprint",
        "status": "active",
        "description": "Implement core security features",
        "primary_objective": "Complete authentication system",
        "strategic_direction": "Security-first approach",
        "architectural_themes": "Zero-trust architecture",
        "tasks": ["TASK-2025-001", "TASK-2025-002"],
        "start_date": "2025-10-01",
        "end_date": "2025-10-14",
        "created_at": "2025-10-01T00:00:00Z",
        "updated_at": "2025-10-07T20:00:00Z"
    }
}
```

**Usage**: `mcp__claude-tasks__sprint_get_current`

**Use Cases**: Sprint context retrieval, agent initialization, progress tracking

---

### 2. sprint_update_strategic_context

**Purpose**: Update sprint strategic fields (objectives, themes, direction).

**Parameters**:
- `sprint_id` (string, required): Sprint ID
- `primary_objective` (string, optional): Main sprint goal
- `strategic_direction` (string, optional): Strategic approach
- `architectural_themes` (string, optional): Key architectural decisions
- `description` (string, optional): Sprint description

**Returns**: Updated sprint object

**Usage Example**:
```python
mcp__claude-tasks__sprint_update_strategic_context
  - sprint_id: "SPRINT-2025-Q4-01"
  - primary_objective: "Complete user authentication"
  - strategic_direction: "Security and usability balance"
```

---

### 3. sprint_add_task

**Purpose**: Add a task to a sprint.

**Parameters**:
- `sprint_id` (string, required): Sprint ID
- `task_id` (string, required): Task ID to add

**Returns**:
```python
{
    "status": "success",
    "message": "Task TASK-2025-001 added to sprint SPRINT-2025-Q4-01"
}
```

**Usage**: `mcp__claude-tasks__sprint_add_task`

**Notes**:
- Updates both sprint's task list and task's sprint_id
- Idempotent (safe to call multiple times)

---

### 4. sprint_remove_task

**Purpose**: Remove a task from a sprint.

**Parameters**:
- `sprint_id` (string, required): Sprint ID
- `task_id` (string, required): Task ID to remove

**Returns**: Success message

**Notes**: Cleans up both sprint and task references

---

### 5. sprint_update

**Purpose**: Comprehensive sprint update - all fields except status.

**Parameters**:
- `sprint_id` (string, required): Sprint ID
- `title` (string, optional): Sprint title
- `description` (string, optional): Description
- `start_date` (string, optional): Start date
- `end_date` (string, optional): End date
- `capacity` (string, optional): Team capacity
- `duration` (string, optional): Sprint duration
- `scope_in_scope` (string, optional): In-scope items
- `scope_out_of_scope` (string, optional): Out-of-scope items
- `validation_criteria` (string, optional): Success criteria
- `update_justification` (string, optional): Reason for update

**Returns**: Updated sprint object

**Usage Example**:
```python
mcp__claude-tasks__sprint_update
  - sprint_id: "SPRINT-2025-Q4-01"
  - title: "Security & Auth Sprint"
  - duration: "2 weeks"
  - validation_criteria: "All auth tests passing"
```

## Common Workflows

### Sprint Setup
```python
# Get current sprint
sprint = mcp__claude-tasks__sprint_get_current

# Update context
mcp__claude-tasks__sprint_update_strategic_context
  - sprint_id: sprint["current_sprint"]["id"]
  - primary_objective: "Launch authentication"
  - strategic_direction: "User security priority"
```

### Task Assignment
```python
# Create and assign task
result = mcp__claude-tasks__task_create
  - title: "Implement OAuth"
  - priority: "high"

mcp__claude-tasks__sprint_add_task
  - sprint_id: "SPRINT-2025-Q4-01"
  - task_id: result["task"]["id"]
```
