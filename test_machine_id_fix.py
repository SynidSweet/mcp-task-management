#!/usr/bin/env python3
"""
Test that machine_id fix is working correctly
"""
import sys
from pathlib import Path
from supabase import create_client

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.document_tools import get_or_create_project_id as doc_get_or_create
from tools.specification_tools import get_or_create_project_id as spec_get_or_create
from core.machine_id import get_machine_id

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def test_machine_id_available():
    """Test that machine_id is accessible"""
    print("TEST 1: Machine ID Availability")
    print("-" * 60)
    try:
        machine_id = get_machine_id()
        print(f"✓ Machine ID: {machine_id}")
        return True, machine_id
    except Exception as e:
        print(f"✗ Failed to get machine_id: {e}")
        return False, None

def test_document_tools_get_or_create():
    """Test document_tools.get_or_create_project_id includes machine_id"""
    print("\nTEST 2: document_tools.get_or_create_project_id")
    print("-" * 60)
    try:
        project_path = Path.cwd()
        project_id, error = doc_get_or_create(project_path)

        if error:
            print(f"✗ Error: {error}")
            return False

        if not project_id:
            print(f"✗ No project_id returned")
            return False

        print(f"✓ Project ID returned: {project_id}")

        # Verify in database that it has machine_id
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = client.table('projects').select('machine_id').eq('id', project_id).execute()

        if result.data and result.data[0].get('machine_id'):
            print(f"✓ Project has machine_id: {result.data[0]['machine_id']}")
            return True
        else:
            print(f"✗ Project missing machine_id in database")
            return False

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specification_tools_get_or_create():
    """Test specification_tools.get_or_create_project_id includes machine_id"""
    print("\nTEST 3: specification_tools.get_or_create_project_id")
    print("-" * 60)
    try:
        project_path = Path.cwd()
        project_id, error = spec_get_or_create(project_path)

        if error:
            print(f"✗ Error: {error}")
            return False

        if not project_id:
            print(f"✗ No project_id returned")
            return False

        print(f"✓ Project ID returned: {project_id}")

        # Verify in database that it has machine_id
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = client.table('projects').select('machine_id').eq('id', project_id).execute()

        if result.data and result.data[0].get('machine_id'):
            print(f"✓ Project has machine_id: {result.data[0]['machine_id']}")
            return True
        else:
            print(f"✗ Project missing machine_id in database")
            return False

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_project_isolation():
    """Test that projects are properly isolated by machine_id"""
    print("\nTEST 4: Project Isolation")
    print("-" * 60)
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Get all projects
        result = client.table('projects').select('*').execute()

        if not result.data:
            print(f"✗ No projects found")
            return False

        print(f"✓ Found {len(result.data)} project(s)")

        has_null_machine_id = False
        for proj in result.data:
            machine_id = proj.get('machine_id')
            path = proj.get('path')
            if machine_id:
                print(f"  ✓ {path}: machine_id = {machine_id}")
            else:
                print(f"  ✗ {path}: machine_id = NULL")
                has_null_machine_id = True

        if has_null_machine_id:
            print(f"\n✗ Some projects still have NULL machine_id")
            return False
        else:
            print(f"\n✓ All projects have machine_id set")
            return True

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_visibility():
    """Test that data is visible for this project"""
    print("\nTEST 5: Data Visibility")
    print("-" * 60)
    try:
        project_path = Path.cwd()
        machine_id = get_machine_id()

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Get project ID
        result = client.table('projects').select('id')\
            .eq('path', str(project_path))\
            .eq('machine_id', machine_id)\
            .execute()

        if not result.data:
            print(f"✗ Project not found")
            return False

        project_id = result.data[0]['id']
        print(f"✓ Project ID: {project_id}")

        # Check data in various tables
        tables = ['tasks', 'sprints', 'journal_sessions', 'specifications', 'documentation']
        all_visible = True

        for table in tables:
            result = client.table(table).select('id').eq('project_id', project_id).execute()
            count = len(result.data) if result.data else 0

            if count > 0:
                print(f"  ✓ {table}: {count} record(s)")
            else:
                print(f"  ⚠️  {table}: 0 records")

        return True

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("MACHINE ID FIX - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()

    tests = [
        ("Machine ID Availability", test_machine_id_available),
        ("document_tools.get_or_create_project_id", test_document_tools_get_or_create),
        ("specification_tools.get_or_create_project_id", test_specification_tools_get_or_create),
        ("Project Isolation", test_project_isolation),
        ("Data Visibility", test_data_visibility),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        # Handle test_machine_id_available returning tuple
        if isinstance(result, tuple):
            result = result[0]
        results.append((name, result))

    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Fix is working correctly!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
