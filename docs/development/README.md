# MCP Server Development Guide

*Last updated: 2025-10-07*

## Overview

This is a clean, simplified MCP server with modular architecture. The server provides 35+ MCP tools for task management, sprints, journals, specifications, and documents through a function-based tool registration pattern.

## Getting Started

### Prerequisites
- Python 3.12+
- FastMCP 2.10.5+
- Project directory with `.claude-tasks/` structure

### Quick Start
```bash
# Start the development server
cd /home/dev/.claude/task-sprint-system/mcp-server-dev
python server.py --project-dir "$(pwd)"

# Run comprehensive tests
python test_all_mcp_tools_direct.py
```

## Project Structure

```
mcp-server-dev/
├── server.py                 # FastMCP server with modular registration (143 lines)
├── core/
│   └── project_manager.py    # File operations and path management (157 lines)
├── tools/                    # 8 specialized tool modules (7-320 lines each)
│   ├── system_tools.py       # Project initialization, health checks (77 lines)
│   ├── task_tools.py         # Task CRUD operations (320 lines)
│   ├── sprint_tools.py       # Sprint management (197 lines)
│   ├── journal_tools.py      # Session tracking (116 lines)
│   ├── git_tools.py          # Git session operations (81 lines)
│   ├── specification_tools.py # Specification system (357 lines)
│   ├── template_tools.py     # Template management (234 lines)
│   └── document_tools.py     # Document operations (314 lines)
├── utils/
│   ├── helpers.py            # Shared utilities (113 lines)
│   └── validation_wrapper.py # Validation decorators (7 lines)
├── schemas/                  # JSON schema definitions
└── docs/                     # Documentation (you are here)
```

### Key Directories Explained

**`core/`**: Core infrastructure
- `project_manager.py`: Handles project paths, file operations, directory structure

**`tools/`**: MCP tool implementations organized by domain
- Each module registers 2-10 related MCP tools
- Function-based tool registration pattern
- Direct JSON file operations
- Shared utility functions

**`utils/`**: Shared helper functions
- `helpers.py`: Error handling, validation, JSON operations, ID generation
- `validation_wrapper.py`: Decorator for project initialization checks

## Development Workflow

### 1. Understanding the Architecture

The server uses a **modular, function-based architecture**:

```python
# server.py - Tool registration
from tools.task_tools import register_task_tools

class MCPServer:
    def __init__(self, project_dir):
        self.mcp = FastMCP("claude-tasks")
        self.project_manager = ProjectManager(project_dir)
        self._register_all_tools()

    def _register_all_tools(self):
        register_task_tools(self.mcp, self.project_manager)
        # ... more registrations
```

Each tool module follows this pattern:

```python
# tools/task_tools.py
def register_task_tools(mcp, project_manager: ProjectManager):
    @mcp.tool()
    async def task_create(title: str, priority: str = "medium"):
        """Create task - simplified (no TaskEngine)"""
        # Direct file operations
        tasks_file = project_manager.get_data_file('tasks')
        data = load_json_data(tasks_file)

        # Modify data
        data["tasks"].append(new_task)
        save_json_data(tasks_file, data)

        return {"status": "success", "task": new_task}
```

### 2. Code Style and Patterns

**Follow these patterns consistently**:

✅ **Validation First**
```python
# Check project initialization
init_error = check_project_initialized(project_manager)
if init_error:
    return init_error

# Validate input parameters
if not validate_priority(priority):
    return {"status": "error", "error": "Invalid priority"}
```

✅ **Simple File Operations**
```python
# Load data
data_file = project_manager.get_data_file('tasks')
data = load_json_data(data_file)

# Modify data
data["tasks"].append(new_item)

# Save atomically
save_json_data(data_file, data)
```

✅ **Consistent Error Handling**
```python
try:
    # Tool logic
    return {"status": "success", "result": data}
except Exception as e:
    return handle_error(e, "tool_name")
```

✅ **Standard Return Format**
```python
# Success
{"status": "success", "result": data, "message": "Operation complete"}

# Error
{"status": "error", "error": "Error message", "details": {...}}
```

### 3. Running the Server Locally

**Development mode**:
```bash
# Start with project directory
python server.py --project-dir "/path/to/project"

# Validate configuration
python server.py --validate
```

**Test with Claude Code**:
```bash
# Add to Claude Code (local testing)
claude mcp add claude-tasks-dev python server.py --project-dir "$(pwd)"

# Test tools
mcp__claude-tasks-dev__system_health_check
```

### 4. Common Development Tasks

**Adding a new tool** → See [`adding-tools.md`](./adding-tools.md)

**Testing changes**:
```bash
# Run full test suite
python test_all_mcp_tools_direct.py

# Test specific functionality
python -c "from tools.task_tools import *; print('Import successful')"
```

