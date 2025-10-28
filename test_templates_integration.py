#!/usr/bin/env python3
"""
Template System Integration Test

Tests the normalized template system (template_tasks, template_sprints) via
direct database queries. This verifies the data migration and structure.

Run: python3 test_templates_integration.py
"""

import sys
from tools.document_tools import get_supabase_client

def test_template_tasks_exist():
    """Test that template_tasks table exists and has data"""
    print("\n1️⃣  Testing template_tasks table...")
    client, _ = get_supabase_client()

    try:
        result = client.table('template_tasks').select('*').execute()
        count = len(result.data)
        print(f"   ✅ Found {count} template tasks")

        # Check for entry tasks
        entry_tasks = [t for t in result.data if t.get('is_entry_task')]
        print(f"   ✅ Entry tasks: {len(entry_tasks)}")

        # Check for nested tasks
        nested_tasks = [t for t in result.data if not t.get('is_entry_task')]
        print(f"   ✅ Nested tasks: {len(nested_tasks)}")

        return count > 0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_template_sprints_exist():
    """Test that template_sprints table exists and has data"""
    print("\n2️⃣  Testing template_sprints table...")
    client, _ = get_supabase_client()

    try:
        result = client.table('template_sprints').select('*').execute()
        count = len(result.data)
        print(f"   ✅ Found {count} sprint templates")
        return count > 0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_template_composition():
    """Test that template composition (references) works"""
    print("\n3️⃣  Testing template composition...")
    client, _ = get_supabase_client()

    try:
        # Find a template with references
        result = client.table('template_tasks').select('*').not_.is_('references_template_id', 'null').execute()

        if result.data:
            ref_task = result.data[0]
            print(f"   ✅ Found reference: {ref_task['template_id']} → {ref_task['references_template_id']}")

            # Verify the referenced template exists
            ref_result = client.table('template_tasks').select('*').eq('template_id', ref_task['references_template_id']).execute()

            if ref_result.data:
                print(f"   ✅ Referenced template exists: {ref_result.data[0]['template_name']}")
                return True
            else:
                print(f"   ❌ Referenced template not found: {ref_task['references_template_id']}")
                return False
        else:
            print(f"   ⚠️  No template references found (this is okay if no composite templates exist)")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_template_hierarchy():
    """Test that template hierarchy (parent-child) works"""
    print("\n4️⃣  Testing template hierarchy...")
    client, _ = get_supabase_client()

    try:
        # Find templates with children
        result = client.table('template_tasks').select('*').execute()

        templates_with_children = [
            t for t in result.data
            if t.get('child_template_ids') and len(t.get('child_template_ids', [])) > 0
        ]

        if templates_with_children:
            parent = templates_with_children[0]
            print(f"   ✅ Found parent template: {parent['template_id']}")
            print(f"   ✅ Children: {parent['child_template_ids']}")

            # Verify children exist
            child_id = parent['child_template_ids'][0]
            child_result = client.table('template_tasks').select('*').eq('template_id', child_id).execute()

            if child_result.data:
                child = child_result.data[0]
                print(f"   ✅ Child template exists: {child['template_id']}")
                print(f"   ✅ Child's parent: {child.get('parent_template_id')}")
                return True
            else:
                print(f"   ❌ Child template not found: {child_id}")
                return False
        else:
            print(f"   ⚠️  No template hierarchies found (this is okay if no nested templates exist)")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_template_variables():
    """Test that template variables are stored correctly"""
    print("\n5️⃣  Testing template variables...")
    client, _ = get_supabase_client()

    try:
        # Find templates with variables
        result = client.table('template_tasks').select('*').execute()

        templates_with_vars = [
            t for t in result.data
            if t.get('variables') and len(t.get('variables', [])) > 0
        ]

        if templates_with_vars:
            template = templates_with_vars[0]
            variables = template['variables']
            print(f"   ✅ Template: {template['template_id']}")
            print(f"   ✅ Variables: {len(variables)}")

            # Check variable structure
            if variables:
                var = variables[0]
                if 'name' in var:
                    print(f"   ✅ Variable structure valid: {var}")
                    return True
                else:
                    print(f"   ❌ Variable missing 'name' field: {var}")
                    return False
        else:
            print(f"   ⚠️  No templates with variables found")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_sprint_task_references():
    """Test that sprint templates reference task templates"""
    print("\n6️⃣  Testing sprint task references...")
    client, _ = get_supabase_client()

    try:
        result = client.table('template_sprints').select('*').execute()

        if result.data:
            sprint = result.data[0]
            task_ids = sprint.get('task_ids', [])

            print(f"   ✅ Sprint: {sprint['template_id']}")
            print(f"   ✅ Task IDs (mirrors sprints.task_ids): {len(task_ids)}")

            # Verify at least one task reference exists
            if task_ids:
                task_id = task_ids[0]
                task_result = client.table('template_tasks').select('*').eq('template_id', task_id).execute()

                if task_result.data:
                    print(f"   ✅ Referenced task exists: {task_id}")
                    return True
                else:
                    print(f"   ❌ Referenced task not found: {task_id}")
                    return False
            else:
                print(f"   ⚠️  Sprint has no task assignments")
                return True
        else:
            print(f"   ⚠️  No sprint templates found")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all integration tests"""
    print("=" * 60)
    print("TEMPLATE SYSTEM INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        ("Template Tasks Table", test_template_tasks_exist),
        ("Template Sprints Table", test_template_sprints_exist),
        ("Template Composition", test_template_composition),
        ("Template Hierarchy", test_template_hierarchy),
        ("Template Variables", test_template_variables),
        ("Sprint Task References", test_sprint_task_references),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
