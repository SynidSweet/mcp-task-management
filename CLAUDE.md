# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A **simplified MCP (Model Context Protocol) server** providing 37 tools for task/sprint management. Built with a function-based architecture emphasizing directness over abstraction.

**Key Stats**: 37 tools across 8 categories | 100% test coverage | Full sprint-task integration

**📋 Database Schema:** See `../SCHEMA.md` for complete database schema documentation (shared with frontend)

## Quick Commands

```bash
# Run the server
python server.py --project-dir "$(pwd)"

# Run all tests (expect 37/37 passing)
python test_all_mcp_tools_direct.py

# Run database readiness check
python test_database_readiness.py

# Check data integrity (recommended after schema changes)
python3 check_data_integrity.py
python3 check_data_integrity.py --fix  # Auto-repair safe issues

# Run migrations
python3 run_migration.py supabase/migrations/<migration_file>.sql
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

**Synced entity types**: tasks, sprints, journal, requirements, templates, commands, agents, documentation, mcp_configs

**Tools don't handle sync** - Just save JSON, monitor handles the rest.

## Database Schema

**Flattened schema** with individual columns (see SCHEMA.md for complete details):

- **projects** - Multi-project isolation (project_id FK everywhere)
- **tasks** - Individual columns: id, title, description, status, priority, notes, dependencies (JSONB), completed_at, timestamps
- **sprints** - id, title, status, dates, task_ids (JSONB)
- **journal_sessions** - (note: table name is `journal_sessions` not `journal`)
- **documentation** - Simple markdown docs from `/docs/*.md` files - auto-synced with title, path, and full content (no metadata files needed)
- **specifications** - Requirements/specs management
- **specifications_validated** - Human-approved specification snapshots (see Validation System below)

**Connection info**: URL and keys in `tools/document_tools.py:40`

## Specification Validation System

**⚠️ CRITICAL WORKFLOW: AI Suggestions vs Human Approval**

### Core Principle

All specification operations (create/update/delete) by AI agents are **SUGGESTIONS ONLY**.
Human validation in the frontend is required before implementation.

### How It Works

**1. AI Agent Creates/Updates Specification**
- Writes to `specifications` table (current suggestions)
- Marked as `approved=false` by default
- Assigned `validation_status="new"` (or "modified" if updating validated spec)

**2. Frontend Shows Validation Status**
- Queries both `specifications` and `specifications_validated` tables
- Compares current (AI suggested) vs validated (human approved)
- Shows diffs for fields that changed

**3. Human Validates in Frontend**
- Reviews AI suggestions and diffs
- Approves changes → copies to `specifications_validated`
- Sets `validated_at` timestamp and optional `validated_by` user

**4. AI Agents Check Before Implementation**
- Query specifications with validation status
- See `validation_status` field: `"new"`, `"modified"`, or `"validated"`
- Only implement specs with `validation_status="validated"`

### Validation Status Values

```python
"new"       # Never validated - AI suggestion only
"modified"  # Was validated, but has new AI changes
"validated" # Matches last human approval - safe to implement
```

### Query Tool Enhancement

All specification queries automatically include validation status:

```python
# Minimal mode - adds validation_status field
{
  "display_id": "api_gateway",
  "specification_name": "API Gateway",
  "validation_status": "modified"  # ⚠️ Has unvalidated changes
}

# Compact mode - adds hint for modified specs
{
  "display_id": "api_gateway",
  "validation_status": "modified",
  "validation_hint": "Has unvalidated changes"
}

# Full mode - includes validated snapshot for comparison
{
  "display_id": "api_gateway",
  "validation_status": "modified",
  "validated_snapshot": {
    "specification_name": "API Gateway [validated]",
    "description": "Original validated description",
    "validated_at": "2025-10-19T12:00:00Z"
  }
}
```

### Tool Response Messages

All CRUD tools return suggestion reminders:

```python
# Create
"message": "Specification 'API Gateway' suggested (pending user validation)",
"reminder": "⚠️ This is a suggestion. A user must validate in the frontend."

# Update
"message": "Specification updates suggested (pending user validation)",
"reminder": "⚠️ Changes are suggestions. User must re-validate in the frontend."

# Delete
"message": "Specification deletion suggested (pending user approval)",
"reminder": "⚠️ Deletion is a suggestion. User must approve in the frontend."
```

### Agent Best Practices

1. **Check validation status before implementing**
   ```python
   result = await specification_get(display_id="api_gateway", verbosity="compact")
   if result["specifications"][0]["validation_status"] != "validated":
       print("⚠️ Cannot implement: Specification not validated by user")
   ```

2. **Use appropriate verbosity**
   - `minimal` - Lightweight queries, just status flag
   - `compact` - See status + helpful hints
   - `full` - Compare current vs validated when debugging

3. **Suggest, don't demand**
   - Your role is to propose specifications
   - Users make final decisions on requirements
   - Treat rejections as valuable feedback

### Database Tables

See `SCHEMA.md` for complete table definitions:
- `specifications` - Current state (AI suggestions + validated)
- `specifications_validated` - Human-approved snapshots only
- `specification_requirements_validated` - Approved requirements
- `specification_constraints_validated` - Approved constraints

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

## Tool Subscription Filtering

**Control which tools are available** per project using a subscription configuration file.

### Default Configuration

**A default configuration is automatically created** on first server startup that excludes the `document` category. This is because:
- **Local agents** use the filesystem directly for documentation (Read/Write/Edit tools)
- **Document tools** provide database queries for synced `/docs/*.md` files (useful for online agents that can't access filesystem directly)

The default config is created at `.claude-tasks/config/tool_subscription.json` and looks like:

```json
{
  "_comment": "Tool Subscription Configuration - Controls which MCP tools are available",
  "_description": "Default config excludes 'document' category (online agents only). Local agents use filesystem for docs.",
  "tool_subscription": {
    "include_tools": [],
    "exclude_tools": [],
    "include_categories": [],
    "exclude_categories": ["document"]
  }
}
```

### Custom Configuration

Edit `.claude-tasks/config/tool_subscription.json` to customize:

```json
{
  "tool_subscription": {
    "include_tools": [],
    "exclude_tools": [],
    "include_categories": [],
    "exclude_categories": []
  }
}
```

### Filtering Modes

**1. Whitelist Specific Tools** (most restrictive):
```json
{
  "tool_subscription": {
    "include_tools": ["task_create", "task_get", "sprint_get_current"]
  }
}
```

**2. Blacklist Specific Tools**:
```json
{
  "tool_subscription": {
    "exclude_tools": ["task_delete", "sprint_delete", "specification_delete"]
  }
}
```

**3. Whitelist Categories**:
```json
{
  "tool_subscription": {
    "include_categories": ["task", "sprint", "journal"]
  }
}
```

**4. Blacklist Categories**:
```json
{
  "tool_subscription": {
    "exclude_categories": ["git", "specification"]
  }
}
```

**5. Combined Filtering**:
```json
{
  "tool_subscription": {
    "include_categories": ["task", "sprint"],
    "exclude_tools": ["task_delete", "sprint_delete"]
  }
}
```

### Available Categories

- `system` - Health checks, project setup (3 tools)
- `task` - Task CRUD operations (7 tools)
- `sprint` - Sprint management (8 tools)
- `journal` - Session tracking (3 tools)
- `git` - Git operations (2 tools)
- `specification` - Requirements management (5 tools)
- `template` - Template operations (2 tools)
- `document` - Documentation query/management (5 tools) - queries `documentation` table (synced from `/docs/*.md`)

### Precedence Order

1. `include_tools` - If set, ONLY these tools are available (overrides everything)
2. `include_categories` - If set, only tools from these categories
3. `exclude_categories` - Remove entire categories
4. `exclude_tools` - Remove specific tools
5. **Default** - All tools available if no config exists

### Testing Filters

Run the subscription filter tests:

```bash
python3 test_tool_subscription.py
```

### Implementation Details

- **Default config automatically created** on first startup (excludes `document` category)
- Filter loaded at server startup from `.claude-tasks/config/tool_subscription.json`
- Tools not matching filter are never registered with MCP
- Server prints active filters on startup if any are configured
- No performance impact - filtering happens once during initialization
- See `tool_subscription.example.json` for the default config structure

## Template System (Normalized Schema)

**Status**: ✅ Fully migrated to normalized database tables (as of 2025-10-26)

### Overview

Templates are stored in normalized database tables (`template_tasks`, `template_sprints`) that mirror the structure of actual `tasks` and `sprints` tables. This enables:
- **Queryable templates** - Filter by category, scope, variables, etc.
- **Template composition** - Templates can reference other templates
- **Unlimited nesting** - Support for complex hierarchies
- **Single source of truth** - Reusable workflow components

### Database Tables

#### `template_tasks`
Mirrors `tasks` table structure with template-specific features:
- `template_id` - User-facing ID (e.g., "setup_infrastructure")
- `is_entry_task` - `true` for root templates, `false` for nested subtasks
- `references_template_id` - Points to another template (for composition)
- `override_variables` - Variable overrides when referencing
- `child_template_ids` - Array of child template IDs (hierarchy)
- `variables` - JSONB array of variable definitions
- All standard task fields: `title`, `description`, `priority`, etc.

#### `template_sprints`
Mirrors `sprints` table structure with template-specific features:
- `template_id` - User-facing ID (e.g., "feature_development")
- `task_ids` - Array of template_task IDs (mirrors sprints.task_ids)
- `variables` - JSONB array of variable definitions
- All standard sprint fields: `title`, `focus`, dates, etc.

### Key Concepts

#### Entry Tasks vs Nested Tasks

The `is_entry_task` field distinguishes:
- **Entry tasks** (`is_entry_task = true`) - Root-level templates shown in listings
- **Nested tasks** (`is_entry_task = false`) - Child tasks only visible within parent

Example:
```
quality_gate (entry task)
├── code_review_ref (nested, references code_review template)
└── security_scan (nested, inline definition)
```

#### Template Composition

Templates can reference other templates using `references_template_id`:
```sql
-- Reusable template
SELECT * FROM template_tasks WHERE template_id = 'code_review';

-- Composite template that references it
SELECT * FROM template_tasks
WHERE template_id = 'quality_gate_ref_0'
  AND references_template_id = 'code_review';
```

Supports:
- Unlimited nesting depth
- Variable override at each level
- Circular reference detection

### Template Tools (6 tools total)

**Task Template Tools**:
- `template_list(scope, category, entry_tasks_only)` - List task templates
- `template_get(template_id, resolve_references, resolve_children)` - Get task template

**Sprint Template Tools**:
- `sprint_template_list(scope)` - List sprint templates
- `sprint_template_get(template_id, resolve_tasks)` - Get sprint template

**Instantiation Tools**:
- `task_create_from_template(template_id, variables, sprint_id)` - Create actual tasks from template
- `sprint_create_from_template(template_id, variables, start_date)` - Create actual sprint from template

### Migration

Templates were migrated from monolithic JSON to normalized tables on 2025-10-26:
- **Migration script**: `migrate_templates_to_normalized.py`
- **Old tables dropped**: `templates`, `template_versions`, `template_collections` (deprecated)
- **Status**: ✅ Migration complete, old tables removed
- **Rollback**: Not available (deprecated tables dropped). Backup exists in `migrate_templates_to_normalized.py` logic.

### Example Queries

```sql
-- List all entry task templates by category
SELECT template_id, template_name, category
FROM template_tasks
WHERE is_entry_task = true AND category = 'infrastructure';

-- Get template with all children
SELECT t.*, array_agg(c.*) as children
FROM template_tasks t
LEFT JOIN template_tasks c ON c.parent_template_id = t.template_id
WHERE t.template_id = 'quality_gate'
GROUP BY t.id;

-- Find all templates that reference a specific template
SELECT template_id, parent_template_id
FROM template_tasks
WHERE references_template_id = 'code_review';
```

### File Sync

**Note**: File monitor updates for templates are pending. Current workflow:
1. Templates queryable directly from database
2. File sync will be added for local JSON compatibility
3. Bidirectional sync planned: DB ↔ JSON files

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

## Data Integrity Checker

**Location**: `check_data_integrity.py`

Validates database integrity, Dual-ID system consistency, and architecture compliance. Run after schema changes or when debugging data issues.

**Usage**:
```bash
# Check integrity (safe, no changes)
python3 check_data_integrity.py

# Auto-repair safe issues (Dual-ID mismatches)
python3 check_data_integrity.py --fix

# Check specific table only
python3 check_data_integrity.py --table specifications

# Verbose output with detailed progress
python3 check_data_integrity.py --verbose

# JSON output for CI/CD integration
python3 check_data_integrity.py --format json > report.json
```

**What it checks**:
- **Specifications:** Dual-ID sync, hierarchy, circular refs, uniqueness
- **Tasks:** Hierarchy, dependencies, circular refs, sprint_id FK, value validation
- **Sprints:** task_ids array, dates, sprint-task reciprocity
- **Global resources:** Templates, commands, agents, documentation field validation
- **Schema compliance:** Required fields, valid values, deprecated fields

**Auto-repair**:
- Safely fixes Dual-ID mismatches by resolving parent_display_id to UUID
- Re-runs checks after repair to verify fixes
- Exit code: 0 = pass, 1 = issues found, 2 = error

**Full spec**: See `docs/specifications/data-integrity-checker.md`

## Common Pitfalls

1. **"No project directory set"** - Must call `system_set_project_directory` first or use `@require_project_basics()` decorator
2. **Table name mismatch** - Journal table is `journal_sessions`, not `journal`
3. **Legacy fields** - Old tasks.json may have fields not in database schema (filtered during sync)
4. **Both 'tasks' and 'task' keys** - Handle both in code for compatibility
5. **Missing parent_id UUIDs** - Run integrity checker after creating specifications to detect/fix Dual-ID mismatches

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
