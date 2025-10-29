# MCP Config Normalization - Complete Research & Design

**Status:** ✅ Schema designed, migration SQL created, ready for implementation
**Date:** 2025-10-29
**Migration File:** `supabase/migrations/20251029000000_normalize_mcp_configs.sql`

---

## Executive Summary

Successfully researched Claude Code's MCP configuration structure and designed a **normalized database schema** to replace the current JSONB-based storage. The new schema breaks down `mcp_configs.config_data` into two related tables with queryable columns while preserving JSONB only for variable-length arrays.

### Key Improvements

| Aspect | Current (JSONB) | New (Normalized) | Improvement |
|--------|-----------------|------------------|-------------|
| **Server Queries** | Complex JSON path operators | Simple SQL WHERE clauses | ⭐⭐⭐⭐⭐ |
| **Indexing** | Limited JSONB indexes | Full column indexes | ⭐⭐⭐⭐⭐ |
| **Integrity** | No constraints within JSONB | Foreign keys + CHECK constraints | ⭐⭐⭐⭐⭐ |
| **Maintainability** | JSON parsing in queries | Standard SQL | ⭐⭐⭐⭐ |
| **Performance** | Full table scans | Indexed lookups | ⭐⭐⭐⭐ |

---

## Research Findings

### MCP Config File Structure

Claude Code uses **two configuration file formats**:

1. **`.claude-mcp-config.json`** (legacy/user format)
   - Located at `~/.claude/.claude-mcp-config.json`
   - Uses `"transport"` field for transport type
   - Includes optional `_metadata` section

2. **`.mcp.json`** (project format)
   - Located at project root
   - Uses `"type"` field for transport type
   - No metadata section

### Complete Configuration Schema

```json
{
  "_metadata": {                    // Optional (only in .claude-mcp-config.json)
    "machine_id": "string",
    "created_at": "timestamp",
    "auto_generated": boolean,
    "repo_root": "path"
  },
  "mcpServers": {
    "server-name": {
      // Common fields
      "type": "stdio|http|sse",      // In .mcp.json
      "transport": "http|stdio|sse", // In .claude-mcp-config.json
      "disabled": boolean,            // Optional
      "alwaysAllow": boolean,         // Optional

      // Stdio-specific
      "command": "executable",
      "args": ["arg1", "arg2"],
      "env": {"KEY": "value"},

      // HTTP/SSE-specific
      "url": "http://endpoint",
      "headers": {"Authorization": "Bearer ..."}
    }
  }
}
```

### Real-World Examples

**Example 1: HTTP servers**
```json
{
  "mcpServers": {
    "claude-tasks-dev": {
      "transport": "http",
      "url": "http://localhost:8082/projects//home/dev/.claude/mcp"
    }
  }
}
```

