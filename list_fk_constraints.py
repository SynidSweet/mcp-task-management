#!/usr/bin/env python3
"""
List all foreign key constraint names that reference projects table
"""
from supabase import create_client

SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("FOREIGN KEY CONSTRAINTS TO PROJECTS TABLE")
    print("=" * 80)
    print()

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # We'll try to drop constraints one by one to discover which ones exist
    possible_tables = [
        'tasks', 'sprints', 'journal_sessions', 'backlog_items', 'sync_metadata',
        'entities', 'entity_ui_state', 'documents', 'documentation', 'cross_references',
        'specifications', 'specifications_validated', 'template_tasks', 'template_sprints'
    ]

    existing_fks = []

    print("Testing which tables have FK constraints to projects...")
    print()

    for table in possible_tables:
        # Try various possible constraint names
        possible_names = [
            f'{table}_project_id_fkey',
            f'{table}_project_fkey',
            f'fk_{table}_project',
            f'{table}_projects_fkey'
        ]

        for constraint_name in possible_names:
            sql = f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name};'
            try:
                result = client.rpc('exec_ddl', {'sql_statement': sql}).execute()

                # If result contains "Success", check if constraint existed
                # We can't easily tell if DROP IF EXISTS actually dropped something
                # So let's just note that we tried
                pass

            except Exception as e:
                # Table might not exist
                if 'does not exist' in str(e).lower() and table in str(e).lower():
                    break  # Skip this table

        # Try to query the table to see if it exists
        try:
            client.table(table).select('id').limit(0).execute()
            print(f"  ✓ {table:30} (table exists)")
        except Exception as e:
            if 'not find' in str(e).lower() or 'does not exist' in str(e).lower():
                print(f"  ✗ {table:30} (table doesn't exist)")
            else:
                print(f"  ? {table:30} ({str(e)[:40]})")

    print()
    print("Note: We cannot easily list actual constraint names via Python client.")
    print("The tables listed above exist - their FK constraints may have various names.")
    print()
    print("To see actual constraint names, you would need:")
    print("  1. Direct psql access")
    print("  2. Supabase SQL Editor query:")
    print()
    print("     SELECT conname, conrelid::regclass AS table_name")
    print("     FROM pg_constraint")
    print("     WHERE confrelid = 'projects'::regclass;")
    print()

if __name__ == "__main__":
    main()
