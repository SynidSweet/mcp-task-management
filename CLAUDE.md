# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A **simplified MCP (Model Context Protocol) server** providing 35 tools for task/sprint management. Built with a function-based architecture emphasizing directness over abstraction.

**Key Stats**: 35 tools across 8 categories | 100% test coverage | ~68% less code than production version

## Quick Commands

```bash
# Run the server
python server.py --project-dir "$(pwd)"

# Run all tests (expect 35/35 passing)
python test_all_mcp_tools_direct.py

# Run database readiness check
python test_database_readiness.py
```

## Architecture Philosophy

**Core Principle**: Direct operations over abstraction layers.

### What We Do

- **Function-based tool registration** - No class hierarchies
- **Direct JSON file operations** - No repository pattern
- **Explicit over implicit** - Clear what happens when
- **Separation of concerns** - Tools handle logic, UnifiedFileMonitor handles sync

### What We Don't Do

- No storage abstraction layers
- No transformer classes
- No complex dependency injection
- No repository patterns

**Result**: Average tool is ~30 lines vs ~80 lines in production version.

## Code Structure

```
mcp-server/
├── server.py                   # Main server (140 lines)
├── tools/                      # 8 tool modules
│   ├── system_tools.py         # Health checks, project setup (3 tools)
│   ├── task_tools.py           # Task CRUD (8 tools)
│   ├── sprint_tools.py         # Sprint management (5 tools)
│   ├── journal_tools.py        # Session tracking (3 tools)
│   ├── git_tools.py            # Git validation (4 tools)
│   ├── specification_tools.py  # Requirements (10 tools)
│   ├── template_tools.py       # Templates (2 tools)
│   └── document_tools.py       # Documentation (6 tools)
├── core/
│   ├── project_manager.py      # File path management only
│   └── universal_storage/
│       └── unified_file_monitor.py  # Bidirectional file ↔ DB sync
├── utils/
│   ├── helpers.py              # JSON ops, validation, timestamps
│   └── validation_wrapper.py   # @require_project_basics decorator
└── test_all_mcp_tools_direct.py    # 35 tool tests
```

## Tool Development Pattern

All tools follow this pattern:

```python
def register_your_tools(mcp, project_manager: ProjectManager):
    """Register tools in module"""

    @require_project_basics()  # Decorator checks project initialized
    @mcp.tool()
    async def tool_name(param: str) -> Dict[str, Any]:
        """Tool description"""
        try:
            # 1. Load data
            data_file = project_manager.get_data_file('tasks')
            data = load_json_data(data_file)

            # 2. Validate inputs
            if not validate_something(param):
                return {"status": "error", "error": "Invalid param"}

            # 3. Perform operation
            result = do_something(data, param)

            # 4. Save changes (if modifying)
            save_json_data(data_file, data)

            # 5. Return response
            return {"status": "success", "result": result}

        except Exception as e:
            return handle_error(e, "tool_name")
```

**Key Points**:
- Use `@require_project_basics()` decorator for project initialization check
- Always return `{"status": "success"|"error", ...}` format
- Use helpers from `utils/helpers.py` for common operations
- Keep tool logic in single function - no layers

## File Sync System

**UnifiedFileMonitor** watches files and syncs to Supabase automatically:

- **Local edit** → File monitor detects → Syncs to database
- **Database edit** → Syncs to local files (bidirectional)
- **Hash-based loop prevention** - Won't re-sync unchanged content
- **Entity-level sync** - Only changed items update

**Synced entity types**: tasks, sprints, journal, requirements, documents, templates, commands, agents, documentation, mcp_configs

**Tools don't handle sync** - Just save JSON, monitor handles the rest.

## Database Schema

**Flattened schema** with individual columns (see SCHEMA.md for complete details):

- **projects** - Multi-project isolation (project_id FK everywhere)
- **tasks** - Individual columns: id, title, description, status, priority, notes, dependencies (JSONB), completed_at, timestamps
- **sprints** - id, title, status, dates, task_ids (JSONB)
- **journal_sessions** - (note: table name is `journal_sessions` not `journal`)
- **documentation** - Tracks `/docs/*.md` files (no more documents.json)
- **specifications** - Requirements/specs management

**Connection info**: URL and keys in `tools/document_tools.py:40`

## Adding New Tools

### 1. Choose Module

Add to existing module in `tools/` or create new one for new domains.

### 2. Implement Tool

```python
# In tools/task_tools.py (for example)

@require_project_basics()
@mcp.tool()
async def task_your_feature(task_id: str, param: str) -> Dict[str, Any]:
    """Description of what this does"""
    try:
        # Input validation
        if not param:
            return {"status": "error", "error": "param required"}

        # Load data
        tasks_file = project_manager.get_data_file('tasks')
        data = load_json_data(tasks_file)

        # Find and modify
        task = next((t for t in data['tasks'] if t['id'] == task_id), None)
        if not task:
            return {"status": "error", "error": f"Task {task_id} not found"}

        task['your_field'] = param
        task['updated_at'] = get_timestamp()

        # Save
        save_json_data(tasks_file, data)

        return {"status": "success", "task": task}

    except Exception as e:
        return handle_error(e, "task_your_feature")
```

### 3. Register (if new module)

Edit `server.py` `_register_all_tools()`:

