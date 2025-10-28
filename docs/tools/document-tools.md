# Document Tools (5 tools)

*Simple markdown document management from /docs/ folder*

## Overview

Document tools manage simple markdown documentation that is automatically synced from `/docs/**/*.md` files. The system uses the `documentation` table with minimal metadata:

- **Title**: Extracted from first `# ` header in markdown
- **Path**: Relative path from docs folder (e.g., `guides/user-guide.md`)
- **Content**: Full markdown content
- **Scope**: `project` or `global` (based on location)

**Auto-Sync**: UnifiedFileMonitor automatically syncs markdown files from `/docs/` folder to database.

## Tools

### 1. document_create

**Purpose**: Create new markdown document file and sync to database.

**Parameters**:
- `document_title` (string, required): Document title
- `document_type` (string, required): Document type/category for folder organization (e.g., "guides", "architecture", "api")
- `description` (string, optional): Short description
- `content` (string, optional): Markdown content (default: empty)

**Returns**:
```python
{
    "status": "success",
    "document": {
        "id": "uuid-here",
        "doc_title": "Getting Started",
        "file_path": "guides/Getting Started.md",
        "scope": "project",
        "is_global": false
    },
    "file_created": "/path/to/docs/guides/Getting Started.md",
    "message": "Document 'Getting Started' created in docs/guides/"
}
```

**Usage Example**:
```python
# Create guide document
mcp__claude-tasks__document_create
  - document_title: "API Reference"
  - document_type: "guides"
  - description: "REST API documentation"
  - content: "# API Reference\n\nAPI endpoints..."
```

**Creates**:
- File: `docs/guides/API Reference.md`
- Database record in `documentation` table

---

### 2. document_update

**Purpose**: Update existing document content or metadata.

**Parameters**:
- `file_path` (string, required): Document path (e.g., "guides/API Reference.md")
- `content` (string, optional): New markdown content
- `description` (string, optional): New description

**Returns**: Updated document object

**Usage Example**:
```python
mcp__claude-tasks__document_update
  - file_path: "guides/API Reference.md"
  - content: "# Updated API Reference\n\nNew content..."
```

**Updates**:
- File: `docs/guides/API Reference.md`
- Database: `documentation` table record

---

### 3. document_query

**Purpose**: Search and filter documentation.

**Parameters**:
- `query` (string, optional): Text search in title/description/content
- `limit` (int, optional): Maximum results (default: 50)

**Returns**:
```python
{
    "status": "success",
    "documents": [
        {
            "id": "uuid",
            "doc_title": "Getting Started",
            "file_path": "guides/Getting Started.md",
            "description": "Quick start guide...",
            "scope": "project",
            "is_global": false,
            "created_at": "2025-10-24T...",
            "updated_at": "2025-10-24T..."
        }
    ],
    "total_matches": 5
}
```

**Usage Example**:
```python
# Search all docs
mcp__claude-tasks__document_query
  - query: "authentication"

# Get recent docs
mcp__claude-tasks__document_query
  - limit: 10
```

---

### 4. document_get

**Purpose**: Get single document by file path.

**Parameters**:
- `file_path` (string, required): Document path (e.g., "guides/API Reference.md")

**Returns**: Complete document object with full content

**Usage Example**:
```python
mcp__claude-tasks__document_get
  - file_path: "guides/Getting Started.md"
```

**Returns**:
```python
{
    "status": "success",
    "document": {
        "id": "uuid",
        "doc_title": "Getting Started",
        "file_path": "guides/Getting Started.md",
        "content": "# Getting Started\n\n...",
        "description": "Quick start guide",
        "scope": "project",
        "is_global": false
    }
}
```

---

### 5. document_delete

**Purpose**: Delete document file and remove from database.

**Parameters**:
- `file_path` (string, required): Document path to delete

**Returns**: Deletion confirmation

**Usage Example**:
```python
mcp__claude-tasks__document_delete
  - file_path: "guides/Old Guide.md"
```

**Removes**:
- File: `docs/guides/Old Guide.md`
- Database: Record from `documentation` table

---

## Document System Architecture

### Simple Sync System

