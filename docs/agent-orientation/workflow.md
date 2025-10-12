# Agent Workflow Patterns

*Detailed step-by-step workflows for common agent operations*

## Task Workflow

### Create → Get Next → Update → Complete

#### Step 1: Create a Task

```python
# Create new task
result = mcp__claude-tasks__task_create(
    title="Implement user authentication",
    description="Add OAuth2 login with Google and GitHub providers",
    priority="high"
)

# Expected response
{
    "status": "success",
    "task": {
        "id": "TASK-2025-042",
        "title": "Implement user authentication",
        "description": "Add OAuth2 login with Google and GitHub providers",
        "priority": "high",
        "status": "pending",
        "created_at": "2025-10-07T20:15:30Z",
        "updated_at": "2025-10-07T20:15:30Z"
    },
    "message": "Task TASK-2025-042 created successfully"
}
```

#### Step 2: Get Next Recommended Task

```python
# Get task recommendations based on priority, dependencies, and sprint context
result = mcp__claude-tasks__get_next_tasks(
    limit=5,
    criteria="priority,dependencies,status"
)

# Expected response
{
    "status": "success",
    "recommended_tasks": [
        {
            "id": "TASK-2025-042",
            "title": "Implement user authentication",
            "priority": "high",
            "status": "pending",
            "recommendation_reason": "High priority, no blockers"
        },
        # ... more tasks
    ],
    "count": 5
}
```

#### Step 3: Update Task Status

```python
# Mark task as in progress
result = mcp__claude-tasks__task_update(
    task_id="TASK-2025-042",
    status="in_progress"
)

# Expected response
{
    "status": "success",
    "task": {
        "id": "TASK-2025-042",
        "status": "in_progress",
        "updated_at": "2025-10-07T20:16:45Z"
        # ... other fields
    }
}
```

#### Step 4: Complete Task

```python
# Mark task as completed
result = mcp__claude-tasks__task_update(
    task_id="TASK-2025-042",
    status="completed"
)

# Expected response
{
    "status": "success",
    "task": {
        "id": "TASK-2025-042",
        "status": "completed",
        "updated_at": "2025-10-07T20:45:10Z"
        # ... other fields
    }
}
```

### Error Recovery: Task Not Found

```python
# Try to update task
result = mcp__claude-tasks__task_update(
    task_id="TASK-2025-999",
    status="completed"
)

# Error response
{
    "status": "error",
    "error": "Task TASK-2025-999 not found"
}

# Recovery: Search for correct task
search_result = mcp__claude-tasks__task_search(
    query="authentication",
    status="in_progress"
)

# Use found task ID
if search_result.get("tasks"):
    correct_task_id = search_result["tasks"][0]["id"]
    result = mcp__claude-tasks__task_update(
        task_id=correct_task_id,
        status="completed"
    )
```

## Sprint Workflow

### Get Current → Add Tasks → Track Progress

#### Step 1: Get Current Sprint

```python
# Get active sprint with task information
result = mcp__claude-tasks__sprint_get_current()

# Expected response
{
    "status": "success",
    "sprint": {
        "id": "SPRINT-2025-Q4-001",
        "title": "Authentication & User Management",
        "status": "active",
        "primary_objective": "Implement complete user authentication system",
        "task_summary": {
            "total": 12,
            "pending": 5,
            "in_progress": 3,
            "completed": 4,
            "blocked": 0
        },
        "start_date": "2025-10-01",
        "end_date": "2025-10-14"
    }
}
```

#### Step 2: Add Task to Sprint

```python
# Add newly created task to active sprint
result = mcp__claude-tasks__sprint_add_task(
    sprint_id="SPRINT-2025-Q4-001",
    task_id="TASK-2025-042"
)

# Expected response
{
    "status": "success",
    "sprint": {
        "id": "SPRINT-2025-Q4-001",
        "task_ids": [
            "TASK-2025-038",
            "TASK-2025-039",
            # ... existing tasks
            "TASK-2025-042"  # newly added
        ]
    },
    "message": "Task TASK-2025-042 added to sprint SPRINT-2025-Q4-001"
}
```

#### Step 3: Check Sprint Progress

