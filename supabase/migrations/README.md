# Database Migrations

This directory contains SQL migration files for the MCP server database.

## Running Migrations

Supabase doesn't support programmatic DDL execution via the Python client. Migrations must be run manually through the SQL Editor.

### Manual Migration Process

1. **Open Supabase SQL Editor**
   - URL: https://yxyfiatdrgelnvxopdsm.supabase.co
   - Navigate to: SQL Editor

2. **Copy migration SQL**
   - Open the migration file (e.g., `20251016000000_drop_specification_path.sql`)
   - Copy the SQL content

3. **Execute in SQL Editor**
   - Paste SQL into the editor
   - Click "Run" or press Ctrl+Enter
   - Verify success message

4. **Verify migration**
   - Run verification queries to confirm changes
   - Check table structure with `\d specifications` or similar

### Alternative: Use Supabase CLI

If you have Supabase CLI installed:

```bash
# Link to remote project
supabase link --project-ref yxyfiatdrgelnvxopdsm

# Run migrations
supabase db push
```

## Migration Files

Migrations are named with timestamp prefix: `YYYYMMDDHHMMSS_description.sql`

| File | Date | Description |
|------|------|-------------|
| `20250904214500_claude_tasks_schema.sql` | 2025-09-04 | Initial schema |
| `20250905155806_requirements_schema.sql` | 2025-09-05 | Requirements/specs |
| `20250907113227_requirements_schema.sql` | 2025-09-07 | Requirements update |
| `20250907114814_add_templates_schema.sql` | 2025-09-07 | Templates table |
| `20250909000000_add_document_system.sql` | 2025-09-09 | Document system |
| `20250909100000_add_implemented_validated_fields.sql` | 2025-09-09 | Status fields |
| `20251016000000_drop_specification_path.sql` | 2025-10-16 | Drop specification_path column |
| `20251020000000_add_specification_validation_tables.sql` | 2025-10-20 | **Add validation tables** |

## Latest Migration: Add Specification Validation Tables

**Status:** ✅ COMPLETED (2025-10-23)

**What it does:**
- Creates `specifications_validated` table (exact mirror of specifications)
- Creates `specification_requirements_validated` table (simple copy)
- Creates `specification_constraints_validated` table (simple copy)
- Adds indexes for performance
- Enables AI suggestion vs human validation workflow

**Why:**
- Separates AI agent suggestions from human-approved specifications
- Frontend can show diffs between current (AI suggested) and validated (human approved)
- No ID linkage for requirements/constraints - frontend handles diff comparison

**Verification after running:**
```sql
-- Check new tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE '%validated%'
  AND table_schema = 'public';

-- Should return:
-- specifications_validated
-- specification_requirements_validated
-- specification_constraints_validated
```