```python
from tools.your_module import register_your_tools

tool_registrations = [
    # ... existing ...
    ("YourTools", register_your_tools),
]
```

### 4. Add Tests

Add test to `test_all_mcp_tools_direct.py` (see file for patterns). Update tool counts.

### 5. Verify

```bash
python test_all_mcp_tools_direct.py
# Should show your new tool passing
```

**See docs/development/adding-tools.md for complete guide**

## Testing Approach

**Direct testing** - No mocking complexity:

```python
# Create temp ProjectManager
project_manager = ProjectManager(temp_dir)

# Test tool directly
result = await task_create("Test Task", "high")

# Verify results
assert result['status'] == 'success'

# Check file
data = load_json_data(project_manager.get_data_file('tasks'))
assert len(data['tasks']) == 1
```

All 35 tools tested this way. Run with `python test_all_mcp_tools_direct.py`.

## Common Helper Functions

From `utils/helpers.py`:

- `load_json_data(file_path)` - Load JSON with error handling
- `save_json_data(file_path, data)` - Save JSON with formatting
- `get_timestamp()` - ISO timestamp
- `create_task_id()` - Generate task IDs (TASK-YYYY-NNN)
- `validate_priority(priority)` - Check priority values
- `validate_status(status)` - Check status values
- `handle_error(e, operation)` - Standard error format
- `check_project_initialized(pm)` - Project validation

## Key Implementation Details

### ProjectManager

Simple file path manager - **no business logic**:

```python
project_manager.get_data_file('tasks')      # → .claude-tasks/data/tasks.json
project_manager.get_spec_file('req-001')    # → .claude-specs/data/specifications/req-001.json
project_manager.get_template_file('sprint') # → .claude-tasks/templates/sprint.json
```

### Task IDs

Format: `TASK-YYYY-NNN` (e.g., `TASK-2025-001`)

Generated with: `f"TASK-{datetime.now().strftime('%Y')}-{len(tasks_list) + 1:03d}"`

### Data File Structure

Tasks.json format:
```json
{
  "tasks": [
    {
      "id": "TASK-2025-001",
      "title": "Task title",
      "description": "Description",
      "priority": "high",
      "status": "pending",
      "notes": "",
      "dependencies": {"blocks": [], "blocked_by": [], "related": []},
      "created_at": "2025-10-08T12:00:00Z",
      "updated_at": "2025-10-08T12:00:00Z",
      "completed_at": null
    }
  ],
  "metadata": {
    "created_at": "2025-10-08T12:00:00Z",
    "version": "1.0"
  }
}
```

### Error Handling

Standard response format:

```python
# Success
{"status": "success", "result": data, "message": "Optional message"}

# Error
{"status": "error", "error": "Error description"}
```

Use `handle_error(e, operation)` for consistent error responses.

## Documentation

**Complete docs in `docs/` directory:**

- **[docs/README.md](docs/README.md)** - Documentation index
- **[docs/architecture/](docs/architecture/)** - System design (4 files)
  - [simplified-architecture.md](docs/architecture/simplified-architecture.md) - Why function-based
  - [tool-registration.md](docs/architecture/tool-registration.md) - How tools work
  - [file-monitor.md](docs/architecture/file-monitor.md) - Sync system details
- **[docs/development/](docs/development/)** - Developer guides (2 files)
  - [adding-tools.md](docs/development/adding-tools.md) - Step-by-step tool creation
- **[docs/tools/](docs/tools/)** - All 35 tools documented (10 files)
- **[docs/agent-orientation/](docs/agent-orientation/)** - AI agent workflows (3 files)
- **[docs/testing/](docs/testing/)** - Testing guide (1 file)

## Performance Characteristics

- **Most tool operations**: <10ms
- **File read/write**: <5ms
- **Cloud sync**: <100ms (async, non-blocking)
- **Full test suite**: <1s

**50% faster than production** due to simplified architecture.

## Dependencies

Installed in `venv/`:

- `mcp` - Official MCP SDK
- `watchdog` - File monitoring
- Supabase client libs
- pytest (testing)

Install: `pip install mcp watchdog`

## Common Pitfalls

1. **"No project directory set"** - Must call `system_set_project_directory` first or use `@require_project_basics()` decorator
2. **Table name mismatch** - Journal table is `journal_sessions`, not `journal`
3. **Legacy fields** - Old tasks.json may have fields not in database schema (filtered during sync)
4. **Both 'tasks' and 'task' keys** - Handle both in code for compatibility

## Design Trade-offs

**What we lose:**
- Reusability (extract to helpers when needed)
- Can't easily swap storage backends
- Less flexible schemas

**What we gain:**
- Simplicity (easy to understand/modify)
- Performance (50% faster)
- Maintainability (fewer moving parts)
- Clarity (obvious execution path)

**Philosophy**: Use the simplest approach that solves the problem. Add abstractions only when they provide clear value.

## For More Information

- Complete architecture explanation: [docs/architecture/simplified-architecture.md](docs/architecture/simplified-architecture.md)
- Step-by-step tool creation: [docs/development/adding-tools.md](docs/development/adding-tools.md)
- Database schema details: [SCHEMA.md](SCHEMA.md)
- Agent workflows: [docs/agent-orientation/README.md](docs/agent-orientation/README.md)