```python
# Get updated sprint status
result = mcp__claude-tasks__sprint_get_current()

# Calculate progress
sprint = result.get("sprint", {})
summary = sprint.get("task_summary", {})
completion_rate = (summary.get("completed", 0) / summary.get("total", 1)) * 100

print(f"Sprint completion: {completion_rate:.1f}%")
print(f"Tasks in progress: {summary.get('in_progress', 0)}")
print(f"Tasks blocked: {summary.get('blocked', 0)}")
```

#### Step 4: Check for Blockers

```python
# Check if anything is blocking sprint completion
result = mcp__claude-tasks__sprint_check_blockers(
    sprint_id="SPRINT-2025-Q4-001",
    include_validation_blockers=True,
    suggest_resolution_actions=True
)

# Expected response
{
    "status": "success",
    "blockers": [
        {
            "task_id": "TASK-2025-040",
            "title": "Setup OAuth providers",
            "blocker_type": "dependency",
            "blocking_tasks": ["TASK-2025-042"],
            "resolution_suggestion": "Complete TASK-2025-040 first"
        }
    ],
    "blocker_count": 1
}
```

### Error Recovery: Sprint Not Found

```python
# Try to add task to non-existent sprint
result = mcp__claude-tasks__sprint_add_task(
    sprint_id="SPRINT-2025-Q4-999",
    task_id="TASK-2025-042"
)

# Error response
{
    "status": "error",
    "error": "Sprint SPRINT-2025-Q4-999 not found"
}

# Recovery: Get current active sprint
current_sprint = mcp__claude-tasks__sprint_get_current()
if current_sprint.get("sprint"):
    sprint_id = current_sprint["sprint"]["id"]
    # Retry with correct sprint ID
```

## Journal Workflow

### Start Session → Record Work → Search History

#### Step 1: Start Work Session (Implicit)

```python
# Record session start time
session_start = datetime.now()
tasks_worked = []
```

#### Step 2: Track Work on Tasks

```python
# As you work, track changes
tasks_worked.append({
    "task_id": "TASK-2025-042",
    "status_change": "started",
    "work_summary": "Began implementing OAuth2 flow"
})

# Continue working...
tasks_worked.append({
    "task_id": "TASK-2025-042",
    "status_change": "completed",
    "work_summary": "Completed OAuth2 implementation with Google and GitHub"
})
```

#### Step 3: Create Session Entry

```python
# Calculate session duration
session_end = datetime.now()
duration = (session_end - session_start).total_seconds() / 60

# Create journal entry
result = mcp__claude-tasks__journal_create_session(
    session_type="carry-on",
    duration_minutes=duration,
    tasks_worked=json.dumps(tasks_worked),
    key_achievements=[
        "Implemented OAuth2 authentication",
        "Added Google and GitHub providers",
        "Tests passing for auth flow"
    ],
    discoveries=[
        "Need to add refresh token handling",
        "Session management needs improvement",
        "Consider rate limiting for auth endpoints"
    ],
    sprint_progress_impact="Completed 1 of 5 authentication tasks"
)

# Expected response
{
    "status": "success",
    "session": {
        "id": "SESSION-2025-10-07T20:45:10Z",
        "session_type": "carry-on",
        "duration_minutes": 45,
        "tasks_worked": [...],
        "key_achievements": [...],
        "discoveries": [...],
        "created_at": "2025-10-07T20:45:10Z"
    }
}
```

#### Step 4: Search Session History

```python
# Find previous work on authentication
result = mcp__claude-tasks__journal_search(
    query="authentication",
    session_type="carry-on"
)

# Expected response
{
    "status": "success",
    "sessions": [
        {
            "id": "SESSION-2025-10-07T20:45:10Z",
            "session_type": "carry-on",
            "tasks_worked": [...],
            "key_achievements": [...],
            "match_reason": "Found 'authentication' in achievements and discoveries"
        },
        # ... more sessions
    ],
    "count": 3
}
```

#### Step 5: Get Recent Work

```python
# Review last 5 sessions
result = mcp__claude-tasks__journal_get_recent(limit=5)

# Expected response
{
    "status": "success",
    "sessions": [
        {
            "id": "SESSION-2025-10-07T20:45:10Z",
            "session_type": "carry-on",
            "duration_minutes": 45,
            "tasks_count": 1,
            "achievements_count": 3
        },
        # ... 4 more recent sessions
    ],
    "count": 5
}
```

### Valid Status Changes

