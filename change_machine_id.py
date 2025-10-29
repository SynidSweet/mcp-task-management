#!/usr/bin/env python3
"""
Change machine_id to 'hetzner'
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client
from core.machine_id import set_machine_id, get_machine_id

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("CHANGE MACHINE_ID TO 'hetzner'")
    print("=" * 80)
    print()

    new_machine_id = "hetzner"

    try:
        # Get current machine_id
        try:
            old_machine_id = get_machine_id()
            print(f"Current machine_id: {old_machine_id}")
        except Exception as e:
            print(f"Could not get current machine_id: {e}")
            old_machine_id = None

        print()

        # Update global config
        print("-" * 80)
        print("STEP 1: UPDATE GLOBAL CONFIG")
        print("-" * 80)

        result = set_machine_id(new_machine_id)

        if result.get('status') == 'success':
            print(f"✓ Updated global config to: {new_machine_id}")
            print(f"  Config file: {result.get('config_file')}")
        else:
            print(f"✗ Failed to update config: {result.get('error')}")
            sys.exit(1)

        print()

        # Verify we can read it back
        current_id = get_machine_id()
        if current_id == new_machine_id:
            print(f"✓ Verified: get_machine_id() returns '{current_id}'")
        else:
            print(f"✗ Verification failed: got '{current_id}', expected '{new_machine_id}'")
            sys.exit(1)

        print()

        # Update database
        print("-" * 80)
        print("STEP 2: UPDATE DATABASE PROJECTS")
        print("-" * 80)

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Get all projects that had the old machine_id
        if old_machine_id:
            result = client.table('projects').select('*').eq('machine_id', old_machine_id).execute()
        else:
            # Get all projects in our directories
            dev_path = "/home/dev/projects/mcp-management-system/dev/mcp-server"
            prod_path = "/home/dev/projects/mcp-management-system/prod/mcp-server"
            result = client.table('projects').select('*').in_('path', [dev_path, prod_path]).execute()

        if not result.data:
            print("⚠️  No projects found to update")
        else:
            print(f"Found {len(result.data)} project(s) to update:")
            for proj in result.data:
                print(f"  - {proj['path']}")

            print()
            print("Updating projects...")

            for proj in result.data:
                project_id = proj['id']
                path = proj['path']

                update_result = client.table('projects')\
                    .update({'machine_id': new_machine_id})\
                    .eq('id', project_id)\
                    .execute()

                if update_result.data:
                    print(f"  ✓ Updated {Path(path).name}")
                else:
                    print(f"  ✗ Failed to update {Path(path).name}")

        print()

        # Verify database
        print("-" * 80)
        print("STEP 3: VERIFY DATABASE")
        print("-" * 80)

        result = client.table('projects').select('*').eq('machine_id', new_machine_id).execute()

        if result.data:
            print(f"✓ Found {len(result.data)} project(s) with machine_id = '{new_machine_id}':")
            for proj in result.data:
                print(f"  - {proj['path']}")
        else:
            print(f"⚠️  No projects found with machine_id = '{new_machine_id}'")

        print()
        print("=" * 80)
        print(f"✓ SUCCESS - MACHINE_ID CHANGED TO '{new_machine_id}'")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