**Debugging**:
```python
# Add debug output in tools
print(f"DEBUG: {variable}")  # Appears in MCP server logs

# Check file operations
from utils.helpers import load_json_data
data = load_json_data(Path("/path/to/tasks.json"))
print(json.dumps(data, indent=2))
```

**File structure validation**:
```bash
# Check project structure
ls -la .claude-tasks/data/
cat .claude-tasks/data/tasks.json | python -m json.tool
```

## Utility Functions Reference

### From `utils/helpers.py`

**Error Handling**:
- `handle_error(error, tool_name)` - Standard error response format
- `check_project_initialized(project_manager)` - Validation check

**JSON Operations**:
- `load_json_data(file_path)` - Load with defaults if missing
- `save_json_data(file_path, data)` - Atomic write with temp file
- `get_default_data(data_type)` - Default data structures

**ID Generation**:
- `create_task_id()` - Generate task ID with timestamp
- `create_sprint_id()` - Generate sprint ID
- `create_session_id()` - Generate session ID

**Validation**:
- `validate_priority(priority)` - Check if priority valid (low/medium/high/critical)
- `validate_status(status)` - Check if status valid (pending/in_progress/completed/blocked)
- `validate_sprint_status(status)` - Check sprint status validity

**Timestamps**:
- `get_timestamp()` - Current ISO timestamp

### From `core/project_manager.py`

**Path Management**:
- `get_data_file(data_type)` - Get path to data file
- `get_spec_file(spec_type)` - Get path to specification file
- `get_template_file(template_type)` - Get path to template file

**Project Operations**:
- `set_project_directory(project_dir)` - Initialize project context
- `is_initialized()` - Check if project directory set

**Data Operations**:
- `get_storage_data(entity_type)` - Load data from file
- `save_storage_data(entity_type, data)` - Save data to file

## Tool Registration Pattern

**Standard pattern for new tool modules**:

```python
def register_your_tools(mcp, project_manager: ProjectManager):
    """Register your tool category"""

    @mcp.tool()
    async def your_tool_name(param: str) -> Dict[str, Any]:
        """Tool description for Claude"""
        try:
            # Validate project initialized
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error

            # Get data file
            data_file = project_manager.get_data_file('your_type')
            data = load_json_data(data_file)

            # Perform operation
            # ... tool logic ...

            # Save changes
            save_json_data(data_file, data)

            return {
                "status": "success",
                "result": data,
                "message": "Operation completed"
            }

        except Exception as e:
            return handle_error(e, "your_tool_name")
```

## Testing Your Changes

Always test changes with the comprehensive test suite:

```bash
# Run all tests
python test_all_mcp_tools_direct.py

# Expected output: 35/35 tools passing (100%)
```

See [`../testing/README.md`](../testing/README.md) for testing details.

## Common Pitfalls

❌ **Don't use complex abstractions**
```python
# Bad - complex abstraction layers
task_engine = TaskEngine(project_manager)
result = task_engine.create_task_with_validation(...)

# Good - direct file operations
data = load_json_data(project_manager.get_data_file('tasks'))
data["tasks"].append(new_task)
save_json_data(tasks_file, data)
```

❌ **Don't forget initialization checks**
```python
# Bad - assumes project initialized
data_file = project_manager.get_data_file('tasks')

# Good - check first
init_error = check_project_initialized(project_manager)
if init_error:
    return init_error
```

❌ **Don't skip error handling**
```python
# Bad - no error handling
data = json.load(file)

# Good - use helpers
data = load_json_data(file_path)  # Returns defaults if missing
```

❌ **Don't modify files directly without atomic writes**
```python
# Bad - direct write (can corrupt on failure)
with open(file_path, 'w') as f:
    json.dump(data, f)

# Good - atomic write via helper
save_json_data(file_path, data)  # Uses temp file + rename
```

## Performance Considerations

**File Operations**:
- All operations use atomic writes (temp file + rename)
- JSON files are small (~1-100KB), no caching needed
- Synchronization handled by unified file monitor

**Response Times**:
- Target: <100ms for all MCP tools
- File I/O: ~1-5ms
- JSON parsing: ~1-2ms
- Current: Sub-100ms achieved for all 35 tools

**Concurrency**:
- File operations are atomic but not locked
- MCP server is single-threaded
- No race conditions within single server instance
- External file changes handled by file monitor

## Next Steps

- **Add a new tool**: Follow the guide in [`adding-tools.md`](./adding-tools.md)
- **Run tests**: See [`../testing/README.md`](../testing/README.md)
- **Deploy changes**: Use deploy scripts (when available)

## Getting Help

- **Architecture Questions**: See `server.py` and `core/project_manager.py`
- **Tool Patterns**: Check existing tools in `tools/` directory
- **Testing**: See [`../testing/README.md`](../testing/README.md)
- **Production Deployment**: See main MCP server docs at `../mcp-server/`