```python
# Valid status_change values for tasks_worked
valid_status_changes = [
    "started",      # Task work began
    "completed",    # Task finished
    "blocked",      # Hit blocker
    "progressed",   # Made progress but not complete
    "abandoned"     # Stopped working on task
]
```

## Specification Workflow

### Create → Query → Update → Validate

#### Step 1: Create Requirements Entity

```python
# Create top-level module
result = mcp__claude-tasks__requirements_create_entity(
    entity_name="Authentication System",
    entity_type="module",
    display_id="auth_system",
    description="Complete user authentication and authorization module",
    requirements=[
        "Support OAuth2 authentication",
        "Support multiple providers (Google, GitHub)",
        "Handle session management",
        "Implement refresh token flow"
    ],
    constraints=[
        "Must use industry-standard protocols",
        "Session tokens expire after 1 hour",
        "Refresh tokens valid for 30 days"
    ]
)

# Expected response
{
    "status": "success",
    "entity": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "entity_name": "Authentication System",
        "entity_type": "module",
        "display_id": "auth_system",
        "requirements": [...],
        "constraints": [...],
        "created_at": "2025-10-07T20:50:00Z"
    }
}
```

#### Step 2: Create Child Entity

```python
# Create feature under module
result = mcp__claude-tasks__requirements_create_entity(
    entity_name="OAuth2 Login",
    entity_type="feature",
    display_id="oauth2_login",
    parent_display_id="auth_system",  # Links to parent
    description="OAuth2 authentication flow implementation",
    requirements=[
        "Redirect to provider login page",
        "Handle callback with authorization code",
        "Exchange code for access token",
        "Create user session"
    ]
)
```

#### Step 3: Query Entity Hierarchy

```python
# Get all entities with hierarchy
result = mcp__claude-tasks__requirements_list_entities(
    depth=-1,  # All levels
    include_unapproved=False,
    verbosity="full"
)

# Expected response
{
    "status": "success",
    "entities": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "entity_name": "Authentication System",
            "entity_type": "module",
            "display_id": "auth_system",
            "children": [
                {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "entity_name": "OAuth2 Login",
                    "entity_type": "feature",
                    "display_id": "oauth2_login",
                    "parent_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }
    ]
}
```

#### Step 4: Update Entity

```python
# Update entity with implementation status
result = mcp__claude-tasks__requirements_update_entity(
    entity_id="660e8400-e29b-41d4-a716-446655440001",
    description="OAuth2 authentication flow implementation - COMPLETED"
)

# Expected response
{
    "status": "success",
    "entity": {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "description": "OAuth2 authentication flow implementation - COMPLETED",
        "updated_at": "2025-10-07T21:00:00Z"
    }
}
```

#### Step 5: Get Entity Subtree

```python
# Get specific entity with all descendants
result = mcp__claude-tasks__requirements_get_entity_subtree(
    parent_id="550e8400-e29b-41d4-a716-446655440000",
    depth=-1,  # All descendants
    verbosity="minimal"
)

# Expected response
{
    "status": "success",
    "subtree": {
        "entity": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "entity_name": "Authentication System",
            "display_id": "auth_system"
        },
        "children": [...]
    }
}
```

## Document Workflow

### Create → Organize → Update → Reference

#### Step 1: Create Document

```python
# Create new document
result = mcp__claude-tasks__document_create(
    document_title="API Authentication Guide",
    document_type="guide",
    description="Complete guide for implementing API authentication",
    scope="project",
    priority="high",
    sections=[
        {
            "title": "Overview",
            "content": "This guide explains how to implement API authentication..."
        },
        {
            "title": "OAuth2 Flow",
            "content": "The OAuth2 flow consists of..."
        }
    ]
)

# Expected response
{
    "status": "success",
    "document": {
        "id": "770e8400-e29b-41d4-a716-446655440000",
        "document_title": "API Authentication Guide",
        "document_type": "guide",
        "document_path": "guides/api-authentication-guide",
        "status": "draft",
        "sections": [...],
        "created_at": "2025-10-07T21:10:00Z"
    }
}
```

#### Step 2: Create Child Document

```python
# Create document under parent
result = mcp__claude-tasks__document_create(
    document_title="OAuth2 Implementation Details",
    document_type="guide",
    parent_id="770e8400-e29b-41d4-a716-446655440000",
    sections=[
        {
            "title": "Google Provider Setup",
            "content": "..."
        }
    ]
)
```

