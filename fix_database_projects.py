#!/usr/bin/env python3
"""
Fix orphaned projects in database by setting machine_id and project_path
"""
import sys
from supabase import create_client
from core.machine_id import get_machine_id
from pathlib import Path

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("DATABASE PROJECT FIX SCRIPT")
    print("=" * 80)
    print()

    try:
        # Get machine ID
        machine_id = get_machine_id()
        print(f"✓ Machine ID: {machine_id}")
        print()

        # Get current project path
        project_path = str(Path.cwd().resolve())
        print(f"✓ Project path: {project_path}")
        print()

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Check for existing projects
        print("-" * 80)
        print("STEP 1: CHECKING EXISTING PROJECTS")
        print("-" * 80)

        result = client.table("projects").select("*").execute()

        if not result.data:
            print("✓ No projects found - will create new one")
            create_project = True
            project_to_update = None
        else:
            print(f"Found {len(result.data)} existing project(s):")
            for proj in result.data:
                print(f"  - ID: {proj['id']}")
                print(f"    Name: {proj.get('name')}")
                print(f"    Path: {proj.get('path')}")
                print(f"    Machine ID: {proj.get('machine_id')}")
                print()

            # Strategy: Update the first project, delete others
            project_to_update = result.data[0]['id']
            create_project = False

        print()
        print("-" * 80)
        print("STEP 2: FIXING PROJECT RECORDS")
        print("-" * 80)

        if create_project:
            # Create new project with correct data
            print("Creating new project...")
            new_project = {
                'name': 'mcp-server',
                'path': project_path,
                'machine_id': machine_id
            }
            result = client.table('projects').insert(new_project).execute()

            if result.data:
                print(f"✓ Created project: {result.data[0]['id']}")
                project_id = result.data[0]['id']
            else:
                print("✗ Failed to create project")
                sys.exit(1)

        else:
            # Update first project
            print(f"Updating project {project_to_update}...")
            update_data = {
                'path': project_path,
                'machine_id': machine_id,
                'name': 'mcp-server'
            }
            result = client.table('projects')\
                .update(update_data)\
                .eq('id', project_to_update)\
                .execute()

            if result.data:
                print(f"✓ Updated project {project_to_update}")
                project_id = project_to_update
            else:
                print(f"✗ Failed to update project {project_to_update}")
                sys.exit(1)

            # Delete duplicate projects
            if len(result.data) > 1:
                print()
                print("Deleting duplicate projects...")
                for proj in result.data[1:]:
                    dup_id = proj['id']
                    print(f"  Deleting project {dup_id}...")
                    del_result = client.table('projects').delete().eq('id', dup_id).execute()
                    if del_result:
                        print(f"  ✓ Deleted {dup_id}")
                    else:
                        print(f"  ✗ Failed to delete {dup_id}")

        print()
        print("-" * 80)
        print("STEP 3: VERIFYING FIX")
        print("-" * 80)

        # Verify project exists with correct data
        result = client.table('projects')\
            .select('*')\
            .eq('machine_id', machine_id)\
            .eq('path', project_path)\
            .execute()

        if result.data:
            print("✓ Verification successful!")
            print()
            print("Project details:")
            proj = result.data[0]
            print(f"  ID: {proj['id']}")
            print(f"  Name: {proj['name']}")
            print(f"  Path: {proj['path']}")
            print(f"  Machine ID: {proj['machine_id']}")
            print()

            project_id = proj['id']
        else:
            print("✗ Verification failed - project not found")
            sys.exit(1)

        print()
        print("-" * 80)
        print("STEP 4: CHECKING DATA VISIBILITY")
        print("-" * 80)

        # Check if we can now see data for this project
        tables = ['tasks', 'sprints', 'journal_sessions', 'specifications', 'documentation']

        for table in tables:
            try:
                result = client.table(table).select('id').eq('project_id', project_id).execute()
                count = len(result.data) if result.data else 0
                print(f"  {table}: {count} record(s)")
            except Exception as e:
                print(f"  {table}: error - {e}")

        print()
        print("=" * 80)
        print("FIX COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Run audit_database.py to verify data visibility")
        print("  2. Check frontend to confirm data appears")
        print("  3. Test file sync by editing local files")
        print()

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
