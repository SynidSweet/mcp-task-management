#!/usr/bin/env python3
"""
Verify that project_id and machine_id are correctly stored in database records.

This script queries the Supabase database to check if records actually contain
project_id and machine_id fields as expected.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.document_tools import get_supabase_client
from core.machine_id import get_machine_id, get_machine_config_path


def verify_database_ids():
    """Verify project_id and machine_id in database records."""

    print("="*70)
    print("DATABASE ID VERIFICATION")
    print("="*70)
    print()

    # Step 1: Check machine_id configuration
    print("📋 Step 1: Checking machine_id configuration...")
    print("-"*70)

    config_file = get_machine_config_path()
    print(f"Config file location: {config_file}")
    print(f"Config file exists: {config_file.exists()}")

    if not config_file.exists():
        print("❌ Machine ID not configured!")
        print(f"   Create file: {config_file}")
        print('   Content: {"machine_id": "your-machine-name", ...}')
        return False

    try:
        machine_id = get_machine_id()
        print(f"✅ Machine ID: {machine_id}")
    except Exception as e:
        print(f"❌ Error reading machine_id: {e}")
        return False

    print()

    # Step 2: Connect to database
    print("📋 Step 2: Connecting to Supabase database...")
    print("-"*70)

    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        return False

    print("✅ Connected to Supabase")
    print()

    # Step 3: Check each table for project_id and machine_id
    print("📋 Step 3: Checking database tables for IDs...")
    print("-"*70)
    print()

    tables_to_check = [
        ('tasks', 'Tasks'),
        ('sprints', 'Sprints'),
        ('journal_sessions', 'Journal Sessions'),
        ('specifications', 'Specifications'),
        ('documents', 'Documents')
    ]

    results = {}

    for table_name, display_name in tables_to_check:
        print(f"Checking {display_name} ({table_name})...")

        try:
            # Query first 5 records
            result = client.table(table_name).select('id, project_id, machine_id').limit(5).execute()

            if not result.data or len(result.data) == 0:
                print(f"  ⚠️  No records found in {table_name}")
                results[table_name] = {
                    'status': 'empty',
                    'count': 0,
                    'has_project_id': None,
                    'has_machine_id': None
                }
            else:
                records = result.data
                count = len(records)

                # Check if records have the IDs
                has_project_id = all('project_id' in r and r['project_id'] is not None for r in records)
                has_machine_id = all('machine_id' in r and r['machine_id'] is not None for r in records)

                # Show sample
                sample = records[0]
                print(f"  ✅ Found {count} records")
                print(f"     Sample ID: {sample.get('id', 'N/A')}")
                print(f"     project_id: {sample.get('project_id', 'MISSING')[:20]}..." if sample.get('project_id') else f"     project_id: MISSING ❌")
                print(f"     machine_id: {sample.get('machine_id', 'MISSING')}")

                results[table_name] = {
                    'status': 'ok',
                    'count': count,
                    'has_project_id': has_project_id,
                    'has_machine_id': has_machine_id,
                    'sample': {
                        'id': sample.get('id'),
                        'project_id': sample.get('project_id'),
                        'machine_id': sample.get('machine_id')
                    }
                }

        except Exception as e:
            print(f"  ❌ Error querying {table_name}: {e}")
            results[table_name] = {
                'status': 'error',
                'error': str(e)
            }

        print()

    # Step 4: Summary
    print("="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    print()

    total_tables = len(tables_to_check)
    tables_with_data = sum(1 for r in results.values() if r['status'] == 'ok')
    tables_with_project_id = sum(1 for r in results.values() if r.get('has_project_id') == True)
    tables_with_machine_id = sum(1 for r in results.values() if r.get('has_machine_id') == True)

    print(f"Tables checked: {total_tables}")
    print(f"Tables with data: {tables_with_data}")
    print(f"Tables with project_id: {tables_with_project_id}/{tables_with_data}")
    print(f"Tables with machine_id: {tables_with_machine_id}/{tables_with_data}")
    print()

    # Detailed results
    for (table_name, display_name), result in zip(tables_to_check, results.values()):
        status_icon = "✅" if result['status'] == 'ok' else "⚠️" if result['status'] == 'empty' else "❌"
        print(f"{status_icon} {display_name}:")

        if result['status'] == 'ok':
            project_check = "✅" if result['has_project_id'] else "❌"
            machine_check = "✅" if result['has_machine_id'] else "❌"
            print(f"   {project_check} project_id present")
            print(f"   {machine_check} machine_id present")
        elif result['status'] == 'empty':
            print(f"   No records to check")
        else:
            print(f"   Error: {result.get('error', 'Unknown')}")
        print()

    # Final verdict
    print("="*70)
    if tables_with_data > 0 and tables_with_project_id == tables_with_data and tables_with_machine_id == tables_with_data:
        print("✅ VERIFICATION PASSED")
        print("   All database records contain project_id and machine_id")
        return True
    elif tables_with_data == 0:
        print("⚠️  VERIFICATION INCONCLUSIVE")
        print("   No data in database tables to verify")
        print("   Sync may not have run yet, or tables are empty")
        return None
    else:
        print("❌ VERIFICATION FAILED")
        print("   Some records missing project_id or machine_id")
        return False


if __name__ == "__main__":
    try:
        result = verify_database_ids()
        if result is True:
            sys.exit(0)
        elif result is None:
            sys.exit(2)  # Inconclusive
        else:
            sys.exit(1)  # Failed
    except Exception as e:
        print(f"\n❌ Verification script error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
