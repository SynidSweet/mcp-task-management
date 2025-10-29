# Database Audit Report - MCP Management System

**Date**: 2025-10-28
**Project**: mcp-management-system/dev/mcp-server
**Issue**: Frontend agent reports no MCP data in database

---

## Executive Summary

**ROOT CAUSE IDENTIFIED**: Projects in database have NULL `machine_id` and NULL `project_path`, preventing proper project identification and data isolation.

### Critical Findings

1. ✗ **Two orphaned projects in database** with NULL machine_id
2. ✗ **No machine_id.txt file** in project config (though .claude-machine-config.json exists)
3. ✗ **Projects not properly initialized** with machine_id during creation
4. ✗ **All data (tasks, sprints, journal, specs, docs) is invisible** because project_id can't be determined

---

## Database State

### Projects Table
```
Project 1:
  - ID: 19717129-ac4d-4268-9b80-5a4a4643eeb1
  - Name: mcp-server
  - machine_id: NULL ❌
  - path: NULL ❌

Project 2:
  - ID: 6f46af87-336f-4c62-8f2a-5803bac54083
  - Name: mcp-server
  - machine_id: NULL ❌
  - path: NULL ❌
```

**Analysis**: Both projects have NULL values for critical identification fields. This makes it impossible to:
- Identify which project this local installation belongs to
- Query data by project_id
- Isolate data between different projects

### Data Tables (tasks, sprints, journal, specs, docs)
**Status**: Not queried because project_id couldn't be determined

---

## Local File System State

### Machine ID Configuration

#### .claude-machine-config.json ✓
```json
{
  "machine_id": "test-machine",
  "description": "Test machine for MCP document tools validation",
  "created_at": "2025-10-12T00:00:00Z",
  "version": "1.0"
}
```
**Location**: `/home/dev/projects/mcp-management-system/dev/mcp-server/.claude-machine-config.json`
**Status**: EXISTS and has valid machine_id

#### machine_id.txt ✗
**Location**: Should be at `.claude-tasks/config/machine_id.txt`
**Status**: MISSING

**Impact**: Some code may look for machine_id.txt instead of .claude-machine-config.json

### Project Data Files

All data files exist and are initialized:
- ✓ `.claude-tasks/data/tasks.json` (exists)
- ✓ `.claude-tasks/data/sprints.json` (exists)
- ✓ `.claude-tasks/data/journal.json` (exists)
- ✓ `.claude-tasks/data/backlog.json` (exists)

---

## Root Cause Analysis

### Problem 1: Inconsistent machine_id Sources

**Code uses two different approaches:**

1. **Core system** (`core/machine_id.py`):
   - Reads from `.claude-machine-config.json` ✓
   - Located in MCP server directory root
   - Currently working correctly

2. **Legacy references** (possibly):
   - May look for `.claude-tasks/config/machine_id.txt`
   - This file doesn't exist

### Problem 2: Project Creation Without machine_id

**Two implementations of `get_or_create_project_id()`:**

1. **document_tools.py** (line 58):
   ```python
   def get_or_create_project_id(project_path):
       # Creates project with name and path
       # ❌ DOES NOT SET machine_id
       new_project = {
           'name': project_name,
           'path': str(project_path)
       }
       result = client.table('projects').insert(new_project).execute()
   ```

2. **specification_tools.py** (line 602):
   ```python
   def get_or_create_project_id(project_path):
       # Uses RPC function 'get_or_create_project'
       # ❌ RPC function also doesn't set machine_id
       result = client.rpc('get_or_create_project', {
           'project_path': str(project_path),
           'project_name': os.path.basename(str(project_path))
       }).execute()
   ```

**Database RPC Function** (`supabase/migrations/20250904214500_claude_tasks_schema.sql:155`):
```sql
CREATE OR REPLACE FUNCTION get_or_create_project(project_path TEXT, project_name TEXT DEFAULT NULL)
RETURNS UUID AS $$
BEGIN
    -- ❌ DOES NOT SET machine_id
    INSERT INTO projects (path, name) VALUES (project_path, default_name)
    RETURNING id INTO project_id;
    RETURN project_id;
END;
$$ LANGUAGE plpgsql;
```

### Problem 3: File Monitor Can't Initialize Project

**UnifiedFileMonitor** depends on `get_or_create_project_id()` to sync data:
- Monitor calls `get_or_create_project_id(project_path)`
- Function creates project WITHOUT machine_id
- Monitor tries to call `get_machine_id()` for sync
- Monitor can sync IF machine_id is accessible
- BUT projects in database end up with NULL machine_id

---

## Impact Assessment

