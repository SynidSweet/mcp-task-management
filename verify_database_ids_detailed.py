#!/usr/bin/env python3
"""
Detailed verification of project_id and machine_id in database records.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.document_tools import get_supabase_client
from core.machine_id import get_machine_id


def verify_table_detailed(client, table_name, display_name):
    """Verify a single table with detailed output."""

    print(f"\n{'='*70}")
    print(f"{display_name.upper()} ({table_name})")
    print('='*70)

    try:
        # Query first 5 records
        result = client.table(table_name).select('*').limit(5).execute()

        if not result.data or len(result.data) == 0:
            print("⚠️  No records found")
            return {'status': 'empty', 'records': []}

        records = result.data
        print(f"✅ Found {len(records)} record(s)")
        print()

        # Analyze each record
        issues = []
        for i, record in enumerate(records, 1):
            print(f"Record {i}:")
            print(f"  ID: {record.get('id', 'N/A')}")

            # Check project_id
            project_id = record.get('project_id')
            if project_id is None:
                print(f"  ❌ project_id: MISSING (None)")
                issues.append(f"Record {i}: missing project_id")
            elif project_id == '':
                print(f"  ❌ project_id: EMPTY STRING")
                issues.append(f"Record {i}: empty project_id")
            else:
                print(f"  ✅ project_id: {str(project_id)[:40]}...")

            # Check machine_id
            machine_id = record.get('machine_id')
            if machine_id is None:
                print(f"  ❌ machine_id: MISSING (None)")
                issues.append(f"Record {i}: missing machine_id")
            elif machine_id == '':
                print(f"  ❌ machine_id: EMPTY STRING")
                issues.append(f"Record {i}: empty machine_id")
            else:
                print(f"  ✅ machine_id: {machine_id}")

            print()

        # Summary for this table
        if issues:
            print(f"❌ Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            return {'status': 'issues', 'records': records, 'issues': issues}
        else:
            print(f"✅ All records have both project_id and machine_id")
            return {'status': 'ok', 'records': records}

    except Exception as e:
        print(f"❌ Error querying table: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}


def main():
    """Run detailed verification."""

    print("="*70)
    print("DETAILED DATABASE ID VERIFICATION")
    print("="*70)
    print()

    # Check machine_id
    try:
        machine_id = get_machine_id()
        print(f"✅ Machine ID configured: {machine_id}")
    except Exception as e:
        print(f"❌ Machine ID error: {e}")
        return False

    # Connect to database
    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        return False

    print(f"✅ Database connected")

    # Check each table
    tables = [
        ('tasks', 'Tasks'),
        ('sprints', 'Sprints'),
        ('journal_sessions', 'Journal Sessions'),
        ('specifications', 'Specifications'),
        ('documents', 'Documents')
    ]

    results = {}
    for table_name, display_name in tables:
        results[table_name] = verify_table_detailed(client, table_name, display_name)

    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print()

    tables_ok = sum(1 for r in results.values() if r['status'] == 'ok')
    tables_issues = sum(1 for r in results.values() if r['status'] == 'issues')
    tables_empty = sum(1 for r in results.values() if r['status'] == 'empty')
    tables_error = sum(1 for r in results.values() if r['status'] == 'error')

    print(f"Tables checked: {len(tables)}")
    print(f"  ✅ OK: {tables_ok}")
    print(f"  ⚠️  Issues: {tables_issues}")
    print(f"  ⚠️  Empty: {tables_empty}")
    print(f"  ❌ Errors: {tables_error}")
    print()

    if tables_ok == len(tables):
        print("✅ VERIFICATION PASSED - All records have both IDs")
        return True
    elif tables_ok + tables_empty == len(tables):
        print("⚠️  VERIFICATION INCONCLUSIVE - Some tables empty")
        return None
    else:
        print("❌ VERIFICATION FAILED - Some records missing IDs")

        # Show specific issues
        print("\nIssues by table:")
        for table_name, result in results.items():
            if result['status'] == 'issues':
                print(f"\n{table_name}:")
                for issue in result.get('issues', []):
                    print(f"  - {issue}")

        return False


if __name__ == "__main__":
    try:
        result = main()
        if result is True:
            sys.exit(0)
        elif result is None:
            sys.exit(2)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
