# Document System Consolidation Summary

*Date: 2025-10-08*

## Changes Made

### Removed CMS Metadata System
- ❌ Removed `documents.json` from sync system
- ❌ Removed `documents` + `document_sections` tables usage
- ❌ Removed complex hierarchy/approval workflow

### Implemented Simple Filesystem Approach
- ✅ Direct `/docs/*.md` file management
- ✅ Single `documentation` table for metadata
- ✅ Bidirectional sync between files and database

## New Architecture

### Frontend AI Agents (Chat UI)
```
MCP document_create() → documentation table → /docs/*.md file
MCP document_update() → documentation table → /docs/*.md file
MCP document_query() → documentation table
MCP document_get() → documentation table
MCP document_delete() → documentation table + delete file
```

### Local AI Agents (Claude Code)
```
Edit /docs/*.md directly → File monitor → documentation table
Read /docs/*.md directly → Filesystem
```

### Bidirectional Sync
```
MCP Tools → Database → Filesystem (via MCP tool)
Filesystem → Database (via file monitor)
```

**Note**: Database → Filesystem sync will work automatically once realtime subscriptions are fixed (requires async Supabase client).

## Database Schema

### `documentation` Table
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `project_id` | UUID | Project isolation (NULL for global) |
| `doc_title` | TEXT | Document title |
| `file_path` | TEXT | Relative path (e.g., "guides/Setup.md") |
| `description` | TEXT | Short description |
| `content` | TEXT | Full markdown content |
| `scope` | TEXT | "project" or "global" |
| `is_global` | BOOLEAN | Scope flag |
| `created_at`, `updated_at` | TIMESTAMPTZ | Timestamps |

## MCP Tool Changes

### document_create
**Before**: Wrote to documents.json with complex hierarchy
**After**: Writes to documentation table + creates `/docs/{type}/{title}.md`

### document_update
**Before**: Updated documents.json metadata
**After**: Updates documentation table + file content

### document_query
**Before**: Queried documents.json with complex filtering
**After**: Simple query of documentation table

### document_get
**Before**: Retrieved from documents.json
**After**: Retrieves from documentation table

### document_delete
**Before**: Soft/hard delete in documents.json
**After**: Deletes from documentation table + removes file

## Benefits

1. **Simpler**: One table, one file per document
2. **Direct**: Filesystem reflects database directly
3. **Flexible**: Local agents edit files, frontend agents use MCP
4. **Maintainable**: No complex hierarchy/approval metadata
5. **Synced**: Automatic bidirectional sync

## Migration Notes

- Old `documents.json` entries will not be migrated
- Existing `/docs/*.md` files will be auto-synced on server start
- Frontend will need updates to use new MCP tool signatures
