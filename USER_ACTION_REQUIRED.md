# ⚠️ USER ACTION REQUIRED - DDL Migration Issue

**Date**: 2025-10-28
**Priority**: HIGH
**Status**: Awaiting your input

---

## What I Found (Good News!)

✅ **Your MCP backend CAN run DDL queries** - the `exec_ddl` function works perfectly
✅ **Migration runner works** - I've fixed the error detection
✅ **Code is correct** - all application code properly updated
✅ **Files are correct** - project_id files created

---

## The Issue

**Foreign key constraints are blocking the primary key change.**

When I try to run:
```sql
ALTER TABLE projects DROP CONSTRAINT projects_pkey;
```

Database returns:
```
Error: cannot drop constraint projects_pkey on table projects
because other objects depend on it
```

**Those "other objects" are foreign key constraints from child tables** (tasks, sprints, etc.).

---

## Why We're Stuck

I've tried to drop the FK constraints before changing the PK, but **I don't know the exact constraint names** in your database. I've tried:
- `tasks_project_id_fkey` ✗
- `tasks_project_fkey` ✗
- `fk_tasks_project` ✗
- `fk_tasks_project_id` ✗

Since `DROP CONSTRAINT IF EXISTS fake_name` returns "Success" (because of IF EXISTS), I can't tell if constraints are actually being dropped.

---

## What I Need From You

### Run This Query in Supabase SQL Editor

**URL**: https://yxyfiatdrgelnvxopdsm.supabase.co

**Query**:
```sql
SELECT
    tc.table_name,
    tc.constraint_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND EXISTS (
      SELECT 1 FROM information_schema.constraint_column_usage ccu
      WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.table_name = 'projects'
  )
ORDER BY tc.table_name, kcu.ordinal_position;
```

**This will show me** the actual FK constraint names so I can drop them properly.

**Expected output**: Something like:
```
table_name | constraint_name        | column_name
tasks      | tasks_projects_id_fkey | project_id
sprints    | sprints_projects_fkey  | project_id
...
```

### Then I Can

1. Create migration with **exact constraint names**
2. Run it successfully
3. Verify everything works
4. Complete the composite key implementation

---

## Alternative Options (If You Prefer)

### Option A: You Run the Entire Migration Manually

**Easiest for you, lets you see everything**:

1. Get FK constraint names (query above)
2. Manually write DROP statements with correct names
3. Run complete migration in SQL Editor
4. I verify it worked

**File to run**: `supabase/migrations/20251028000004_composite_key_simplified.sql` (but replace FK names with actual ones)

### Option B: Install psycopg2 So I Can Query Database

```bash
./venv/bin/pip install psycopg2-binary
```

**Then I can**:
- Query information_schema directly
- Discover FK constraint names automatically
- Run migrations properly
- No manual steps needed

**Note**: I'd need the PostgreSQL connection string (not just API key)

### Option C: Install Supabase CLI

```bash
npm install -g supabase
supabase link --project-ref yxyfiatdrgelnvxopdsm
```

**Then**:
```bash
supabase db push
```

This would apply all migrations properly using official Supabase tooling.

---

## Current Database State

**What's Applied**:
- ✅ Path UNIQUE constraint removed
- ✅ specifications_validated has machine_id column

**What's NOT Applied**:
- ❌ Composite PRIMARY KEY on projects
- ❌ Composite FK constraints on child tables
- ❌ Proper referential integrity

**Risk**: Medium - system works but database doesn't enforce proper constraints

---

## My Recommendation

**Best approach**: Option B (install psycopg2)

**Why**:
1. One-time setup
2. Enables me to fully manage migrations automatically
3. No manual SQL execution needed
4. I can query database structure directly
5. Future-proof for all database operations

**If not possible**: Share FK constraint names (query above) and I'll create exact migration.

---

## What Happens After We Fix This

Once composite key is properly applied:

1. ✅ Same repo recognized across machines
2. ✅ Different paths supported
3. ✅ Referential integrity enforced
4. ✅ CASCADE deletes work
5. ✅ Invalid inserts rejected
6. ✅ Frontend sees data correctly
7. ✅ Multi-machine architecture fully functional

---

## Files Ready

All prepared and waiting for FK constraint names or psycopg2 installation:

**Migrations**:
- `20251028000004_composite_key_simplified.sql` (can be customized with exact names)

**Tools**:
- `run_migration.py` (fixed error detection)
- `verify_composite_fks_final.py` (5 comprehensive tests)
- `audit_all_migrations.py` (migration status checker)

**Documentation**:
- `DDL_CAPABILITY_COMPLETE_AUDIT.md` (complete audit results)
- `USER_ACTION_REQUIRED.md` (this file)

---

## Questions?

I'm ready to:
- Generate exact migration from FK query results
- Install and configure psycopg2 if you approve
- Help troubleshoot any issues
- Explain any part of this in more detail

**What would you like me to do?**

1. Wait for FK constraint names (you run query)
2. Install psycopg2 (you approve installation)
3. Something else?

Let me know!
