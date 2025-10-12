# Git Tools (2 tools)

*Git session management and commit workflows*

## Overview

Git tools manage version control workflows, creating session branches and tracking commit history.

## Tools

### 1. session_commit_start

**Purpose**: Start a Git session for task work - creates session branch and initial commit.

**Parameters**:
- `task_id` (string, required): Task ID for the session
- `message` (string, optional): Custom commit message
- `force_clean` (bool, optional): Proceed with uncommitted changes (default: false)
- `include_context` (bool, optional): Include branch context in message (default: false)

**Returns**:
```python
{
    "status": "success",
    "session_started": {
        "task_id": "TASK-2025-001",
        "session_branch": "session/TASK-2025-001-20251007201530",
        "timestamp": "20251007201530",
        "previous_branch": "main",
        "commit_message": "SESSION_START: TASK-2025-001 - Starting work session",
        "commit_hash": "a1b2c3d4"
    }
}
```

**Usage Example**:
```python
# Basic session start
mcp__claude-tasks__session_commit_start
  - task_id: "TASK-2025-001"

# With custom message and context
mcp__claude-tasks__session_commit_start
  - task_id: "TASK-2025-001"
  - message: "Implementing OAuth integration"
  - include_context: true
```

**Use Cases**: Starting focused work, isolating changes, tracking sessions

**Notes**:
- Creates branch: `session/TASK-ID-TIMESTAMP`
- Fails if working directory dirty (unless force_clean=true)
- Creates empty commit if no staged changes

---

### 2. session_list_history

**Purpose**: List Git session history with intelligent file summarization.

**Parameters**:
- `limit` (int, optional): Maximum commits to show (default: 20)
- `task_filter` (string, optional): Filter by task ID
- `file_detail_level` (string, optional): File detail level (default: "summary")
  - `none`: No file information
  - `summary`: First 10 files with directory grouping
  - `full`: All files
- `include_context` (bool, optional): Include timestamp/author (default: false)

**Returns**:
```python
{
    "status": "success",
    "session_history": {
        "sessions": [
            {
                "commit_hash": "a1b2c3d4",
                "message": "SESSION_START: TASK-2025-001 - ...",
                "task_id": "TASK-2025-001",
                "is_session": true,
                "files": [
                    {"status": "M", "file": "src/auth.py"},
                    {"status": "A", "file": "tests/test_auth.py"}
                ],
                "timestamp": "2025-10-07 20:15:30 +0000",
                "author": "Developer Name"
            }
        ],
        "total_shown": 5,
        "limit": 20,
        "task_filter": "",
        "file_detail_level": "summary"
    }
}
```

**Usage Example**:
```python
# Basic history
mcp__claude-tasks__session_list_history

# Filter by task
mcp__claude-tasks__session_list_history
  - task_filter: "TASK-2025-001"
  - limit: 10

# Full file details
mcp__claude-tasks__session_list_history
  - file_detail_level: "full"
  - include_context: true

# Minimal (no files)
mcp__claude-tasks__session_list_history
  - file_detail_level: "none"
  - limit: 5
```

**Use Cases**: Session review, work tracking, change analysis

**Notes**:
- Intelligently groups files by directory when > 10 files
- Filters for session commits (contains "SESSION_START:")
- Fast operation (uses git log)

## Common Workflows

### Session Workflow
```python
# 1. Start session
session = mcp__claude-tasks__session_commit_start
  - task_id: "TASK-2025-001"

# 2. Work on task...

# 3. Review session history
history = mcp__claude-tasks__session_list_history
  - task_filter: "TASK-2025-001"
  - file_detail_level: "summary"

# 4. Record in journal
mcp__claude-tasks__journal_create_session
  - session_type: "development"
  - duration_minutes: 120
  - tasks_worked: "TASK-2025-001"
```
