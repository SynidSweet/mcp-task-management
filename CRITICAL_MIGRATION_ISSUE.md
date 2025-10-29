# CRITICAL: Migration System Not Working

**Date**: 2025-10-28
**Severity**: 🚨 **CRITICAL**
**Status**: ❌ **MIGRATIONS HAVE NOT BEEN EXECUTING**

---

## Executive Summary

**The `exec_ddl` RPC function returns "Success" but does NOT actually execute DDL statements.**

All migrations run through `run_migration.py` have appeared to succeed but **no schema changes have been applied to the database**.

---

## Discovery

### Test 1: Foreign Key Constraint

**Expected**: Composite FK constraint prevents invalid inserts
**Actual**: Invalid insert SUCCEEDS (no FK constraint exists)

```python
# This should FAIL but SUCCEEDS
client.table('tasks').insert({
    'project_id': '00000000-0000-0000-0000-000000000000',  # Doesn't exist
    'machine_id': 'nonexistent-machine',                   # Doesn't exist
    # ...
}).execute()

# Result: ✗ Insert succeeded - FK constraint NOT enforced
```

### Test 2: UNIQUE Constraint on Path

**Expected**: Path UNIQUE constraint removed by migration
**Actual**: UNIQUE constraint STILL EXISTS

```python
# Try to insert duplicate path
client.table('projects').insert({
    'path': '/home/dev/projects/mcp-management-system/dev/mcp-server',  # Duplicate
    # ...
}).execute()

# Result: Error - duplicate key violates unique constraint "projects_path_key"
# ✗ UNIQUE constraint was NOT removed
```

### Test 3: exec_ddl Function

**Test**:
```python
result = client.rpc('exec_ddl', {'sql_statement': 'SELECT 1'}).execute()
# Returns: data='Success'
```

**Problem**: Function exists and returns 'Success', but doesn't actually execute the SQL!

---

## Impact

### Migrations That DID NOT Actually Run

1. ✗ `20251028000000_fix_project_creation_machine_id.sql`
   - Updated get_or_create_project RPC function
   - **Status**: NOT applied

2. ✗ `20251028000001_file_based_project_id.sql`
   - Drop UNIQUE constraint on path
   - Change PRIMARY KEY to composite (id, machine_id)
   - **Status**: NOT applied
   - **Critical**: Database still has wrong schema!

3. ✗ `20251028000002_fix_composite_foreign_keys.sql`
   - Add machine_id to specifications_validated
   - Drop single-column FK constraints
   - Add composite FK constraints
   - **Status**: NOT applied

### Current Database State (WRONG)

```sql
-- Projects table (INCORRECT)
PRIMARY KEY: (id)                    ← Should be (id, machine_id)
UNIQUE CONSTRAINT: projects_path_key ← Should be removed

-- Tasks table (INCORRECT)
FOREIGN KEY: project_id REFERENCES projects(id)  ← Should be (project_id, machine_id)

-- specifications_validated table (INCOMPLETE)
Missing machine_id column            ← Should have been added
```

### What Still Works

✅ **Application code**: Already uses correct patterns (queries by both columns)
✅ **Data**: Exists and is accessible
✅ **Local files**: project_id files created
✅ **Code changes**: All properly implemented

**Problem**: Database schema doesn't match what code expects!

---

## Why System Appears to Work

1. **Application code is defensive**: Queries by both fields even though FK only checks one
2. **Data happens to be valid**: Existing data doesn't violate constraints
3. **No referential integrity needed yet**: Haven't tried to delete projects or insert invalid refs

