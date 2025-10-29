# How to Run Migrations Manually

**Date**: 2025-10-28
**Reason**: The `exec_ddl` RPC function does not actually execute DDL statements

---

## CRITICAL Issue Discovered

The migration runner `run_migration.py` uses `client.rpc('exec_ddl')` which returns "Success" but **does NOT actually execute the SQL**. All migrations appear to have succeeded but no schema changes were applied.

---

## Migrations Pending Execution

### 1. File-Based Project ID System

**File**: `supabase/migrations/20251028000001_file_based_project_id.sql`

**Changes**:
- Remove UNIQUE constraint on path
- Change PRIMARY KEY to composite (id, machine_id)
- Add indexes

**Must run FIRST** (other migration depends on this)

### 2. Composite Foreign Key Constraints

**File**: `supabase/migrations/20251028000002_fix_composite_foreign_keys.sql`

**Changes**:
- Add machine_id column to specifications_validated
- Drop old single-column FK constraints
- Add composite FK constraints
- Add composite indexes

**Must run SECOND** (depends on migration 1)

---

## How to Run Migrations

### Step 1: Open Supabase SQL Editor

1. Go to: **https://yxyfiatdrgelnvxopdsm.supabase.co**
2. Sign in if needed
3. Navigate to **SQL Editor**

### Step 2: Run Migration 1

1. Open file: `supabase/migrations/20251028000001_file_based_project_id.sql`
2. Copy entire content
3. Paste into SQL Editor
4. Click **Run**
5. Verify output shows no errors

### Step 3: Run Migration 2

1. Open file: `supabase/migrations/20251028000002_fix_composite_foreign_keys.sql`
2. Copy entire content
3. Paste into SQL Editor
4. Click **Run**
5. Check output for verification report showing all FKs are composite

### Step 4: Verify

Run verification script:
```bash
python3 verify_composite_fks_final.py
```

Should show:
- ✓ UNIQUE constraint removed
- ✓ Composite primary key exists
- ✓ FK constraints are composite
- ✓ Invalid FK inserts are rejected

---

## Alternative: Helper Script

I've created a helper script that displays the SQL with instructions:

```bash
python3 display_migrations_for_manual_run.py
```

This will:
1. Display both migrations in correct order
2. Show exactly what to copy/paste
3. Provide step-by-step instructions

---

## Why This Happened

### exec_ddl Function

The `exec_ddl` RPC function in Supabase:
- Exists and can be called
- Returns `data='Success'`
- **Does NOT actually execute the DDL**
- Likely a placeholder or security restriction

### Previous Migrations

**Question**: Did previous migrations actually run?

Need to audit all migrations in `supabase/migrations/` to determine which ones were applied and which ones only appeared to succeed.

**Files to check**:
```bash
ls -1 supabase/migrations/*.sql
```

---

## Long-Term Solution

### Option 1: Install psycopg2 (Recommended)

```bash
./venv/bin/pip install psycopg2-binary
```

Then create proper migration runner that connects directly to PostgreSQL.

### Option 2: Use Supabase CLI

```bash
npm install -g supabase
supabase link --project-ref yxyfiatdrgelnvxopdsm
supabase db push
```

### Option 3: Create Real exec_ddl Function

Create function in Supabase that actually executes DDL:

```sql
CREATE OR REPLACE FUNCTION exec_ddl(sql_statement TEXT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    EXECUTE sql_statement;
    RETURN 'Success';
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error: ' || SQLERRM;
END;
$$;
```

**Warning**: Security implications - be careful with SECURITY DEFINER

---

## Immediate Action Required

1. ✅ Migrations are prepared and ready
2. ⏳ **USER ACTION**: Run migrations manually in Supabase SQL Editor
3. ⏳ Verify migrations applied correctly
4. ⏳ Fix migration runner for future

---

## Verification After Manual Run

```bash
# Should all pass
python3 verify_composite_fks_final.py
python3 test_file_based_project_id.py
python3 audit_database.py
```

---

## Status

**Code**: ✅ All updated correctly
**Files**: ✅ project_id files created
**Migrations**: ✅ SQL scripts ready
**Database**: ❌ **PENDING MANUAL EXECUTION**

**Blocker**: Need manual migration execution in Supabase SQL Editor

---

## Next Steps

1. User runs migrations manually (see steps above)
2. Verify with verification scripts
3. Fix migration runner for future (install psycopg2 or use Supabase CLI)
4. Audit all previous migrations to see what else needs manual execution