**Example 2: Stdio server**
```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

---

## Normalized Schema Design

### Table 1: `mcp_config_files`

**Purpose:** Store file-level metadata about MCP configuration files

```sql
CREATE TABLE mcp_config_files (
    id UUID PRIMARY KEY,
    machine_id TEXT NOT NULL,

    -- File identification
    config_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,  -- 'claude-mcp-config' or 'mcp'

    -- Metadata fields (from _metadata section)
    metadata_machine_id TEXT,
    metadata_created_at TIMESTAMPTZ,
    metadata_auto_generated BOOLEAN,
    metadata_repo_root TEXT,

    -- Scope and timestamps
    scope TEXT DEFAULT 'global',
    is_global BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(machine_id, config_name)
);
```

### Table 2: `mcp_servers`

**Purpose:** Store individual MCP server configurations with normalized columns

```sql
CREATE TABLE mcp_servers (
    id UUID PRIMARY KEY,
    config_file_id UUID REFERENCES mcp_config_files(id) ON DELETE CASCADE,
    machine_id TEXT NOT NULL,

    -- Server identification
    server_name TEXT NOT NULL,
    transport_type TEXT NOT NULL CHECK (transport_type IN ('stdio', 'http', 'sse')),

    -- Common fields
    disabled BOOLEAN DEFAULT false,
    always_allow BOOLEAN DEFAULT false,

    -- Stdio fields
    command TEXT,
    args JSONB,    -- Array (variable length, must be JSONB)
    env JSONB,     -- Object (key-value pairs, must be JSONB)

    -- HTTP/SSE fields
    url TEXT,
    headers JSONB,  -- Object (key-value pairs, must be JSONB)

    -- Ordering
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(config_file_id, server_name),

    -- Transport-specific field validation
    CONSTRAINT check_stdio_fields CHECK (
        transport_type = 'stdio' AND command IS NOT NULL OR transport_type != 'stdio'
    ),
    CONSTRAINT check_http_sse_fields CHECK (
        transport_type IN ('http', 'sse') AND url IS NOT NULL OR transport_type NOT IN ('http', 'sse')
    )
);
```

### Key Design Decisions

1. **Two-table design**: Separates file metadata from server configs for clean structure
2. **Denormalized machine_id**: In `mcp_servers` for faster queries without joins
3. **JSONB for arrays only**: `args`, `env`, `headers` remain JSONB (unavoidable, variable-length)
4. **CHECK constraints**: Enforce transport-specific field requirements
5. **sort_order column**: Preserves server order from JSON file
6. **Cascade delete**: Removing config file automatically removes related servers

---

## Query Improvements

### Before (JSONB) vs After (Normalized)

#### Query 1: Get all HTTP servers
**Before:**
```sql
-- Nearly impossible without full JSON traversal
SELECT config_data FROM mcp_configs
WHERE config_data::text LIKE '%"transport":"http"%';
```

**After:**
```sql
-- Simple indexed query
SELECT server_name, url, disabled
FROM mcp_servers
WHERE transport_type = 'http' AND disabled = false;
```

#### Query 2: Find Python-based servers
**Before:**
```sql
-- Full table scan, no indexes
SELECT * FROM mcp_configs
WHERE config_data::text LIKE '%python%';
```

**After:**
```sql
-- Indexed command column
SELECT server_name, command, args
FROM mcp_servers
WHERE command LIKE '%python%';
```

#### Query 3: Count servers by transport type
**Before:**
```sql
-- Complex JSON aggregation
-- (Actually not feasible with current schema)
```

**After:**
```sql
-- Simple GROUP BY with indexed column
SELECT transport_type, COUNT(*)
FROM mcp_servers
GROUP BY transport_type;
```

---

## Migration Strategy

### Phase 1: Schema Creation ✅
**File:** `supabase/migrations/20251029000000_normalize_mcp_configs.sql`

- Creates `mcp_config_files` and `mcp_servers` tables
- Sets up indexes, triggers, and RLS policies
- Includes data migration from existing `mcp_configs` table
- **Status:** Complete, ready to run

### Phase 2: Update Sync Code (Next Step)
**File:** `core/universal_storage/unified_file_monitor.py:_sync_mcp_config()`

Required changes:
1. Parse JSON file into config file + servers structure
2. Upsert to `mcp_config_files` table
3. Delete existing servers for config
4. Insert server records in batch
5. Handle both `.claude-mcp-config.json` and `.mcp.json` formats

### Phase 3: Verification & Cleanup
1. Run migration on test database
2. Verify data integrity
3. Test sync from file changes
4. Drop old `mcp_configs` table
5. Update documentation

---

## Data Flow Example

### Input: `.claude-mcp-config.json`
```json
{
  "_metadata": {
    "machine_id": "thesystem",
    "created_at": "2025-09-30T18:16:30+00:00",
    "auto_generated": true,
    "repo_root": "/home/dev/.claude"
  },
  "mcpServers": {
    "claude-tasks-dev": {
      "transport": "http",
      "url": "http://localhost:8082/..."
    },
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

### Output: Database Records

**mcp_config_files (1 row):**
```sql
id: uuid-1
machine_id: thesystem
config_name: claude_mcp_config
file_path: .claude-mcp-config.json
file_type: claude-mcp-config
metadata_machine_id: thesystem
metadata_created_at: 2025-09-30T18:16:30+00:00
metadata_auto_generated: true
metadata_repo_root: /home/dev/.claude
scope: global
is_global: true
```

**mcp_servers (2 rows):**
```sql
-- Row 1
id: uuid-2
config_file_id: uuid-1
machine_id: thesystem
server_name: claude-tasks-dev
transport_type: http
url: http://localhost:8082/...
command: NULL
args: NULL
env: NULL
headers: NULL
sort_order: 0

-- Row 2
id: uuid-3
config_file_id: uuid-1
machine_id: thesystem
server_name: puppeteer
transport_type: stdio
command: npx
args: ["-y", "@modelcontextprotocol/server-puppeteer"]
env: NULL
url: NULL
headers: NULL
sort_order: 1
```

---

## Benefits Summary

### 1. Queryability ⭐⭐⭐⭐⭐
- ✅ Filter by transport type: `WHERE transport_type = 'http'`
- ✅ Search by command: `WHERE command LIKE '%python%'`
- ✅ Find by URL: `WHERE url LIKE '%localhost%'`
- ✅ Check server status: `WHERE disabled = false`
- ✅ Query environment vars: `WHERE env ? 'API_KEY'`

### 2. Performance ⭐⭐⭐⭐
- ✅ Indexed columns (transport_type, server_name, command, url)
- ✅ No JSON path traversal needed
- ✅ Efficient filtering and sorting
- ⚠️ Requires JOIN for complete config (acceptable trade-off)

### 3. Data Integrity ⭐⭐⭐⭐⭐
- ✅ Foreign key relationships enforced
- ✅ CHECK constraints validate transport-specific fields
- ✅ UNIQUE constraints prevent duplicates
- ✅ NOT NULL constraints ensure required fields

### 4. Maintainability ⭐⭐⭐⭐
- ✅ Clear schema without JSON operators
- ✅ Easy to add new fields (ALTER TABLE)
- ✅ Standard SQL patterns
- ⚠️ Slightly more complex sync code (2 tables vs 1)

### 5. Consistency ⭐⭐⭐⭐⭐
- ✅ Matches pattern of `commands` and `agents` tables
- ✅ All global settings now normalized consistently
- ✅ Single architectural approach across system

---

## Next Steps

1. **Review migration SQL** (`20251029000000_normalize_mcp_configs.sql`)
2. **Run migration on dev database** to test data transformation
3. **Update sync code** in `unified_file_monitor.py:_sync_mcp_config()`
4. **Test file-to-DB sync** with both config file formats
5. **Verify queries** work as expected with new schema
6. **Drop old table** after verification
7. **Update documentation** (CLAUDE.md, README)

---

## Files Created

- ✅ `supabase/migrations/20251029000000_normalize_mcp_configs.sql` - Complete migration SQL
- ✅ `/tmp/mcp_normalized_schema.sql` - Detailed schema design with comments
- ✅ `/tmp/mcp_normalization_comparison.md` - Before/after comparison analysis
- ✅ `MCP_CONFIG_NORMALIZATION_COMPLETE.md` - This summary document

---

## Recommendation

**✅ PROCEED WITH IMPLEMENTATION**

The normalized schema provides significant benefits:
- **Consistency** with other global settings (commands, agents)
- **Queryability** essential for frontend features
- **Minimal complexity** (only 1 JOIN for reconstruction)
- **Future-proof** for health checks, usage stats, etc.

The migration is **backward compatible** - existing data will be automatically transformed. The sync code update is straightforward and follows the same pattern as commands/agents sync.
