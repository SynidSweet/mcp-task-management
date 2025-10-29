# DDL Execution Capability - Comprehensive Audit Report

**Date**: 2025-10-28
**Status**: 🔍 **ROOT CAUSE IDENTIFIED**

---

## Executive Summary

**exec_ddl WORKS CORRECTLY** - The migration runner is functional.

**Root Cause**: Migration #20251028000001 failed due to **incorrect statement ordering**, not exec_ddl failure.

**Issue**: Cannot drop primary key while foreign keys depend on it. Migrations must drop FKs FIRST, then change PK, then recreate FKs.

---

## Investigation Results

### Test 1: exec_ddl Basic Functionality ✅

```python
client.rpc('exec_ddl', {'sql_statement': 'CREATE TABLE test (id INT);'})
# Result: Success
# Verification: Table EXISTS and can be queried ✓
```

**Conclusion**: exec_ddl works correctly

### Test 2: exec_ddl Multiple Statements ✅

```python
sql = '''
CREATE TABLE multi_test_1 (id INTEGER);
CREATE TABLE multi_test_2 (id INTEGER);
CREATE TABLE multi_test_3 (id INTEGER);
'''
client.rpc('exec_ddl', {'sql_statement': sql})
# Result: Success
# Verification: All 3 tables EXIST ✓
```

**Conclusion**: exec_ddl handles multiple statements correctly

### Test 3: Migration Statement #1 ✅

```sql
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;
```
**Result**: Success - UNIQUE constraint WAS dropped ✓

**Verification**:
```python
# Try to insert duplicate path
client.table('projects').insert({'path': '/same/path', ...})
# Result: SUCCEEDS (constraint is gone) ✓
```

### Test 4: Migration Statement #2 ❌

```sql
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;
```
**Result**: Error - "cannot drop constraint projects_pkey on table projects because other objects depend on it"

**Verification**: Primary key change FAILED ✗

**Reason**: Foreign key constraints from child tables (tasks, sprints, etc.) depend on projects(id). Cannot drop PK while FKs reference it.

---

## Root Cause Analysis

### Why Migration Failed

**Migration 20251028000001_file_based_project_id.sql** attempted:

```sql
-- Step 1: Drop UNIQUE constraint ✓ SUCCESS
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;

-- Step 2: Drop PK ✗ FAILED
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;
-- Error: other objects depend on it (FK constraints!)

-- Step 3: Add composite PK (never executed)
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);
```

**Result**: Migration partially applied, then stopped at Step 2

### Dependency Chain

```
tasks.project_id ─────────┐
sprints.project_id ───────┤
journal_sessions.project_id ──┤
... (9 more tables)       │
                          ↓
                   FK: REFERENCES projects(id)
                          ↓
                   projects.id (PRIMARY KEY)
```

**You cannot drop projects.id PRIMARY KEY while FKs reference it!**

---

## Current Database State

### What Applied ✅
- UNIQUE constraint on path: DROPPED ✓
  - Can now insert same path with different machine_ids

### What Did NOT Apply ❌
- Primary key change: FAILED
  - Still: `PRIMARY KEY (id)`
  - Should be: `PRIMARY KEY (id, machine_id)`
- Foreign key updates: NOT ATTEMPTED (Migration 2 depends on Migration 1)

### Partial Success State

**Database is in an INCONSISTENT state**:
- ✓ Path UNIQUE constraint removed
- ✗ Primary key still single-column
- ✗ Foreign keys still single-column
- ✗ Can insert same path multiple times (without proper composite key constraints!)

**Risk**: Database allows invalid states that shouldn't be possible

---

## Correct Migration Order

### Migration Structure That Works

