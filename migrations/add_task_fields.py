#!/usr/bin/env python3
"""
Migration: Add dependencies and completed_at fields to tasks table

Adds:
- dependencies (JSONB) - stores {blocks: [], blocked_by: [], related: []}
- completed_at (TIMESTAMPTZ) - timestamp when task was completed
"""

try:
    from supabase import create_client

    # Connect to database
    url = "https://yxyfiatdrgelnvxopdsm.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

    client = create_client(url, key)

    print("🔄 Adding dependencies and completed_at columns to tasks table...")

    # Note: We can't add columns via supabase-py client directly
    # This would need to be done via SQL in Supabase dashboard or psql

    sql_migration = """
-- Add dependencies column (JSONB) to store task relationships
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS dependencies JSONB DEFAULT '{"blocks": [], "blocked_by": [], "related": []}'::jsonb;

-- Add completed_at column (TIMESTAMPTZ) to track completion time
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Add comment for documentation
COMMENT ON COLUMN tasks.dependencies IS 'Task dependencies: {blocks: [task_ids], blocked_by: [task_ids], related: [task_ids]}';
COMMENT ON COLUMN tasks.completed_at IS 'Timestamp when task was marked as completed';
"""

    print("\n📝 SQL Migration:")
    print("=" * 60)
    print(sql_migration)
    print("=" * 60)

    print("\n⚠️  This migration must be run via Supabase Dashboard or psql:")
    print("   1. Go to Supabase Dashboard → SQL Editor")
    print("   2. Paste the SQL above")
    print("   3. Run the query")
    print("\nOr via psql:")
    print(f"   psql {url.replace('https://', 'postgresql://postgres:PASSWORD@').replace('.supabase.co', '.supabase.co:5432/postgres')}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
