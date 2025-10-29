#!/usr/bin/env python3
"""
Fix database to use correct global machine_id for all projects on this computer
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client
from core.machine_id import get_machine_id

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("FIX DATABASE - USE CORRECT GLOBAL MACHINE_ID")
    print("=" * 80)
    print()

    try:
        # Get correct machine_id from global config
        machine_id = get_machine_id()
        print(f"✓ Global machine_id: {machine_id}")
        print()

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Get all projects on this computer
        dev_path = "/home/dev/projects/mcp-management-system/dev/mcp-server"
        prod_path = "/home/dev/projects/mcp-management-system/prod/mcp-server"

        print("-" * 80)
        print("STEP 1: FIND PROJECTS ON THIS COMPUTER")
        print("-" * 80)

        result = client.table('projects').select('*').in_('path', [dev_path, prod_path]).execute()

        if not result.data:
            print("✗ No projects found")
            sys.exit(1)

        print(f"✓ Found {len(result.data)} project(s):")
        for proj in result.data:
            print(f"  - {proj['path']}")
            print(f"    Current machine_id: {proj.get('machine_id')}")
        print()

        # Update all projects to use correct machine_id
        print("-" * 80)
        print(f"STEP 2: UPDATE TO CORRECT MACHINE_ID: {machine_id}")
        print("-" * 80)

        for proj in result.data:
            project_id = proj['id']
            current_machine_id = proj.get('machine_id')

            if current_machine_id == machine_id:
                print(f"✓ {proj['path']}: Already correct")
            else:
                print(f"Updating {proj['path']}...")
                print(f"  From: {current_machine_id}")
                print(f"  To:   {machine_id}")

                update_result = client.table('projects')\
                    .update({'machine_id': machine_id})\
                    .eq('id', project_id)\
                    .execute()

                if update_result.data:
                    print(f"  ✓ Updated successfully")
                else:
                    print(f"  ✗ Update failed")

        print()

        # Verify
        print("-" * 80)
        print("STEP 3: VERIFY ALL PROJECTS HAVE CORRECT MACHINE_ID")
        print("-" * 80)

        result = client.table('projects').select('*').in_('path', [dev_path, prod_path]).execute()

        all_correct = True
        for proj in result.data:
            proj_machine_id = proj.get('machine_id')
            if proj_machine_id == machine_id:
                print(f"✓ {proj['path']}: machine_id = {proj_machine_id}")
            else:
                print(f"✗ {proj['path']}: machine_id = {proj_machine_id} (WRONG)")
                all_correct = False

        print()

        if all_correct:
            print("=" * 80)
            print("✓ SUCCESS - ALL PROJECTS NOW USE CORRECT MACHINE_ID")
            print("=" * 80)
            print()
            print(f"Both dev and prod projects now correctly share:")
            print(f"  machine_id = {machine_id}")
            print()
        else:
            print("=" * 80)
            print("✗ SOME PROJECTS STILL HAVE INCORRECT MACHINE_ID")
            print("=" * 80)
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