```sql
-- ============================================================================
-- SINGLE ATOMIC MIGRATION
-- ============================================================================

-- STEP 1: Drop all FK constraints from child tables
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_fkey;
ALTER TABLE sprints DROP CONSTRAINT IF EXISTS sprints_project_id_fkey;
-- ... all other child tables ...

-- STEP 2: Now we can drop the old PK (no dependencies)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;

-- STEP 3: Ensure machine_id is NOT NULL
ALTER TABLE projects ALTER COLUMN machine_id SET NOT NULL;

-- STEP 4: Add new composite PK
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- STEP 5: Add missing machine_id to specifications_validated
ALTER TABLE specifications_validated ADD COLUMN IF NOT EXISTS machine_id TEXT;
UPDATE specifications_validated sv SET machine_id = s.machine_id FROM specifications s WHERE sv.id = s.id;
ALTER TABLE specifications_validated ALTER COLUMN machine_id SET NOT NULL;

-- STEP 6: Recreate FK constraints as composite
ALTER TABLE tasks
ADD CONSTRAINT tasks_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

ALTER TABLE sprints
ADD CONSTRAINT sprints_project_fkey
FOREIGN KEY (project_id, machine_id)
REFERENCES projects(id, machine_id)
ON DELETE CASCADE;

-- ... all other child tables ...

-- STEP 7: Add indexes
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
CREATE INDEX IF NOT EXISTS idx_projects_id ON projects(id);
-- ... composite indexes on child tables ...
```

---

## Why This Happened

### Migration Split into Two Files

**Original approach**:
- Migration 1: Change projects table PK
- Migration 2: Update FK constraints

**Problem**: Can't change PK while FKs exist!

**Should have been**:
- Single migration: Drop FKs → Change PK → Recreate FKs

### Lesson Learned

When changing a primary key that has foreign key dependencies:
1. All FK constraint changes must be in SAME migration
2. Drop FKs first
3. Change PK
4. Recreate FKs
5. Never split across multiple migrations

---

## Solution

### Create Combined Migration

**File**: `20251028000003_composite_key_complete.sql`

This migration will:
1. Revert the partial change (restore path UNIQUE constraint temporarily)
2. Do the entire transformation in correct order
3. Apply all changes atomically

OR:

**File**: `20251028000001_file_based_project_id_corrected.sql` (replace existing)

Complete migration with proper ordering.

---

## Impact Assessment

### Current State Analysis

**Database State**:
- Projects table:
  - ✗ Primary key: (id) only
  - ✗ Path: NO UNIQUE constraint (was dropped)
  - ✓ machine_id column: exists

**Issues**:
1. Can insert duplicate paths (UNIQUE gone)
2. Cannot insert same project_id with different machine_id (PK not composite)
3. FKs still reference single-column PK
4. **Contradictory constraints**: Allows duplicate paths but not duplicate project_ids

**Risk Level**: MEDIUM
- System won't crash
- Application code works around it
- But database doesn't enforce proper multi-machine architecture

---

## Recommended Action

### Immediate: Create Corrected Migration

**New file**: `supabase/migrations/20251028000003_composite_key_atomic.sql`

**Strategy**:
1. Single atomic migration
2. Proper statement ordering
3. Combines both previous migrations
4. Tested statement-by-statement

### Testing Before Application

Test each statement individually:
```bash
python3 test_migration_statements.py
```

This will execute each statement one-by-one and report which ones succeed/fail.

---

## Files to Create

1. `20251028000003_composite_key_atomic.sql` - Corrected migration
2. `test_migration_statements.py` - Statement-by-statement tester
3. `DDL_EXECUTION_AUDIT_REPORT.md` - This file

---

## What We Learned

### ✅ Working Correctly
- exec_ddl RPC function
- Migration runner (run_migration.py)
- DDL execution capability

### ❌ Issues Found
- Migration statement ordering
- Dependency analysis not done before migration creation
- No rollback for partial failures

### 🔧 Needs Improvement
- Migration testing before running
- Dependency analysis tool
- Rollback capabilities
- Better error reporting from run_migration.py

---

## Success Criteria

After corrected migration:
- [ ] Projects table has PRIMARY KEY (id, machine_id)
- [ ] Path UNIQUE constraint removed
- [ ] All child tables have composite FK constraints
- [ ] specifications_validated has machine_id column
- [ ] Can insert same project_id with different machine_ids
- [ ] Cannot insert invalid FK references
- [ ] CASCADE DELETE works properly

---

## Next Steps

1. Create corrected atomic migration
2. Test statement-by-statement
3. Run corrected migration
4. Verify all constraints
5. Update documentation
6. Add migration testing procedures

---

**Status**: 🔍 ROOT CAUSE FOUND - exec_ddl works, migration ordering was wrong
