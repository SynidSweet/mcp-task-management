#!/usr/bin/env python3
"""Test task hierarchy functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.project_manager import ProjectManager
from tools.task_tools import register_task_tools
from mcp.server import Server


async def test_task_hierarchy():
    """Test task hierarchy creation and queries."""

    print("\n" + "="*60)
    print("TASK HIERARCHY FUNCTIONALITY TEST")
    print("="*60 + "\n")

    # Setup
    project_manager = ProjectManager(Path.cwd())
    project_manager.set_project_directory(Path.cwd())

    mcp = Server("test")
    register_task_tools(mcp, project_manager)

    # Get the tool functions
    task_create = None
    task_get_children = None
    task_get_subtree = None

    for tool in mcp.list_tools():
        if tool.name == "task_create":
            task_create = tool.fn
        elif tool.name == "task_get_children":
            task_get_children = tool.fn
        elif tool.name == "task_get_subtree":
            task_get_subtree = tool.fn

    if not all([task_create, task_get_children, task_get_subtree]):
        print("❌ Failed to find required tools")
        return False

    print("✅ Tools loaded\n")

    # Test 1: Create parent task
    print("1. Creating parent task...")
    result = await task_create(
        title="Parent Task - Auth System",
        description="Top-level authentication system task",
        priority="high"
    )

    if result["status"] != "success":
        print(f"❌ Failed to create parent: {result}")
        return False

    parent_id = result["task"]["id"]
    print(f"   ✅ Created parent: {parent_id}")
    print(f"   parent_task_id: {result['task'].get('parent_task_id')}")
    print(f"   child_task_ids: {result['task'].get('child_task_ids')}\n")

    # Test 2: Create child task
    print("2. Creating child task...")
    result = await task_create(
        title="Child Task - Login Feature",
        description="Login functionality",
        priority="medium",
        parent_task_id=parent_id
    )

    if result["status"] != "success":
        print(f"❌ Failed to create child: {result}")
        return False

    child_id = result["task"]["id"]
    print(f"   ✅ Created child: {child_id}")
    print(f"   parent_task_id: {result['task'].get('parent_task_id')}")
    print(f"   child_task_ids: {result['task'].get('child_task_ids')}\n")

    # Test 3: Create grandchild task
    print("3. Creating grandchild task...")
    result = await task_create(
        title="Grandchild Task - OAuth Integration",
        description="OAuth 2.0 integration",
        priority="medium",
        parent_task_id=child_id
    )

    if result["status"] != "success":
        print(f"❌ Failed to create grandchild: {result}")
        return False

    grandchild_id = result["task"]["id"]
    print(f"   ✅ Created grandchild: {grandchild_id}")
    print(f"   parent_task_id: {result['task'].get('parent_task_id')}\n")

    # Test 4: Get children
    print("4. Getting children of parent task...")
    result = await task_get_children(task_id=parent_id)

    if result["status"] != "success":
        print(f"❌ Failed to get children: {result}")
        return False

    print(f"   ✅ Found {result['children_count']} children")
    for child in result['children']:
        print(f"      - {child['id']}: {child['title']}\n")

    # Test 5: Get subtree
    print("5. Getting full subtree from parent...")
    result = await task_get_subtree(task_id=parent_id, depth=-1)

    if result["status"] != "success":
        print(f"❌ Failed to get subtree: {result}")
        return False

    print(f"   ✅ Subtree has {result['total_tasks']} total tasks")
    for idx, task in enumerate(result['subtree']):
        indent = "   " * (0 if task['id'] == parent_id else 1 if task.get('parent_task_id') == parent_id else 2)
        print(f"   {indent}{task['id']}: {task['title']}")

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - Task hierarchy working correctly!")
    print("="*60 + "\n")

    return True


if __name__ == '__main__':
    success = asyncio.run(test_task_hierarchy())
    sys.exit(0 if success else 1)
