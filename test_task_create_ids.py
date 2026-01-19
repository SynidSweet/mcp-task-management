#!/usr/bin/env python3
"""
TDD Test: task_create must store project_id and machine_id

Problem: Backend creates tasks without project_id and machine_id, but frontend
filters by these fields (tasks.http.api.ts line 181-183), causing created tasks
to disappear from the UI.

This test verifies that task_create properly populates both fields.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.project_manager import ProjectManager
from core.machine_id import get_machine_id
from utils.helpers import (
    load_json_data,
    save_json_data,
    get_timestamp,
    validate_priority
)


async def test_task_create_with_ids():
    """Test that task_create stores project_id and machine_id."""

    print("\n" + "="*70)
    print("TDD TEST: task_create must populate project_id and machine_id")
    print("="*70 + "\n")

    # Setup
    project_path = Path.cwd()
    project_manager = ProjectManager(project_path)

    # Get expected values
    expected_project_id = project_manager.get_or_generate_project_id()
    expected_machine_id = get_machine_id()

    print(f"Expected project_id: {expected_project_id}")
    print(f"Expected machine_id: {expected_machine_id}\n")

    # Test 1: Create a task using actual task_create implementation
    print("Test 1: Creating task via task_create...")

    # We need to test the actual implementation from task_tools.py
    # Import and call it directly
    from tools.task_tools import register_task_tools
    from unittest.mock import MagicMock

    # Create a mock MCP server that captures registered functions
    class MockMCP:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func
            return decorator

    # Mock the decorator
    mock_mcp = MockMCP()
    register_task_tools(mock_mcp, project_manager)

    # Get the task_create function
    task_create = mock_mcp.tools.get('task_create')
    if not task_create:
        print("❌ Failed to find task_create in registered tools")
        return False

    # Call it
    result = await task_create(
        title="Test Task - Frontend Visibility",
        description="This task should be visible in frontend after creation",
        priority="high"
    )

    if result["status"] != "success":
        print(f"❌ Task creation failed: {result}")
        return False

    created_task = result["task"]
    task_id = created_task["id"]
    print(f"✅ Task created: {task_id}\n")

    # Test 2: Verify project_id is stored
    print("Test 2: Verifying project_id...")
    if "project_id" not in created_task:
        print(f"❌ FAIL: project_id not found in task")
        print(f"   Task fields: {list(created_task.keys())}")
        return False

    if created_task["project_id"] != expected_project_id:
        print(f"❌ FAIL: project_id mismatch")
        print(f"   Expected: {expected_project_id}")
        print(f"   Got: {created_task['project_id']}")
        return False

    print(f"✅ project_id correctly stored: {created_task['project_id']}\n")

    # Test 3: Verify machine_id is stored
    print("Test 3: Verifying machine_id...")
    if "machine_id" not in created_task:
        print(f"❌ FAIL: machine_id not found in task")
        print(f"   Task fields: {list(created_task.keys())}")
        return False

    if created_task["machine_id"] != expected_machine_id:
        print(f"❌ FAIL: machine_id mismatch")
        print(f"   Expected: {expected_machine_id}")
        print(f"   Got: {created_task['machine_id']}")
        return False

    print(f"✅ machine_id correctly stored: {created_task['machine_id']}\n")

    # Test 4: Verify persistence (read from file)
    print("Test 4: Verifying persistence in tasks.json...")
    tasks_file = project_manager.get_data_file('tasks')

    with open(tasks_file, 'r') as f:
        data = json.load(f)

    # Find the created task in the file
    file_task = None
    for task in data.get('tasks', data.get('task', [])):
        if task.get('id') == task_id:
            file_task = task
            break

    if not file_task:
        print(f"❌ FAIL: Task {task_id} not found in tasks.json")
        return False

    if file_task.get("project_id") != expected_project_id:
        print(f"❌ FAIL: project_id not persisted correctly")
        print(f"   Expected: {expected_project_id}")
        print(f"   Got: {file_task.get('project_id')}")
        return False

    if file_task.get("machine_id") != expected_machine_id:
        print(f"❌ FAIL: machine_id not persisted correctly")
        print(f"   Expected: {expected_machine_id}")
        print(f"   Got: {file_task.get('machine_id')}")
        return False

    print(f"✅ Both IDs persisted correctly in tasks.json\n")

    # Test 5: Frontend filtering simulation
    print("Test 5: Simulating frontend filtering...")
    all_tasks = data.get('tasks', data.get('task', []))

    # This is what frontend does (tasks.http.api.ts line 181-183)
    filtered_tasks = [
        t for t in all_tasks
        if t.get('project_id') == expected_project_id
        and t.get('machine_id') == expected_machine_id
    ]

    if task_id not in [t['id'] for t in filtered_tasks]:
        print(f"❌ FAIL: Task would be filtered out by frontend!")
        print(f"   Frontend filters by project_id={expected_project_id} and machine_id={expected_machine_id}")
        print(f"   Task has project_id={file_task.get('project_id')} and machine_id={file_task.get('machine_id')}")
        return False

    print(f"✅ Task would pass frontend filtering and be visible to user\n")

    print("="*70)
    print("✅ ALL TESTS PASSED - task_create properly stores project_id and machine_id")
    print("="*70 + "\n")

    return True


if __name__ == '__main__':
    try:
        success = asyncio.run(test_task_create_with_ids())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