```
/docs/**/*.md files
      ↓ (UnifiedFileMonitor watches)
documentation table
      ↓ (MCP tools query)
AI Agents
```

### Data Flow

**1. File Created/Modified**:
```
User creates: docs/guides/my-guide.md
  ↓
UnifiedFileMonitor detects change
  ↓
Extracts title from # header
  ↓
Syncs to documentation table with:
  - doc_title (from # header)
  - file_path (relative path)
  - content (full markdown)
  - scope (project or global)
```

**2. Database Query**:
```
AI agent calls document_query
  ↓
Queries documentation table
  ↓
Returns matching docs with content
```

### Schema

**`documentation` Table (11 fields)**:
```
id, project_id, machine_id, doc_title, file_path, description,
content, scope, is_global, created_at, updated_at
```

**Key Points**:
- No metadata files needed (unlike old system)
- Title extracted from markdown `# ` header
- Full content stored in `content` field
- Simple: just files → database

---

## Common Workflows

### Create Documentation

```python
# Create guide
mcp__claude-tasks__document_create
  - document_title: "Setup Guide"
  - document_type: "guides"
  - content: "# Setup Guide\n\n## Installation\n..."

# Result: Creates docs/guides/Setup Guide.md
```

### Search Documentation

```python
# Find authentication docs
mcp__claude-tasks__document_query
  - query: "authentication"

# Returns all docs mentioning authentication
```

### Update Documentation

```python
# Update content
mcp__claude-tasks__document_update
  - file_path: "guides/Setup Guide.md"
  - content: "# Updated Setup Guide\n\n..."

# File and database both updated
```

---

## File Organization

### Folder Structure

```
docs/
├── guides/           # User guides
├── architecture/     # System architecture
├── api/              # API documentation
├── development/      # Developer docs
└── reference/        # Reference materials
```

### File Naming

- Use descriptive names: `getting-started.md`, not `doc1.md`
- Use folders to organize by type
- Title extracted from `# ` header, not filename

---

## Scope: Project vs Global

### Project Documentation

**Location**: `<project>>/docs/*.md`

**Stored With**:
- `project_id`: Specific project UUID
- `scope`: `"project"`
- `is_global`: `false`

**Use For**: Project-specific documentation

### Global Documentation

**Location**: `~/.claude/docs/*.md`

**Stored With**:
- `project_id`: `NULL`
- `scope`: `"global"`
- `is_global`: `true`

**Use For**: Cross-project documentation, standards, best practices

---

## Auto-Sync Details

### What Gets Synced

- All `*.md` files in `/docs/` folder (recursive)
- Changes detected automatically by UnifiedFileMonitor
- Title extracted from first `# ` header
- Description extracted from first non-header paragraph

### When Sync Happens

- **File created**: Immediate sync to database
- **File modified**: Immediate sync on save
- **File deleted**: Record removed from database

### Hash-Based Deduplication

- File hash calculated before sync
- Only syncs if content changed
- Prevents sync loops and unnecessary updates

---

## Best Practices

1. **Use Clear Headers**: Start each file with `# Title` for proper title extraction
2. **Organize by Type**: Use folders (guides, architecture, api, etc.)
3. **Write Descriptions**: First paragraph becomes searchable description
4. **Keep Simple**: No complex metadata - just markdown files
5. **Use Standard Markdown**: GitHub-flavored markdown recommended

---

## Limitations

- No complex metadata (status, priority, approval workflows)
- No document sections (use markdown headers instead)
- No parent-child hierarchy in database (use folder structure)
- Full content stored (no chunking for very large files)

**Simplicity is the design goal** - just files syncing to database for query access.

---

## Tool Subscription

Document tools are in the `document` category. To exclude them:

```json
{
  "tool_subscription": {
    "exclude_categories": ["document"]
  }
}
```

**Why exclude?**: Local agents can read files directly (faster than database queries)

---

## See Also

- [SCHEMA.md](../../SCHEMA.md) - Database schema details
- [File Monitor Architecture](../architecture/file-monitor.md) - How auto-sync works
- [Adding Tools Guide](../development/adding-tools.md) - Extend document tools
