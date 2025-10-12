# Journal Tools (3 tools)

*Session tracking, work history, and discovery logging*

## Overview

Journal tools track work sessions, achievements, and discoveries. Essential for progress tracking and documentation.

## Tools

### 1. journal_create_session

**Purpose**: Record a work session with achievements and discoveries.

**Parameters**:
- `session_type` (string, required): Session type (e.g., "development", "planning", "debugging")
- `duration_minutes` (float, required): Session duration in minutes
- `tasks_worked` (string, required): Tasks worked on (comma-separated IDs)
- `discoveries` (string, optional): Key discoveries made
- `key_achievements` (string, optional): Main accomplishments
- `sprint_progress_impact` (string, optional): Impact on sprint progress

**Returns**:
```python
{
    "status": "success",
    "session": {
        "id": "SESSION-20251007-201530",
        "session_type": "development",
        "duration_minutes": 120.0,
        "tasks_worked": "TASK-2025-001,TASK-2025-002",
        "discoveries": "Found performance optimization opportunity",
        "key_achievements": "Completed authentication flow",
        "sprint_progress_impact": "Sprint 50% complete",
        "created_at": "2025-10-07T20:15:30.123456Z"
    },
    "message": "Journal session SESSION-20251007-201530 created"
}
```

**Usage Example**:
```python
mcp__claude-tasks__journal_create_session
  - session_type: "development"
  - duration_minutes: 180
  - tasks_worked: "TASK-2025-001"
  - key_achievements: "Implemented OAuth integration with tests"
  - discoveries: "Discovered better error handling pattern"
```

**Use Cases**: Session logging, progress tracking, knowledge capture

---

### 2. journal_get_recent

**Purpose**: Get recent work sessions.

**Parameters**:
- `limit` (string, optional): Maximum sessions to return (default: "5")

**Returns**:
```python
{
    "status": "success",
    "recent_sessions": [
        {
            "id": "SESSION-20251007-201530",
            "session_type": "development",
            "duration_minutes": 120.0,
            "tasks_worked": "TASK-2025-001",
            "key_achievements": "...",
            "created_at": "2025-10-07T20:15:30Z"
        }
        // ... more sessions
    ],
    "total_sessions": 25
}
```

**Usage**: `mcp__claude-tasks__journal_get_recent --limit 10`

**Use Cases**: Recent work review, progress summary, context loading

---

### 3. journal_search

**Purpose**: Search journal entries for specific work or patterns.

**Parameters**:
- `query` (string, required): Search text
- `session_type` (string, optional): Filter by session type

**Returns**:
```python
{
    "status": "success",
    "matching_sessions": [...],
    "query": "authentication",
    "total_matches": 5
}
```

**Usage Example**:
```python
# Search all sessions
mcp__claude-tasks__journal_search
  - query: "authentication"

# Search specific type
mcp__claude-tasks__journal_search
  - query: "bug fix"
  - session_type: "debugging"
```

**Use Cases**: Finding past work, pattern analysis, documentation research

## Common Workflows

### Session Recording
```python
# After completing work
mcp__claude-tasks__journal_create_session
  - session_type: "development"
  - duration_minutes: 240
  - tasks_worked: "TASK-2025-001,TASK-2025-002"
  - key_achievements: "Completed features X and Y"
  - discoveries: "Found optimization for Z"
```

### Progress Review
```python
# Get recent work
recent = mcp__claude-tasks__journal_get_recent
  - limit: "10"

# Search specific topic
results = mcp__claude-tasks__journal_search
  - query: "authentication"
```
