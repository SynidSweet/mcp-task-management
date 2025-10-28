#!/usr/bin/env python3
"""
Clean up legacy database records missing project_id or machine_id.

This script:
1. Identifies records without required IDs
2. Shows what will be deleted
3. Asks for confirmation
4. Deletes the records
5. Verifies cleanup
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.document_tools import get_supabase_client


def find_orphaned_records(client, table_name):
    """Find records missing project_id or machine_id."""

    print(f"\n📋 Checking {table_name}...")

    try:
        # Get all records
        result = client.table(table_name).select('*').execute()

        if not result.data:
            print(f"  ✅ Table is empty")
            return []

        # Find problematic records
        orphaned = []
        for record in result.data:
            issues = []

            if record.get('project_id') is None:
                issues.append('missing project_id')

            if record.get('machine_id') is None:
                issues.append('missing machine_id')

            if issues:
                orphaned.append({
                    'id': record.get('id'),
                    'issues': issues,
                    'record': record
                })

        if orphaned:
            print(f"  ⚠️  Found {len(orphaned)} orphaned record(s)")
            for item in orphaned:
                print(f"     - ID: {item['id']}")
                print(f"       Issues: {', '.join(item['issues'])}")
        else:
            print(f"  ✅ No orphaned records")

        return orphaned

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


def delete_record(client, table_name, record_id):
    """Delete a single record by ID."""

    try:
        # Use the correct column name for the ID
        # Most tables use 'id', but we need to handle it properly
        result = client.table(table_name).delete().eq('id', record_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    """Run cleanup process."""

    print("="*70)
    print("LEGACY RECORD CLEANUP")
    print("="*70)
    print()
    print("This script will remove database records missing project_id or machine_id.")
    print()

    # Connect to database
    print("📋 Connecting to database...")
    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        return False

    print("✅ Connected")
    print()

    # Tables to check
    tables = [
        'tasks',
        'sprints',
        'journal_sessions',
        'specifications',
        'documents'
    ]

    # Step 1: Find all orphaned records
    print("="*70)
    print("STEP 1: SCANNING FOR ORPHANED RECORDS")
    print("="*70)

    all_orphaned = {}
    total_orphaned = 0

    for table_name in tables:
        orphaned = find_orphaned_records(client, table_name)
        if orphaned:
            all_orphaned[table_name] = orphaned
            total_orphaned += len(orphaned)

    # Step 2: Show summary
    print()
    print("="*70)
    print("STEP 2: SUMMARY")
    print("="*70)
    print()

    if total_orphaned == 0:
        print("✅ No orphaned records found! Database is clean.")
        return True

    print(f"⚠️  Found {total_orphaned} orphaned record(s) across {len(all_orphaned)} table(s)")
    print()

    for table_name, orphaned in all_orphaned.items():
        print(f"{table_name}: {len(orphaned)} record(s)")
        for item in orphaned:
            print(f"  - {item['id']}: {', '.join(item['issues'])}")

    print()

    # Step 3: Confirm deletion
    print("="*70)
    print("STEP 3: CONFIRMATION")
    print("="*70)
    print()
    print(f"⚠️  About to delete {total_orphaned} record(s)")
    print("   This action CANNOT be undone!")
    print()

    # Auto-confirm for script usage
    # In production, you might want to require input
    confirm = input("Type 'DELETE' to confirm deletion: ")

    if confirm != 'DELETE':
        print("❌ Deletion cancelled")
        return False

    # Step 4: Delete records
    print()
    print("="*70)
    print("STEP 4: DELETING RECORDS")
    print("="*70)
    print()

    deleted_count = 0
    failed_count = 0

    for table_name, orphaned in all_orphaned.items():
        print(f"\n📋 Cleaning {table_name}...")

        for item in orphaned:
            record_id = item['id']
            success, error = delete_record(client, table_name, record_id)

            if success:
                print(f"  ✅ Deleted: {record_id}")
                deleted_count += 1
            else:
                print(f"  ❌ Failed to delete {record_id}: {error}")
                failed_count += 1

    # Step 5: Verify cleanup
    print()
    print("="*70)
    print("STEP 5: VERIFICATION")
    print("="*70)
    print()

    print("📋 Rescanning database...")

    remaining_orphaned = 0
    for table_name in tables:
        orphaned = find_orphaned_records(client, table_name)
        remaining_orphaned += len(orphaned)

    # Final summary
    print()
    print("="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print()
    print(f"Records deleted: {deleted_count}")
    print(f"Deletion failures: {failed_count}")
    print(f"Remaining orphaned: {remaining_orphaned}")
    print()

    if remaining_orphaned == 0 and failed_count == 0:
        print("✅ CLEANUP SUCCESSFUL - Database is now clean!")
        return True
    elif remaining_orphaned == 0 and failed_count > 0:
        print("⚠️  CLEANUP PARTIAL - Some deletions failed but no orphans remain")
        return True
    else:
        print("❌ CLEANUP INCOMPLETE - Some orphaned records remain")
        return False


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Cleanup error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
