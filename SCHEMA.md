# Dev MCP Server Database Schema

*Last updated: 2025-10-08*

## Overview

The dev MCP server uses a **flattened schema** with individual columns (unlike prod's JSONB `data` column approach).

## Database Connection

- **URL**: `https://yxyfiatdrgelnvxopdsm.supabase.co`
- **Anon Key**: Available in `tools/document_tools.py:40`
- **Schema**: PostgreSQL with individual columns per field

## Tables

### `projects`
Multi-project isolation and identification.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | TEXT | Project name |
| `path` | TEXT | Project filesystem path (UNIQUE) |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

### `tasks`
Task management with flattened schema.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | TEXT | - | Primary key (e.g., "TASK-2025-001") |
| `project_id` | UUID | - | FK to projects.id |
| `machine_id` | TEXT | - | Machine identifier for sync |
| `title` | TEXT | - | Task title |
| `description` | TEXT | - | Task description |
| `status` | TEXT | - | Status: pending, in_progress, completed, blocked |
| `priority` | TEXT | - | Priority: low, medium, high, critical |
| `notes` | TEXT | - | Additional notes |
| `dependencies` | JSONB | `{"blocks": [], "blocked_by": [], "related": []}` | Task relationships |
| `completed_at` | TIMESTAMPTZ | NULL | Completion timestamp |
| `created_at` | TIMESTAMPTZ | NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOW() | Last update timestamp |

**Dependencies Structure:**
```json
{
  "blocks": ["TASK-2025-002"],        // Tasks this task blocks
  "blocked_by": ["TASK-2025-001"],    // Tasks blocking this task
  "related": ["TASK-2025-003"]        // Related tasks
}
```

### `sprints`
Sprint management (similar flattened structure).

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Primary key (e.g., "SPRINT-20251008") |
| `project_id` | UUID | FK to projects.id |
| `machine_id` | TEXT | Machine identifier |
| `title` | TEXT | Sprint title |
| `description` | TEXT | Sprint description |
| `status` | TEXT | Status: planning, active, completed |
| `start_date` | DATE | Sprint start date |
| `end_date` | DATE | Sprint end date |
| `task_ids` | JSONB | Array of task IDs in sprint |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

### `journal_sessions`
Work session tracking (note: table name is `journal_sessions` not `journal`).

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Primary key |
| `project_id` | UUID | FK to projects.id |
| `machine_id` | TEXT | Machine identifier |
| `session_type` | TEXT | Session type (e.g., "carry-on") |
| `tasks_worked` | JSONB | Array of tasks worked on |
| `key_achievements` | JSONB | Array of achievements |
| `discoveries` | JSONB | Array of discoveries |
| `duration_minutes` | INTEGER | Session duration |
| `created_at` | TIMESTAMPTZ | Session start time |
| `updated_at` | TIMESTAMPTZ | Last update |

### `documentation`
Markdown documentation files from /docs/ folder.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `project_id` | UUID | FK to projects.id (NULL for global docs) |
| `machine_id` | TEXT | Machine identifier |
| `doc_title` | TEXT | Document title (from # header or filename) |
| `file_path` | TEXT | Relative path (e.g., "architecture/overview.md") |
| `description` | TEXT | Short description (from first paragraph) |
| `content` | TEXT | Full markdown content |
| `scope` | TEXT | Scope: "project" or "global" |
| `is_global` | BOOLEAN | True if in ~/.claude/docs/, false if project |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update |

**Note**: No more `documents.json` - this table tracks actual `/docs/*.md` files only.

### `specifications`
Requirements/specifications management (formerly entities).

| Column | Type | Description |
|--------|------|-------------|
| `specification_id` | UUID | Primary key |
| `project_id` | UUID | FK to projects.id |
| `display_id` | TEXT | Human-readable ID |
| `specification_name` | TEXT | Specification name |
| `specification_type` | TEXT | Type (module, feature, api, etc.) |
| `description` | TEXT | Description |
| `requirements` | JSONB | Array of requirements |
| `constraints` | JSONB | Array of constraints |
| `approved` | BOOLEAN | Approval status |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update |

## MCP Tools → Database Field Mapping

### Task Operations

**task_create** creates tasks with:
- Core: `id`, `title`, `description`, `priority`, `status`
- Timestamps: `created_at`, `updated_at`
- Auto-added by sync: `project_id`, `machine_id`

**task_update** can modify:
- `status`, `priority`, `notes`
- `dependencies` (adds to JSONB structure)
- `completed_at` (set when status → "completed")
- `updated_at` (auto-updated)

### Document Operations

**document_create** (for frontend AI):
- Writes to `documentation` table directly
- Creates markdown file at `/docs/{document_type}/{document_title}.md`
- Fields: `doc_title`, `file_path`, `description`, `content`, `scope`

**document_update** (for frontend AI):
- Updates `documentation` table record
- Updates markdown file content

**document_query**:
- Queries `documentation` table
- Returns list of documents from project

**Local file edits**:
- Edit `/docs/*.md` files directly
- File monitor auto-syncs to `documentation` table

### Sync System

The unified file monitor (`core/universal_storage/unified_file_monitor.py`) syncs:
- Local JSON files → Database tables
- Adds `project_id` and `machine_id` automatically
- Filters out local-only fields not in database schema

## Schema Evolution

### Migration History
1. **Initial**: Basic flattened schema (id, title, description, status, priority, notes, timestamps)
2. **2025-10-08**: Added `dependencies` (JSONB) and `completed_at` (TIMESTAMPTZ)

### Applying Migrations
Migrations must be run via Supabase Dashboard SQL Editor:
```bash
# Location
/home/dev/.claude/task-sprint-system/mcp-server-dev/migrations/

# Latest migration
20251008_add_task_dependencies_completed_at.sql
```

## Schema Differences: Dev vs Prod

| Aspect | Dev (mcp-server-dev) | Prod (mcp-server) |
|--------|---------------------|-------------------|
| Storage | Individual columns | JSONB `data` column |
| Flexibility | Fixed schema | Flexible schema |
| Queries | Direct column access | JSONB operators |
| Migrations | ALTER TABLE | No migrations needed |
| Validation | Database constraints | Application layer |

## Notes

- **Table name mismatch**: Journal table is `journal_sessions`, not `journal`
- **Legacy fields**: Old local tasks.json may have fields not in database (assignee, tags, complexity, etc.) - these are filtered out during sync
- **Bidirectional sync**: Currently one-way (files → DB) due to realtime subscription issues with sync client
