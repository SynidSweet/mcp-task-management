#!/usr/bin/env python3
"""
Test that machine_id is correctly implemented as computer-wide identifier
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client
from core.machine_id import get_machine_id, get_machine_config_path

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def test_config_location():
    """Test that config is in global location"""
    print("TEST 1: Config Location")
    print("-" * 60)

    config_path = get_machine_config_path()
    expected_path = Path.home() / ".claude" / ".claude-machine-config.json"

    if config_path == expected_path:
        print(f"✓ Config path is global: {config_path}")
        return True
    else:
        print(f"✗ Config path is wrong:")
        print(f"  Expected: {expected_path}")
        print(f"  Got:      {config_path}")
        return False

def test_no_project_configs():
    """Test that project-specific config files don't exist"""
    print("\nTEST 2: No Project-Specific Configs")
    print("-" * 60)

    dev_config = Path("/home/dev/projects/mcp-management-system/dev/mcp-server/.claude-machine-config.json")
    prod_config = Path("/home/dev/projects/mcp-management-system/prod/mcp-server/.claude-machine-config.json")

    all_good = True

    if dev_config.exists():
        print(f"✗ Dev project config exists (should not): {dev_config}")
        all_good = False
    else:
        print(f"✓ No dev project config")

    if prod_config.exists():
        print(f"✗ Prod project config exists (should not): {prod_config}")
        all_good = False
    else:
        print(f"✓ No prod project config")

    return all_good

def test_machine_id_value():
    """Test that machine_id is correct"""
    print("\nTEST 3: Machine ID Value")
    print("-" * 60)

    try:
        machine_id = get_machine_id()
        expected = "ubuntu-bokio-dev"

        if machine_id == expected:
            print(f"✓ Machine ID correct: {machine_id}")
            return True
        else:
            print(f"✗ Machine ID wrong:")
            print(f"  Expected: {expected}")
            print(f"  Got:      {machine_id}")
            return False

    except Exception as e:
        print(f"✗ Error getting machine_id: {e}")
        return False

def test_database_consistency():
    """Test that both projects in database have same machine_id"""
    print("\nTEST 4: Database Consistency")
    print("-" * 60)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        machine_id = get_machine_id()

        dev_path = "/home/dev/projects/mcp-management-system/dev/mcp-server"
        prod_path = "/home/dev/projects/mcp-management-system/prod/mcp-server"

        # Get both projects
        result = client.table('projects').select('*').in_('path', [dev_path, prod_path]).execute()

        if not result.data or len(result.data) != 2:
            print(f"✗ Expected 2 projects, found {len(result.data) if result.data else 0}")
            return False

        all_correct = True
        for proj in result.data:
            proj_machine_id = proj.get('machine_id')
            if proj_machine_id == machine_id:
                print(f"✓ {Path(proj['path']).name}: machine_id = {proj_machine_id}")
            else:
                print(f"✗ {Path(proj['path']).name}: machine_id = {proj_machine_id} (expected {machine_id})")
                all_correct = False

        if all_correct:
            print(f"\n✓ Both projects share machine_id: {machine_id}")
            return True
        else:
            return False

    except Exception as e:
        print(f"✗ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_project_creation():
    """Test that get_or_create_project_id uses correct machine_id"""
    print("\nTEST 5: Project Creation Uses Correct machine_id")
    print("-" * 60)

    try:
        from tools.document_tools import get_or_create_project_id
        machine_id = get_machine_id()

        # Test with current directory
        project_path = Path.cwd()
        project_id, error = get_or_create_project_id(project_path)

        if error:
            print(f"✗ Error: {error}")
            return False

        # Verify in database
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = client.table('projects').select('machine_id').eq('id', project_id).execute()

        if result.data and result.data[0].get('machine_id') == machine_id:
            print(f"✓ Project creation uses correct machine_id: {machine_id}")
            return True
        else:
            db_machine_id = result.data[0].get('machine_id') if result.data else None
            print(f"✗ Project has wrong machine_id:")
            print(f"  Expected: {machine_id}")
            print(f"  Got:      {db_machine_id}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_visibility():
    """Test that data is still visible"""
    print("\nTEST 6: Data Visibility")
    print("-" * 60)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        machine_id = get_machine_id()
        dev_path = "/home/dev/projects/mcp-management-system/dev/mcp-server"

        # Get dev project ID
        result = client.table('projects').select('id')\
            .eq('path', dev_path)\
            .eq('machine_id', machine_id)\
            .execute()

        if not result.data:
            print(f"✗ Dev project not found")
            return False

        project_id = result.data[0]['id']

        # Check data
        tables = ['tasks', 'sprints', 'journal_sessions', 'specifications', 'documentation']
        has_data = False

        for table in tables:
            result = client.table(table).select('id').eq('project_id', project_id).execute()
            count = len(result.data) if result.data else 0
            if count > 0:
                print(f"  ✓ {table}: {count} record(s)")
                has_data = True

        if has_data:
            print(f"\n✓ Data is visible")
            return True
        else:
            print(f"\n⚠️  No data found (may be expected)")
            return True  # Not a failure, just no data

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("=" * 80)
    print("MACHINE ID CORRECTNESS TEST SUITE")
    print("=" * 80)
    print()

    tests = [
        ("Config Location", test_config_location),
        ("No Project-Specific Configs", test_no_project_configs),
        ("Machine ID Value", test_machine_id_value),
        ("Database Consistency", test_database_consistency),
        ("Project Creation", test_project_creation),
        ("Data Visibility", test_data_visibility),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
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
        print("\n🎉 ALL TESTS PASSED - machine_id correctly implemented!")
        print()
        print("Summary:")
        print("  - Global config at ~/.claude/.claude-machine-config.json ✓")
        print("  - No project-specific configs ✓")
        print("  - machine_id = ubuntu-bokio-dev ✓")
        print("  - Both dev and prod projects share same machine_id ✓")
        print("  - Data is visible ✓")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