### What Works ✓
1. Local file operations (Read/Write/Edit via MCP tools)
2. Machine ID detection (`.claude-machine-config.json` exists)
3. Project directory structure
4. MCP server health checks

### What Doesn't Work ✗
1. **Database queries** - Can't identify which project to query
2. **Frontend data display** - No project_id means no data visible
3. **Cross-machine sync** - Projects have no machine_id for isolation
4. **Project identification** - Two projects with same name and NULL fields

---

## Recommended Fixes

### Fix 1: Update Existing Projects (Immediate)

**Update both orphaned projects with proper machine_id:**

```sql
-- Option A: Update project with current project path
UPDATE projects
SET machine_id = 'test-machine',
    path = '/home/dev/projects/mcp-management-system/dev/mcp-server'
WHERE id = '19717129-ac4d-4268-9b80-5a4a4643eeb1';

-- Delete duplicate project
DELETE FROM projects
WHERE id = '6f46af87-336f-4c62-8f2a-5803bac54083';
```

### Fix 2: Update get_or_create_project_id() Functions (Code Fix)

**Update document_tools.py:**
```python
def get_or_create_project_id(project_path):
    from core.machine_id import get_machine_id

    machine_id = get_machine_id()

    # Try to find by path AND machine_id
    result = client.table('projects').select('id')\
        .eq('path', str(project_path))\
        .eq('machine_id', machine_id)\
        .execute()

    if result.data:
        return result.data[0]['id'], None

    # Create with machine_id
    new_project = {
        'name': os.path.basename(str(project_path)),
        'path': str(project_path),
        'machine_id': machine_id  # ✓ ADD THIS
    }
    result = client.table('projects').insert(new_project).execute()
    return result.data[0]['id'], None
```

### Fix 3: Update Database RPC Function (Migration)

**Create new migration:**
```sql
-- Update get_or_create_project to accept machine_id
CREATE OR REPLACE FUNCTION get_or_create_project(
    project_path TEXT,
    project_name TEXT DEFAULT NULL,
    p_machine_id TEXT DEFAULT NULL  -- Add this parameter
)
RETURNS UUID AS $$
DECLARE
    project_id UUID;
    default_name TEXT;
BEGIN
    -- Try to find existing project by path and machine_id
    SELECT id INTO project_id
    FROM projects
    WHERE path = project_path
      AND (p_machine_id IS NULL OR machine_id = p_machine_id);

    IF project_id IS NULL THEN
        -- Create with machine_id
        default_name := COALESCE(project_name, split_part(project_path, '/', -1));
        INSERT INTO projects (path, name, machine_id)
        VALUES (project_path, default_name, p_machine_id)
        RETURNING id INTO project_id;
    END IF;

    RETURN project_id;
END;
$$ LANGUAGE plpgsql;
```

### Fix 4: Consolidate machine_id Sources (Optional)

**Either:**
1. Create `machine_id.txt` symlink to centralized config
2. Update all code to use centralized `core/machine_id.py`
3. Remove legacy machine_id.txt references

---

## Testing Plan

### 1. Fix Database State
```bash
python3 fix_database_projects.py
```

### 2. Verify Data Visibility
```bash
python3 audit_database.py
# Should now show data for the project
```

### 3. Test Frontend
- Frontend should now see tasks, sprints, journal entries, etc.

### 4. Test File Sync
- Edit local tasks.json
- Verify changes sync to database
- Check that machine_id is preserved

---

## Files to Update

1. `tools/document_tools.py` - Fix `get_or_create_project_id()`
2. `tools/specification_tools.py` - Fix `get_or_create_project_id()`
3. `supabase/migrations/YYYYMMDDHHMMSS_fix_project_creation.sql` - Update RPC function
4. **NEW** `fix_database_projects.py` - Script to fix existing orphaned projects

---

## Prevention

### Code Review Checklist
- [ ] All project creation must set machine_id
- [ ] Project queries should filter by machine_id
- [ ] Test with multiple projects to ensure isolation
- [ ] Verify frontend can see data after project creation

### Testing Requirements
- [ ] Integration test: Create project → verify machine_id set
- [ ] Integration test: Query data → verify project isolation
- [ ] Integration test: Frontend → verify data visibility
- [ ] End-to-end test: File change → database sync → frontend update

---

## Appendix: Investigation Commands

```bash
# Check machine config
cat /home/dev/projects/mcp-management-system/dev/mcp-server/.claude-machine-config.json

# Check for machine_id.txt
ls -la .claude-tasks/config/

# Run audit
python3 audit_database.py

# Check health
mcp__claude-tasks__system_health_check

# Query database directly
psql $DATABASE_URL -c "SELECT * FROM projects;"
```
