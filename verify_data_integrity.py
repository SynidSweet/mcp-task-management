#!/usr/bin/env python3
"""
Comprehensive data integrity verification for MCP database.

Checks:
1. All records have required project_id and machine_id
2. No orphaned records
3. Foreign key relationships are valid
4. Data consistency across tables
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.document_tools import get_supabase_client
from core.machine_id import get_machine_id


def check_required_ids(client, table_name, display_name):
    """Check that all records have required project_id and machine_id."""

    try:
        # Query all records
        result = client.table(table_name).select('id, project_id, machine_id').execute()

        if not result.data or len(result.data) == 0:
            return {
                'status': 'empty',
                'table': table_name,
                'total': 0,
                'missing_project_id': 0,
                'missing_machine_id': 0,
                'missing_both': 0
            }

        records = result.data
        total = len(records)

        # Count issues
        missing_project_id = sum(1 for r in records if r.get('project_id') is None)
        missing_machine_id = sum(1 for r in records if r.get('machine_id') is None)
        missing_both = sum(1 for r in records if r.get('project_id') is None and r.get('machine_id') is None)

        status = 'ok' if missing_project_id == 0 and missing_machine_id == 0 else 'issues'

        return {
            'status': status,
            'table': table_name,
            'total': total,
            'missing_project_id': missing_project_id,
            'missing_machine_id': missing_machine_id,
            'missing_both': missing_both
        }

    except Exception as e:
        return {
            'status': 'error',
            'table': table_name,
            'error': str(e)
        }


def check_foreign_keys(client):
    """Check foreign key relationships are valid."""

    print("\n📋 Checking foreign key relationships...")
    print("-"*70)

    issues = []

    try:
        # Check tasks.project_id references projects.id
        result = client.table('tasks').select('id, project_id').execute()
        if result.data:
            task_project_ids = set(r['project_id'] for r in result.data if r.get('project_id'))

            if task_project_ids:
                projects_result = client.table('projects').select('id').execute()
                valid_project_ids = set(r['id'] for r in projects_result.data)

                orphaned_tasks = task_project_ids - valid_project_ids
                if orphaned_tasks:
                    issues.append(f"  ❌ {len(orphaned_tasks)} task(s) reference non-existent projects")
                else:
                    print(f"  ✅ Tasks: All project_id references are valid")
            else:
                print(f"  ⚠️  Tasks: No project_id values to check")
        else:
            print(f"  ⚠️  Tasks: Table is empty")

        # Check sprints.project_id references projects.id
        result = client.table('sprints').select('id, project_id').execute()
        if result.data:
            sprint_project_ids = set(r['project_id'] for r in result.data if r.get('project_id'))

            if sprint_project_ids:
                projects_result = client.table('projects').select('id').execute()
                valid_project_ids = set(r['id'] for r in projects_result.data)

                orphaned_sprints = sprint_project_ids - valid_project_ids
                if orphaned_sprints:
                    issues.append(f"  ❌ {len(orphaned_sprints)} sprint(s) reference non-existent projects")
                else:
                    print(f"  ✅ Sprints: All project_id references are valid")
            else:
                print(f"  ⚠️  Sprints: No project_id values to check")
        else:
            print(f"  ⚠️  Sprints: Table is empty")

        # Check tasks.sprint_id references sprints.id
        result = client.table('tasks').select('id, sprint_id').execute()
        if result.data:
            task_sprint_ids = set(r['sprint_id'] for r in result.data if r.get('sprint_id'))

            if task_sprint_ids:
                sprints_result = client.table('sprints').select('id').execute()
                valid_sprint_ids = set(r['id'] for r in sprints_result.data)

                orphaned_task_sprints = task_sprint_ids - valid_sprint_ids
                if orphaned_task_sprints:
                    issues.append(f"  ❌ {len(orphaned_task_sprints)} task(s) reference non-existent sprints")
                else:
                    print(f"  ✅ Tasks: All sprint_id references are valid")
            else:
                print(f"  ⚠️  Tasks: No sprint_id values to check")

        return issues

    except Exception as e:
        print(f"  ❌ Error checking foreign keys: {e}")
        return [f"  ❌ Foreign key check failed: {e}"]


def check_data_consistency(client):
    """Check data consistency across tables."""

    print("\n📋 Checking data consistency...")
    print("-"*70)

    issues = []

    try:
        # Check task dependencies
        result = client.table('tasks').select('id, dependencies').execute()
        if result.data:
            all_task_ids = set(r['id'] for r in result.data)

            for task in result.data:
                deps = task.get('dependencies', {})
                if not deps:
                    continue

                # Check blocked_by references
                for blocked_by_id in deps.get('blocked_by', []):
                    if blocked_by_id not in all_task_ids:
                        issues.append(f"  ❌ Task {task['id']} blocked_by non-existent task {blocked_by_id}")

                # Check blocks references
                for blocks_id in deps.get('blocks', []):
                    if blocks_id not in all_task_ids:
                        issues.append(f"  ❌ Task {task['id']} blocks non-existent task {blocks_id}")

            if not issues:
                print(f"  ✅ Task dependencies: All references are valid")
        else:
            print(f"  ⚠️  Tasks: Table is empty")

        # Check sprint task_ids
        result = client.table('sprints').select('id, task_ids').execute()
        if result.data:
            tasks_result = client.table('tasks').select('id').execute()
            all_task_ids = set(r['id'] for r in tasks_result.data)

            for sprint in result.data:
                task_ids = sprint.get('task_ids', [])
                if not task_ids:
                    continue

                for task_id in task_ids:
                    if task_id not in all_task_ids:
                        issues.append(f"  ❌ Sprint {sprint['id']} references non-existent task {task_id}")

            if not [i for i in issues if 'Sprint' in i]:
                print(f"  ✅ Sprint task_ids: All references are valid")
        else:
            print(f"  ⚠️  Sprints: Table is empty")

        return issues

    except Exception as e:
        print(f"  ❌ Error checking data consistency: {e}")
        return [f"  ❌ Consistency check failed: {e}"]


def main():
    """Run comprehensive data integrity verification."""

    print("="*70)
    print("DATA INTEGRITY VERIFICATION")
    print("="*70)
    print()

    # Step 1: Connect to database
    print("📋 Step 1: Connecting to database...")
    print("-"*70)

    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        return False

    print("✅ Connected to Supabase")

    # Step 2: Check machine_id configuration
    print("\n📋 Step 2: Checking machine_id configuration...")
    print("-"*70)

    try:
        machine_id = get_machine_id()
        print(f"✅ Machine ID: {machine_id}")
    except Exception as e:
        print(f"❌ Machine ID error: {e}")

    # Step 3: Check required IDs
    print("\n📋 Step 3: Checking required IDs (project_id, machine_id)...")
    print("-"*70)

    tables = [
        ('tasks', 'Tasks'),
        ('sprints', 'Sprints'),
        ('journal_sessions', 'Journal Sessions'),
        ('specifications', 'Specifications'),
        ('documents', 'Documents')
    ]

    results = {}
    total_issues = 0

    for table_name, display_name in tables:
        result = check_required_ids(client, table_name, display_name)
        results[table_name] = result

        if result['status'] == 'ok':
            print(f"  ✅ {display_name}: {result['total']} record(s), all have required IDs")
        elif result['status'] == 'empty':
            print(f"  ⚠️  {display_name}: Table is empty")
        elif result['status'] == 'issues':
            print(f"  ❌ {display_name}: {result['total']} record(s)")
            if result['missing_project_id'] > 0:
                print(f"     Missing project_id: {result['missing_project_id']}")
                total_issues += result['missing_project_id']
            if result['missing_machine_id'] > 0:
                print(f"     Missing machine_id: {result['missing_machine_id']}")
                total_issues += result['missing_machine_id']
        else:
            print(f"  ❌ {display_name}: Error - {result.get('error', 'Unknown')}")

    # Step 4: Check foreign keys
    fk_issues = check_foreign_keys(client)

    # Step 5: Check data consistency
    consistency_issues = check_data_consistency(client)

    # Final summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print()

    tables_with_data = sum(1 for r in results.values() if r['status'] in ['ok', 'issues'])
    tables_clean = sum(1 for r in results.values() if r['status'] == 'ok')

    print(f"Tables checked: {len(tables)}")
    print(f"Tables with data: {tables_with_data}")
    print(f"Tables clean (all IDs present): {tables_clean}/{tables_with_data}")
    print()

    # ID Issues
    if total_issues == 0:
        print("✅ Required IDs: All records have project_id and machine_id")
    else:
        print(f"❌ Required IDs: {total_issues} issue(s) found")

    # Foreign Key Issues
    if not fk_issues:
        print("✅ Foreign Keys: All references are valid")
    else:
        print(f"❌ Foreign Keys: {len(fk_issues)} issue(s) found")
        for issue in fk_issues:
            print(issue)

    # Consistency Issues
    if not consistency_issues:
        print("✅ Data Consistency: All cross-references are valid")
    else:
        print(f"❌ Data Consistency: {len(consistency_issues)} issue(s) found")
        for issue in consistency_issues:
            print(issue)

    print()

    # Final verdict
    all_clean = (
        total_issues == 0 and
        not fk_issues and
        not consistency_issues
    )

    if all_clean:
        print("="*70)
        print("✅ VERIFICATION PASSED")
        print("   Database integrity is intact")
        print("="*70)
        return True
    else:
        print("="*70)
        print("❌ VERIFICATION FAILED")
        print("   Database has integrity issues")
        print("="*70)
        return False


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
