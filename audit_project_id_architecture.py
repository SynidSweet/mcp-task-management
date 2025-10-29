#!/usr/bin/env python3
"""
Audit project_id architecture to understand multi-machine behavior
"""
import sys
from pathlib import Path
from supabase import create_client

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("PROJECT_ID ARCHITECTURE AUDIT")
    print("=" * 80)
    print()

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Check projects table schema and constraints
        print("-" * 80)
        print("1. PROJECTS TABLE SCHEMA")
        print("-" * 80)

        # Get sample project to see columns
        result = client.table('projects').select('*').limit(1).execute()
        if result.data:
            print("Columns in projects table:")
            for key in result.data[0].keys():
                print(f"  - {key}")
        print()

        # Check if path has UNIQUE constraint by trying to understand current data
        result = client.table('projects').select('path, machine_id').execute()
        if result.data:
            paths = {}
            for proj in result.data:
                path = proj['path']
                machine_id = proj.get('machine_id')
                if path not in paths:
                    paths[path] = []
                paths[path].append(machine_id)

            print(f"Total projects: {len(result.data)}")
            print(f"Unique paths: {len(paths)}")

            duplicates = {p: m for p, m in paths.items() if len(m) > 1}
            if duplicates:
                print(f"⚠️  Paths with multiple machine_ids: {len(duplicates)}")
                for path, machine_ids in duplicates.items():
                    print(f"  - {path}: {machine_ids}")
            else:
                print("✓ Each path appears only once (path likely has UNIQUE constraint)")
        print()

        # Check tasks table schema
        print("-" * 80)
        print("2. TASKS TABLE SCHEMA")
        print("-" * 80)

        result = client.table('tasks').select('*').limit(1).execute()
        if result.data:
            print("Columns in tasks table:")
            for key in result.data[0].keys():
                print(f"  - {key}")

            has_machine_id = 'machine_id' in result.data[0]
            if has_machine_id:
                print("\n✓ Tasks have machine_id column (state separation per machine)")
            else:
                print("\n✗ Tasks DO NOT have machine_id column (no per-machine state)")
        print()

        # Check current implementation behavior
        print("-" * 80)
        print("3. CURRENT IMPLEMENTATION BEHAVIOR")
        print("-" * 80)

        sys.path.insert(0, str(Path(__file__).parent))
        from tools.document_tools import get_or_create_project_id
        from core.machine_id import get_machine_id

        current_machine = get_machine_id()
        print(f"Current machine_id: {current_machine}")
        print()

        # Test with current directory
        test_path = Path.cwd()
        print(f"Testing with path: {test_path}")

        project_id, error = get_or_create_project_id(test_path)
        if error:
            print(f"✗ Error: {error}")
        else:
            print(f"✓ Returned project_id: {project_id}")

            # Check what's in database
            result = client.table('projects').select('*').eq('id', project_id).execute()
            if result.data:
                proj = result.data[0]
                print(f"  Path: {proj['path']}")
                print(f"  Machine ID: {proj.get('machine_id')}")
        print()

        # Simulate what would happen on different machine
        print("-" * 80)
        print("4. MULTI-MACHINE SCENARIO ANALYSIS")
        print("-" * 80)

        print("Current behavior:")
        print("  get_or_create_project_id() queries by:")
        print("    - path AND machine_id")
        print()

        print("What this means:")
        print("  Machine A (hetzner):")
        print("    - Path: /project/myrepo")
        print("    - Query: path='/project/myrepo' AND machine_id='hetzner'")
        print("    - Result: Creates or finds project with machine_id='hetzner'")
        print()

        print("  Machine B (other-machine):")
        print("    - Path: /project/myrepo")
        print("    - Query: path='/project/myrepo' AND machine_id='other-machine'")
        print("    - Result: Would TRY to create NEW project")
        print("    - ⚠️  BUT: path has UNIQUE constraint!")
        print("    - Outcome: INSERT would FAIL (duplicate path)")
        print()

        # Check if this is the issue
        print("-" * 80)
        print("5. ARCHITECTURAL ISSUE IDENTIFIED")
        print("-" * 80)

        print("❌ PROBLEM:")
        print("  1. Code queries by path AND machine_id")
        print("  2. Database has UNIQUE constraint on path")
        print("  3. Same repo on Machine B cannot create its own project record")
        print("  4. Same repo on Machine B would fail to initialize")
        print()

        print("✓ CORRECT ARCHITECTURE (per user requirements):")
        print("  - Same repo = SAME project_id (across all machines)")
        print("  - path identifies the project uniquely")
        print("  - machine_id tracks which machines have accessed it")
        print("  - Tasks/data have BOTH project_id AND machine_id for state separation")
        print()

        print("📋 NEEDED FIXES:")
        print("  1. get_or_create_project_id() should query by path ONLY")
        print("  2. machine_id in projects table indicates last/current machine")
        print("  3. Tasks must have machine_id column for state separation")
        print("  4. Queries filter by: project_id AND machine_id")
        print()

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
