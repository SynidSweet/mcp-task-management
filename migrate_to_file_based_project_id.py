#!/usr/bin/env python3
"""
Migrate existing projects to file-based project_id system
"""
import sys
from pathlib import Path
from supabase import create_client

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.project_manager import ProjectManager

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("MIGRATE EXISTING PROJECTS TO FILE-BASED PROJECT_ID SYSTEM")
    print("=" * 80)
    print()

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Get all projects from database
        print("-" * 80)
        print("STEP 1: FIND EXISTING PROJECTS IN DATABASE")
        print("-" * 80)

        result = client.table('projects').select('*').execute()

        if not result.data:
            print("✓ No projects found - nothing to migrate")
            return

        print(f"Found {len(result.data)} project(s):")
        for proj in result.data:
            print(f"  - {proj['path']} (ID: {proj['id']})")
        print()

        # Migrate each project
        print("-" * 80)
        print("STEP 2: CREATE PROJECT_ID FILES")
        print("-" * 80)

        success_count = 0
        skip_count = 0
        error_count = 0

        for proj in result.data:
            project_id = proj['id']
            project_path = Path(proj['path'])

            print(f"\nProcessing: {project_path}")

            # Check if path exists
            if not project_path.exists():
                print(f"  ⚠️  Path doesn't exist - skipping")
                skip_count += 1
                continue

            # Create ProjectManager for this project
            try:
                pm = ProjectManager(project_path)

                # Check if project_id file already exists
                existing_id = pm.read_project_id()
                if existing_id:
                    if existing_id == project_id:
                        print(f"  ✓ project_id file already exists with correct ID")
                        success_count += 1
                    else:
                        print(f"  ⚠️  project_id file exists but has different ID!")
                        print(f"      File: {existing_id}")
                        print(f"      DB:   {project_id}")
                        print(f"      Using file ID (keeping existing)")
                        success_count += 1
                    continue

                # Write project_id from database to file
                pm.write_project_id(project_id)
                print(f"  ✓ Created project_id file: {project_id}")
                success_count += 1

            except Exception as e:
                print(f"  ✗ Error: {e}")
                error_count += 1

        print()
        print("-" * 80)
        print("STEP 3: SUMMARY")
        print("-" * 80)
        print(f"Total projects: {len(result.data)}")
        print(f"  ✓ Success: {success_count}")
        print(f"  ⚠️  Skipped: {skip_count}")
        print(f"  ✗ Errors: {error_count}")
        print()

        if error_count == 0:
            print("=" * 80)
            print("✓ MIGRATION COMPLETE")
            print("=" * 80)
            print()
            print("What happened:")
            print("  - Created .claude-tasks/data/project_id files for existing projects")
            print("  - Files contain the UUID from database")
            print("  - Same project on different machines will now share project_id if")
            print("    the project_id file is committed to version control")
            print()
            print("Next steps:")
            print("  1. Commit project_id files to version control (if desired)")
            print("  2. Test that system works correctly")
            print()
        else:
            print("=" * 80)
            print(f"⚠️  MIGRATION COMPLETED WITH {error_count} ERROR(S)")
            print("=" * 80)
            print()
            print("Review errors above and retry if needed.")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
