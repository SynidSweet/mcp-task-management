# System Tools (3 tools)

*Project initialization, health monitoring, and context management*

## Overview

System tools provide foundational operations for project setup, health monitoring, and context loading. These tools should be used first to initialize the MCP server for a specific project.

## Tools

### 1. system_set_project_directory

**Purpose**: Set the working project directory for all subsequent MCP operations.

**Parameters**:
- `project_dir` (string, required): Absolute path to project directory

**Returns**:
```python
{
    "status": "success",
    "project_path": "/path/to/project",
    "message": "Project directory set successfully"
}
```

**Usage Example**:
```python
mcp__claude-tasks__system_set_project_directory
  - project_dir: "/home/dev/my-project"
```

**Use Cases**:
- Initial project setup
- Switching between projects
- Correcting wrong project auto-detection

**Notes**:
- Must be called before other tools can work
- Creates `.claude-tasks/data/` structure if missing
- Validates that directory exists

---

### 2. system_health_check

**Purpose**: Check system status and verify data file existence.

**Parameters**: None

**Returns**:
```python
{
    "status": "success",
    "project_path": "/path/to/project",
    "data_files": {
        "tasks": {
            "path": "/path/to/tasks.json",
            "exists": true
        },
        "sprints": {
            "path": "/path/to/sprints.json",
            "exists": true
        },
        "backlog": {
            "path": "/path/to/backlog.json",
            "exists": true
        },
        "journal": {
            "path": "/path/to/journal.json",
            "exists": true
        }
    }
}
```

**Usage Example**:
```python
mcp__claude-tasks__system_health_check
```

**Use Cases**:
- Verify system is properly initialized
- Debug file access issues
- Confirm project structure
- Troubleshoot tool failures

**Notes**:
- Returns `status: "not_initialized"` if no project set
- Simple file existence check (no deep validation)
- Fast operation (< 10ms)

---

### 3. workflow_load_context

**Purpose**: Load comprehensive project context for agent workflows.

**Parameters**:
- `context_detail_level` (string, optional): Detail level ("standard" default)
- `include_session_history` (bool, optional): Include session data (true default)
- `include_sprint_details` (bool, optional): Include sprint context (true default)
- `include_system_state` (bool, optional): Include system info (true default)
- `include_task_selection` (bool, optional): Include task recommendations (true default)
- `max_response_size` (string, optional): Response size limit ("standard" default)

**Returns**:
```python
{
    "status": "success",
    "timestamp": "2025-10-07T20:15:30.123456",
    "project_overview": {
        "purpose": "MCP Task Management System",
        "status": "Simplified Architecture - Post-simplification"
    },
    "system_state": {
        "initialized": true,
        "project_path": "/path/to/project",
        "architecture": "Simplified - Function-based tools"
    },
    "note": "Simplified architecture - direct function-based implementation"
}
```

**Usage Example**:
```python
# Basic context load
mcp__claude-tasks__workflow_load_context

# Minimal context
mcp__claude-tasks__workflow_load_context
  - context_detail_level: "minimal"
  - include_session_history: false
  - include_sprint_details: false
```

**Use Cases**:
- Agent initialization (get project overview)
- Context switching (reload project state)
- Debugging (understand current system state)
- Documentation (capture project snapshot)

**Notes**:
- Simplified version provides basic project info
- Fast operation suitable for frequent calls
- Does not load full task/sprint data (use specific tools for that)
- Parameters currently have minimal effect (simplified implementation)

## Common Workflows

### Initial Setup Workflow
```python
# 1. Set project directory
result = mcp__claude-tasks__system_set_project_directory
  - project_dir: "/path/to/project"

# 2. Verify initialization
health = mcp__claude-tasks__system_health_check

# 3. Load context
context = mcp__claude-tasks__workflow_load_context
```

### Health Check Workflow
```python
# Quick health check
health = mcp__claude-tasks__system_health_check

if health["status"] != "success":
    # Reinitialize project
    mcp__claude-tasks__system_set_project_directory
      - project_dir: "/path/to/project"
```

## Error Handling

### Common Errors

**Project Not Initialized**:
```python
{
    "status": "error",
    "error": "No project directory set. Use system_set_project_directory first."
}
```
**Solution**: Call `system_set_project_directory` with valid path

**Invalid Project Path**:
```python
{
    "status": "error",
    "error": "Project directory does not exist: /invalid/path"
}
```
**Solution**: Verify path exists and is accessible

**File Access Error**:
```python
{
    "status": "error",
    "error": "Permission denied accessing data files"
}
```
**Solution**: Check file permissions in `.claude-tasks/data/`

## Performance Characteristics

| Tool | Typical Time | Notes |
|------|-------------|-------|
| system_set_project_directory | < 5ms | Creates directories if needed |
| system_health_check | < 10ms | Simple file checks |
| workflow_load_context | < 20ms | Simplified implementation |

## Related Tools

- **Task Tools**: Require project initialization
- **Sprint Tools**: Require project initialization
- **All Other Tools**: Depend on system tools for setup

## Best Practices

1. **Always initialize first** - Call `system_set_project_directory` before other tools
2. **Verify with health check** - Use health check after setup to confirm success
3. **Load context for agents** - Use workflow_load_context at agent startup
4. **Handle errors gracefully** - Check status field on all responses
5. **Cache project path** - Avoid repeated calls to system_set_project_directory

## Implementation Notes

- All system tools are fast, synchronous operations
- No database access required (file-based only)
- Minimal validation (trusts input paths)
- Simple error messages for quick debugging
