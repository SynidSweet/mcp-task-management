#!/usr/bin/env python3
"""
Fix prod project by creating machine config and updating database
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from supabase import create_client

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    print("=" * 80)
    print("FIX PROD PROJECT - MACHINE ID SETUP")
    print("=" * 80)
    print()

    prod_path = Path("/home/dev/projects/mcp-management-system/prod/mcp-server")

    if not prod_path.exists():
        print(f"✗ Prod directory not found: {prod_path}")
        sys.exit(1)

    print(f"✓ Prod path: {prod_path}")
    print()

    # Step 1: Create machine config for prod
    print("-" * 80)
    print("STEP 1: CREATE MACHINE CONFIG FOR PROD")
    print("-" * 80)

    config_file = prod_path / ".claude-machine-config.json"

    if config_file.exists():
        print(f"✓ Machine config already exists")
        with open(config_file, 'r') as f:
            config = json.load(f)
        machine_id = config.get('machine_id')
        print(f"  Machine ID: {machine_id}")
    else:
        print("Creating machine config...")
        machine_id = "prod-machine"
        config = {
            "machine_id": machine_id,
            "description": "Production machine for MCP server",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Created machine config: {config_file}")
        print(f"  Machine ID: {machine_id}")

    print()

    # Step 2: Update database
    print("-" * 80)
    print("STEP 2: UPDATE DATABASE PROJECT")
    print("-" * 80)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Find prod project by path
        result = client.table('projects').select('*')\
            .eq('path', str(prod_path))\
            .execute()

        if not result.data:
            print(f"✗ No project found with path: {prod_path}")
            print("  Creating new project...")

            new_project = {
                'name': 'mcp-server',
                'path': str(prod_path),
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
            project = result.data[0]
            project_id = project['id']

            print(f"Found project: {project_id}")
            print(f"  Current machine_id: {project.get('machine_id')}")

            if project.get('machine_id') == machine_id:
                print(f"✓ Project already has correct machine_id")
            else:
                print(f"  Updating to: {machine_id}")

                result = client.table('projects')\
                    .update({'machine_id': machine_id})\
                    .eq('id', project_id)\
                    .execute()

                if result.data:
                    print(f"✓ Updated project machine_id")
                else:
                    print(f"✗ Failed to update project")
                    sys.exit(1)

        print()

        # Step 3: Verify
        print("-" * 80)
        print("STEP 3: VERIFY")
        print("-" * 80)

        result = client.table('projects').select('*')\
            .eq('path', str(prod_path))\
            .eq('machine_id', machine_id)\
            .execute()

        if result.data:
            print("✓ Verification successful!")
            proj = result.data[0]
            print()
            print("Prod project details:")
            print(f"  ID: {proj['id']}")
            print(f"  Name: {proj['name']}")
            print(f"  Path: {proj['path']}")
            print(f"  Machine ID: {proj['machine_id']}")
        else:
            print("✗ Verification failed")
            sys.exit(1)

        print()
        print("=" * 80)
        print("PROD PROJECT FIX COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
