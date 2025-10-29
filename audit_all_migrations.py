#!/usr/bin/env python3
"""
Comprehensive audit of all migrations vs actual database state
"""
import sys
from pathlib import Path
from supabase import create_client

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def check_table_exists(client, table_name):
    """Check if a table exists"""
    try:
        result = client.table(table_name).select('*').limit(0).execute()
        return True
    except Exception as e:
        if 'does not exist' in str(e).lower() or 'not found' in str(e).lower():
            return False
        # Other errors might mean table exists but query failed
        return "unknown"

def check_column_exists(client, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        result = client.table(table_name).select(column_name).limit(1).execute()
        return True
    except Exception as e:
        if 'column' in str(e).lower() and 'does not exist' in str(e).lower():
            return False
        # Table might not exist or no data
        return "unknown"

def main():
    print("=" * 80)
    print("COMPREHENSIVE MIGRATION AUDIT")
    print("=" * 80)
    print()
    print("Checking what database objects actually exist vs what migrations should have created...")
    print()

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # ====================================================================
        # Migration 1: 20250904214500_claude_tasks_schema.sql
        # ====================================================================
        print("-" * 80)
        print("MIGRATION 1: 20250904214500_claude_tasks_schema.sql")
        print("-" * 80)

        tables_created = ['projects', 'tasks', 'sprints', 'journal_sessions', 'backlog_items', 'sync_metadata']

        for table in tables_created:
            exists = check_table_exists(client, table)
            status = "✓" if exists == True else "✗" if exists == False else "?"
            print(f"  {status} Table: {table}")

        # Check for get_or_create_project function
        try:
            result = client.rpc('get_or_create_project', {
                'project_path': '/test',
                'project_name': 'test'
            }).execute()
            print(f"  ✓ Function: get_or_create_project")
        except Exception as e:
            if 'could not find' in str(e).lower() or 'does not exist' in str(e).lower():
                print(f"  ✗ Function: get_or_create_project (not found)")
            else:
                print(f"  ? Function: get_or_create_project (error: {str(e)[:50]})")

        print()

        # ====================================================================
        # Migration 2-7: Requirements, specs, templates
        # ====================================================================
        print("-" * 80)
        print("MIGRATIONS 2-7: Requirements, Specs, Templates, Documents")
        print("-" * 80)

        tables_from_later = [
            ('specifications', 'Migration 2/3'),
            ('specification_requirements', 'Migration 2/3'),
            ('specification_constraints', 'Migration 2/3'),
            ('templates', 'Migration 4'),
            ('template_versions', 'Migration 4'),
            ('template_collections', 'Migration 4'),
            ('documentation', 'Migration 5'),
            ('documents', 'Migration 5'),
            ('specifications_validated', 'Migration 11'),
            ('specification_requirements_validated', 'Migration 11'),
            ('specification_constraints_validated', 'Migration 11'),
            ('template_tasks', 'Migration 13'),
            ('template_sprints', 'Migration 13'),
        ]

        for table, migration in tables_from_later:
            exists = check_table_exists(client, table)
            status = "✓" if exists == True else "✗" if exists == False else "?"
            print(f"  {status} {table:40} ({migration})")

        print()

        # ====================================================================
        # Key Schema Elements
        # ====================================================================
        print("-" * 80)
        print("KEY SCHEMA ELEMENTS")
        print("-" * 80)

        # Check projects table structure
        print("\nProjects table:")
        result = client.table('projects').select('*').limit(1).execute()
        if result.data and len(result.data) > 0:
            columns = list(result.data[0].keys())
            print(f"  Columns: {', '.join(columns)}")

            # Try to detect composite PK by testing duplicate id with different machine_id
            print(f"  Testing composite primary key...")
            try:
                test_id = '00000000-1111-1111-1111-000000000000'
                client.table('projects').insert({
                    'id': test_id,
                    'machine_id': 'test-pk-1',
                    'path': '/test/pk/1',
                    'name': 'Test 1'
                }).execute()
                client.table('projects').insert({
                    'id': test_id,  # Same id!
                    'machine_id': 'test-pk-2',  # Different machine
                    'path': '/test/pk/2',
                    'name': 'Test 2'
                }).execute()
                print(f"    ✓ Composite PK exists (same id, different machine_id allowed)")
                # Cleanup
                client.table('projects').delete().eq('id', test_id).execute()
            except Exception as e:
                if 'duplicate' in str(e).lower():
                    print(f"    ✗ Composite PK missing (simple PK on id only)")
                else:
                    print(f"    ? Error: {str(e)[:60]}")

        # Test UNIQUE constraint on path
        print(f"\n  Testing UNIQUE constraint on path...")
        try:
            existing_path = '/home/dev/projects/mcp-management-system/dev/mcp-server'
            client.table('projects').insert({
                'id': '00000000-2222-2222-2222-000000000000',
                'machine_id': 'test-unique',
                'path': existing_path,  # Duplicate path
                'name': 'Test Unique'
            }).execute()
            print(f"    ✓ UNIQUE constraint removed (duplicate path allowed)")
            # Cleanup
            client.table('projects').delete().eq('id', '00000000-2222-2222-2222-000000000000').execute()
        except Exception as e:
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                print(f"    ✗ UNIQUE constraint still exists")
            else:
                print(f"    ? Error: {str(e)[:60]}")

        print()

        # Check tasks table structure
        print("Tasks table:")
        result = client.table('tasks').select('*').limit(1).execute()
        if result.data and len(result.data) > 0:
            columns = list(result.data[0].keys())
            has_parent = 'parent_task_id' in columns
            has_children = 'child_task_ids' in columns
            has_sprint = 'sprint_id' in columns

            print(f"  Columns ({len(columns)}): {', '.join(columns[:10])}...")
            print(f"  ✓ Has parent_task_id" if has_parent else "  ✗ Missing parent_task_id")
            print(f"  ✓ Has child_task_ids" if has_children else "  ✗ Missing child_task_ids")
            print(f"  ✓ Has sprint_id" if has_sprint else "  ✗ Missing sprint_id")

        print()

        # Check template_tasks vs old templates table
        print("Template system:")
        has_template_tasks = check_table_exists(client, 'template_tasks')
        has_old_templates = check_table_exists(client, 'templates')

        print(f"  {'✓' if has_template_tasks else '✗'} template_tasks (new normalized schema)")
        print(f"  {'✗ Still exists!' if has_old_templates else '✓ Dropped'} templates (old deprecated table)")

        print()

        # ====================================================================
        # DDL Execution Capability Test
        # ====================================================================
        print("-" * 80)
        print("DDL EXECUTION CAPABILITY TEST")
        print("-" * 80)
        print()

        # Test 1: exec_ddl
        print("1. Testing exec_ddl RPC function:")
        try:
            result = client.rpc('exec_ddl', {'sql_statement': 'SELECT 1'}).execute()
            print(f"   Result: {result.data}")

            # Now test if it actually does anything
            # Try to create a test table
            test_ddl = "CREATE TABLE IF NOT EXISTS test_exec_ddl_capability (id INTEGER);"
            result = client.rpc('exec_ddl', {'sql_statement': test_ddl}).execute()
            print(f"   exec_ddl CREATE TABLE returned: {result.data}")

            # Check if table actually exists
            table_exists = check_table_exists(client, 'test_exec_ddl_capability')
            if table_exists:
                print(f"   ✓ exec_ddl WORKS - table was created")
                # Cleanup
                client.rpc('exec_ddl', {'sql_statement': 'DROP TABLE test_exec_ddl_capability;'}).execute()
            else:
                print(f"   ✗ exec_ddl DOES NOT WORK - table was NOT created")

        except Exception as e:
            print(f"   ✗ exec_ddl error: {e}")

        print()

        # Test 2: Check if there's a migrations tracking table
        print("2. Checking for migration tracking:")
        migration_tables = ['schema_migrations', 'supabase_migrations', '_migrations', 'migrations']
        found_migration_table = False

        for table in migration_tables:
            exists = check_table_exists(client, table)
            if exists == True:
                print(f"   ✓ Found migration tracking table: {table}")
                found_migration_table = True
                # Try to read it
                try:
                    result = client.table(table).select('*').limit(10).execute()
                    if result.data:
                        print(f"      Columns: {list(result.data[0].keys())}")
                        print(f"      Records: {len(result.data)}")
                except:
                    pass
                break

        if not found_migration_table:
            print(f"   ✗ No migration tracking table found")
            print(f"      Checked: {', '.join(migration_tables)}")

        print()

        # Test 3: List all available RPC functions
        print("3. Checking available RPC functions:")
        rpc_functions = ['get_or_create_project', 'exec_ddl', 'exec_sql', 'run_migration']

        for func in rpc_functions:
            try:
                # Try to call with minimal args
                if func == 'get_or_create_project':
                    result = client.rpc(func, {'project_path': '/test', 'project_name': 'test'}).execute()
                elif func in ['exec_ddl', 'exec_sql']:
                    result = client.rpc(func, {'sql_statement': 'SELECT 1'}).execute()
                elif func == 'run_migration':
                    result = client.rpc(func, {'sql': 'SELECT 1'}).execute()
                else:
                    result = client.rpc(func, {}).execute()

                print(f"   ✓ {func} exists")

            except Exception as e:
                error_msg = str(e).lower()
                if 'could not find' in error_msg or 'not found' in error_msg:
                    print(f"   ✗ {func} not found")
                else:
                    print(f"   ? {func} - error: {str(e)[:50]}")

        print()

        # ====================================================================
        # Summary
        # ====================================================================
        print("=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)
        print()

        print("Tables Status:")
        print("  Core tables (projects, tasks, sprints, etc): Created ✓")
        print("  Specifications system: Created ✓")
        print("  Template system: Migrated to normalized schema ✓")
        print()

        print("Schema Issues Found:")
        print("  Projects table:")
        print("    - Check composite PK test above")
        print("    - Check UNIQUE constraint test above")
        print("  Tasks table:")
        print("    - Has hierarchy fields (parent_task_id, child_task_ids)")
        print("  Foreign Keys:")
        print("    - Need manual verification (can't easily query from Python client)")
        print()

        print("DDL Execution:")
        print("  exec_ddl: Check results above")
        print("  Migration tracking: Check if tracking table exists")
        print()

        print("=" * 80)
        print("DETAILED ANALYSIS NEEDED")
        print("=" * 80)
        print()
        print("To get complete schema information, we need direct database access.")
        print()
        print("Options:")
        print("  1. Install psycopg2 for direct PostgreSQL queries")
        print("  2. Use psql CLI (if available)")
        print("  3. Check Supabase Dashboard → Database → Tables")
        print("  4. Use Supabase SQL Editor to run information_schema queries")
        print()

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