**But this is a ticking time bomb**: First time someone tries to:
- Delete a project (CASCADE won't work properly)
- Insert task with invalid project_id (won't be caught)
- Query across machines (composite key doesn't exist)

---

## Root Cause Analysis

### exec_ddl Function Investigation

**What we know**:
1. `exec_ddl` exists (doesn't error)
2. Returns `data='Success'` for any SQL
3. Does NOT actually execute the SQL
4. Not defined in our migrations

**Possible explanations**:
1. Supabase created a stub function that doesn't do anything
2. Function exists but user doesn't have permissions
3. Function has different signature than we're using
4. Function is disabled/deprecated

---

## Solutions

### Option 1: Manual Migration (RECOMMENDED)

**User manually runs SQL in Supabase SQL Editor**:

1. Go to: https://yxyfiatdrgelnvxopdsm.supabase.co
2. Open SQL Editor
3. Run migrations in order:
   - `20251028000001_file_based_project_id.sql`
   - `20251028000002_fix_composite_foreign_keys.sql`
4. Verify with test queries

**Pros**: Guaranteed to work
**Cons**: Manual step required

### Option 2: Direct PostgreSQL Connection

**Use psycopg2 or similar for direct connection**:

```python
import psycopg2

# Get DATABASE_URL from Supabase
# Format: postgres://user:pass@host:port/database
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute(sql)
conn.commit()
```

**Pros**: Automated, works like real migrations
**Cons**: Need database URL (not just API key), need psycopg2 installed

### Option 3: Create Real exec_ddl Function

**Create a Supabase function that actually executes DDL**:

```sql
CREATE OR REPLACE FUNCTION exec_ddl(sql_statement TEXT)
RETURNS TEXT AS $$
BEGIN
    EXECUTE sql_statement;
    RETURN 'Success';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Pros**: Future migrations work automatically
**Cons**: Need to run this manually first

### Option 4: Supabase CLI

**Use Supabase CLI for migrations**:

```bash
supabase db push
```

**Pros**: Official migration tool
**Cons**: Need Supabase CLI installed and configured

---

## Recommended Immediate Action

1. **Manual Migration** (Option 1):
   - User runs SQL in Supabase SQL Editor
   - Verify changes applied
   - Continue with proper migration tool going forward

2. **Fix Migration System**:
   - Create real exec_ddl function OR
   - Use direct PostgreSQL connection OR
   - Install and use Supabase CLI

---

## Verification Checklist

After running migrations manually, verify:

```sql
-- 1. Check primary key is composite
\d projects
-- Should show: PRIMARY KEY (id, machine_id)

-- 2. Check path constraint removed
\d projects
-- Should NOT show: UNIQUE projects_path_key

-- 3. Check FK constraints are composite
\d tasks
-- Should show: FOREIGN KEY (project_id, machine_id) REFERENCES projects(id, machine_id)

-- 4. Test FK enforcement
INSERT INTO tasks (id, project_id, machine_id, title, ...)
VALUES ('TEST', '00000000-0000-0000-0000-000000000000', 'fake', 'Test', ...);
-- Should FAIL with FK violation
```

---

## Files to Run Manually

1. **`supabase/migrations/20251028000001_file_based_project_id.sql`**
   - Changes projects table structure
   - Run this FIRST

2. **`supabase/migrations/20251028000002_fix_composite_foreign_keys.sql`**
   - Fixes foreign key constraints
   - Run AFTER the first one

---

## Prevention

### Short Term
- Document that migrations must be run manually
- Update run_migration.py to warn about exec_ddl limitations

### Long Term
- Implement proper migration runner using psycopg2
- Or use Supabase CLI
- Or create real exec_ddl function
- Add verification step to all migrations

---

## Status

**Database Schema**: ❌ INCORRECT (migrations not applied)
**Application Code**: ✅ CORRECT (already updated)
**Local Files**: ✅ CORRECT (project_id files created)
**Migration Files**: ✅ CORRECT (ready to run manually)

**Next Step**: User must manually run migrations in Supabase SQL Editor

---

## Migration Scripts Ready to Run

Both migration files are complete and ready:
- `/mcp-server/supabase/migrations/20251028000001_file_based_project_id.sql` (218 lines)
- `/mcp-server/supabase/migrations/20251028000002_fix_composite_foreign_keys.sql` (399 lines)

**Instructions**: Copy content and paste into Supabase SQL Editor, run in order.