#### Step 3: Update Document Content

```python
# Add more sections
result = mcp__claude-tasks__document_update_content(
    document_path="guides/api-authentication-guide",
    sections=[
        {
            "title": "Overview",
            "content": "This guide explains how to implement API authentication..."
        },
        {
            "title": "OAuth2 Flow",
            "content": "The OAuth2 flow consists of..."
        },
        {
            "title": "Session Management",
            "content": "After authentication, sessions are managed..."
        },
        {
            "title": "Error Handling",
            "content": "Common errors and how to handle them..."
        }
    ],
    status="review"  # Update status
)

# Expected response
{
    "status": "success",
    "document": {
        "document_path": "guides/api-authentication-guide",
        "status": "review",
        "sections_count": 4,
        "updated_at": "2025-10-07T21:15:00Z"
    }
}
```

#### Step 4: Add Cross-Reference

```python
# Link document to requirements entity
result = mcp__claude-tasks__document_add_reference(
    source_type="document",
    source_path="guides/api-authentication-guide",
    target_type="requirements",
    target_path="auth_system/oauth2_login",
    reference_type="documents",
    description="Implementation guide for OAuth2 login feature"
)

# Expected response
{
    "status": "success",
    "reference": {
        "source_type": "document",
        "source_path": "guides/api-authentication-guide",
        "target_type": "requirements",
        "target_path": "auth_system/oauth2_login",
        "reference_type": "documents"
    }
}
```

#### Step 5: Mark as Implemented

```python
# Mark document as implemented after completing work
result = mcp__claude-tasks__document_set_implemented_status(
    document_path="guides/api-authentication-guide",
    implemented=True
)

# Expected response
{
    "status": "success",
    "document": {
        "document_path": "guides/api-authentication-guide",
        "implemented": True,
        "updated_at": "2025-10-07T21:20:00Z"
    }
}
```

## Git Session Workflow

### Start → Commit → List History

#### Step 1: Start Git Session

```python
# Start session for task work
result = mcp__claude-tasks__session_commit_start(
    task_id="TASK-2025-042",
    message="Begin OAuth2 implementation",
    include_context=False
)

# Expected response
{
    "status": "success",
    "session": {
        "branch": "session/task-2025-042",
        "commit": "abc123def456",
        "task_id": "TASK-2025-042"
    }
}
```

#### Step 2: List Session History

```python
# Get work history with file details
result = mcp__claude-tasks__session_list_history(
    limit=10,
    file_detail_level="summary",  # or "full" or "none"
    include_context=False
)

# Expected response
{
    "status": "success",
    "sessions": [
        {
            "commit": "abc123def456",
            "task_id": "TASK-2025-042",
            "message": "Begin OAuth2 implementation",
            "timestamp": "2025-10-07T21:25:00Z",
            "files_summary": "3 files changed, 15 directories affected"
        }
    ]
}
```

## Error Recovery Patterns

### Pattern 1: Retry with Correct Parameters

```python
# First attempt fails
result = mcp__claude-tasks__task_create(
    title="New task",
    priority="urgent"  # Invalid
)

# Error: Invalid priority
if result.get("status") == "error":
    # Retry with valid priority
    result = mcp__claude-tasks__task_create(
        title="New task",
        priority="high"  # Valid
    )
```

### Pattern 2: Search and Retry

```python
# Update fails - task not found
result = mcp__claude-tasks__task_update(
    task_id="TASK-2025-999",
    status="completed"
)

if result.get("status") == "error" and "not found" in result.get("error", ""):
    # Search for correct task
    search = mcp__claude-tasks__task_search(query="...")
    if search.get("tasks"):
        task_id = search["tasks"][0]["id"]
        # Retry with correct ID
        result = mcp__claude-tasks__task_update(
            task_id=task_id,
            status="completed"
        )
```

### Pattern 3: Validate Before Operation

```python
# Check if task exists before updating
task = mcp__claude-tasks__task_get(task_id="TASK-2025-042")

if task.get("status") == "success":
    # Task exists, safe to update
    result = mcp__claude-tasks__task_update(
        task_id="TASK-2025-042",
        status="completed"
    )
else:
    # Task doesn't exist, handle accordingly
    print(f"Task not found: {task.get('error')}")
```

---

*For more patterns and best practices, see best-practices.md*
