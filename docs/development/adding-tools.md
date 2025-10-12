# How to Add New MCP Tools

*Step-by-step guide for adding new MCP tools to the simplified server*

## Overview

Adding a new MCP tool involves:
1. Choose the right tool module (or create new one)
2. Implement the tool function following standard patterns
3. Register the tool with FastMCP
4. Add comprehensive tests
5. Update documentation

**Time estimate**: 15-30 minutes for simple tool, 1-2 hours for complex tool

## Step 1: Choose Tool Module Location

Tools are organized by domain in the `tools/` directory:

- **`system_tools.py`** - System operations (health checks, project setup)
- **`task_tools.py`** - Task CRUD operations
- **`sprint_tools.py`** - Sprint management
- **`journal_tools.py`** - Session tracking, work history
- **`git_tools.py`** - Git session management
- **`specification_tools.py`** - Specification system
- **`template_tools.py`** - Template management
- **`document_tools.py`** - Document operations

**Decision guide**:
- Adding task-related feature? → `task_tools.py`
- Adding sprint feature? → `sprint_tools.py`
- New domain? → Create new module (see below)

## Step 2: Implement the Tool Function

### Basic Tool Template

```python
# In tools/your_module.py
from typing import Dict, Any
from core.project_manager import ProjectManager
from utils.helpers import (
    handle_error,
    check_project_initialized,
    load_json_data,
    save_json_data,
    get_timestamp
)

def register_your_tools(mcp, project_manager: ProjectManager):
    """Register your tools"""

    @mcp.tool()
    async def your_tool_name(
        required_param: str,
        optional_param: str = "default"
    ) -> Dict[str, Any]:
        """
        Clear description of what this tool does.

        Args:
            required_param: Description of required parameter
            optional_param: Description of optional parameter

        Returns:
            Success dict with status and result data
        """
        try:
            # Step 1: Validate project initialized
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error

            # Step 2: Validate input parameters (if needed)
            if not required_param:
                return {
                    "status": "error",
                    "error": "required_param cannot be empty"
                }

            # Step 3: Load data from file
            data_file = project_manager.get_data_file('data_type')
            data = load_json_data(data_file)

            # Step 4: Perform operation
            result = perform_operation(data, required_param, optional_param)

            # Step 5: Save changes (if modifying data)
            save_json_data(data_file, data)

            # Step 6: Return success response
            return {
                "status": "success",
                "result": result,
                "message": "Operation completed successfully"
            }

        except Exception as e:
            return handle_error(e, "your_tool_name")
```

### Read-Only Tool (No Data Modification)

```python
@mcp.tool()
async def your_query_tool(query: str) -> Dict[str, Any]:
    """Query data without modifications"""
    try:
        init_error = check_project_initialized(project_manager)
        if init_error:
            return init_error

        # Load data
        data_file = project_manager.get_data_file('tasks')
        data = load_json_data(data_file)

        # Query/filter data
        results = [item for item in data["tasks"] if query in item["title"]]

        # Return results (no save needed)
        return {
            "status": "success",
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return handle_error(e, "your_query_tool")
```

### Tool with Complex Validation

```python
@mcp.tool()
async def your_validated_tool(
    priority: str,
    status: str
) -> Dict[str, Any]:
    """Tool with input validation"""
    try:
        init_error = check_project_initialized(project_manager)
        if init_error:
            return init_error

        # Validate priority
        if not validate_priority(priority):
            return {
                "status": "error",
                "error": f"Invalid priority: {priority}",
                "valid_values": ["low", "medium", "high", "critical"]
            }

        # Validate status
        if not validate_status(status):
            return {
                "status": "error",
                "error": f"Invalid status: {status}",
                "valid_values": ["pending", "in_progress", "completed", "blocked"]
            }

        # Continue with validated inputs
        # ... tool logic ...

        return {"status": "success", "result": result}

    except Exception as e:
        return handle_error(e, "your_validated_tool")
```

## Step 3: Register in Server

### Option A: Add to Existing Module

Edit `server.py` - **no changes needed!** Your tool is automatically registered if you added it to an existing module.

### Option B: Create New Module

1. **Create new tool module**: `tools/your_module.py`

2. **Implement registration function**:
```python
def register_your_tools(mcp, project_manager: ProjectManager):
    """Register your category of tools"""

    @mcp.tool()
    async def tool_one(...):
        # Implementation
        pass

    @mcp.tool()
    async def tool_two(...):
        # Implementation
        pass
```

3. **Register in `server.py`**:
```python
# Add import
from tools.your_module import register_your_tools

# Add to _register_all_tools method
def _register_all_tools(self):
    tool_registrations = [
        # ... existing registrations ...
        ("YourTools", register_your_tools),  # Add this line
    ]
```

## Step 4: Add Tests

Add tests to `test_all_mcp_tools_direct.py`:

```python
async def test_your_tools(self) -> dict:
    """Test your new tools."""
    self.log("\n🔧 Testing Your Tools (2 tools)", "INFO")
    results = {"tested": 2, "passed": 0, "failed": 0, "errors": []}

    try:
        from utils.helpers import load_json_data, save_json_data

        # Test 1: your_tool_name
        try:
            data_file = self.project_manager.get_data_file('data_type')
            data = load_json_data(data_file)

            # Perform test operation
            test_data = {"id": "TEST-001", "title": "Test"}
            data["items"].append(test_data)
            save_json_data(data_file, data)

            # Verify
            verify_data = load_json_data(data_file)
            if len(verify_data["items"]) > 0:
                self.log("your_tool_name", "PASS")
                results["passed"] += 1
            else:
                self.log("your_tool_name: data not saved", "FAIL")
                results["failed"] += 1
        except Exception as e:
            self.log(f"your_tool_name: {e}", "FAIL")
            results["failed"] += 1
            results["errors"].append(f"your_tool_name: {e}")

        # Test 2: your_query_tool
        try:
            data_file = self.project_manager.get_data_file('data_type')
            data = load_json_data(data_file)

            # Query test
            results_found = [item for item in data["items"] if "Test" in item["title"]]

            if len(results_found) > 0:
                self.log("your_query_tool", "PASS")
                results["passed"] += 1
            else:
                self.log("your_query_tool: no results", "FAIL")
                results["failed"] += 1
        except Exception as e:
            self.log(f"your_query_tool: {e}", "FAIL")
            results["failed"] += 1
            results["errors"].append(f"your_query_tool: {e}")

    except Exception as e:
        self.log(f"Your tools test failed: {e}", "FAIL")
        results["failed"] = 2
        results["errors"].append(f"Test setup: {e}")

    return results
```

Add your test to the test runner:

```python
async def run_all_tests(self):
    categories = {
        # ... existing categories ...
        "Your Tools": self.test_your_tools,  # Add this line
    }
```

Update tool counts:

```python
def __init__(self):
    self.results = {
        "total_tools": 37,  # Update count
        # ...
    }
```

## Step 5: Test Your Implementation

```bash
# Run full test suite
python test_all_mcp_tools_direct.py

# Expected output should show your new tools passing
✅ your_tool_name
✅ your_query_tool

# Final summary should show updated counts
Total Tools: 37  # Updated
Tools Passed: 37/37  # All passing
```

## Real Example: Adding a Task Priority Update Tool

Let's walk through a real example.

### 1. Choose Module
Task-related → Add to `tools/task_tools.py`

### 2. Implement Tool
```python
# In tools/task_tools.py, inside register_task_tools()

@mcp.tool()
async def task_update_priority(
    task_id: str,
    priority: str
) -> Dict[str, Any]:
    """
    Update task priority.

    Args:
        task_id: Task ID (e.g., TASK-2025-001)
        priority: New priority (low/medium/high/critical)

    Returns:
        Success dict with updated task
    """
    try:
        init_error = check_project_initialized(project_manager)
        if init_error:
            return init_error

        # Validate priority
        if not validate_priority(priority):
            return {
                "status": "error",
                "error": f"Invalid priority: {priority}",
                "valid_values": ["low", "medium", "high", "critical"]
            }

        # Load tasks
        tasks_file = project_manager.get_data_file('tasks')
        data = load_json_data(tasks_file)

        # Find task
        task = None
        for t in data["tasks"]:
            if t.get("id") == task_id:
                task = t
                break

        if not task:
            return {
                "status": "error",
                "error": f"Task {task_id} not found"
            }

        # Update priority
        old_priority = task.get("priority", "unknown")
        task["priority"] = priority
        task["updated_at"] = get_timestamp()

        # Save
        save_json_data(tasks_file, data)

        return {
            "status": "success",
            "task": task,
            "message": f"Priority updated: {old_priority} → {priority}"
        }

    except Exception as e:
        return handle_error(e, "task_update_priority")
```

### 3. Register
Already registered! (existing module)

### 4. Add Test
```python
# In test_all_mcp_tools_direct.py, add to test_task_tools()

# Test: task_update_priority
try:
    tasks_file = self.project_manager.get_data_file('tasks')
    data = load_json_data(tasks_file)

    if data["tasks"]:
        task_id = data["tasks"][0]["id"]
        data["tasks"][0]["priority"] = "critical"
        data["tasks"][0]["updated_at"] = get_timestamp()
        save_json_data(tasks_file, data)

        verify_data = load_json_data(tasks_file)
        if verify_data["tasks"][0]["priority"] == "critical":
            self.log("task_update_priority", "PASS")
            results["passed"] += 1
        else:
            self.log("task_update_priority: update failed", "FAIL")
            results["failed"] += 1
    else:
        self.log("task_update_priority: no tasks to test", "PASS")
        results["passed"] += 1
except Exception as e:
    self.log(f"task_update_priority: {e}", "FAIL")
    results["failed"] += 1
    results["errors"].append(f"task_update_priority: {e}")

# Update test count
results = {"tested": 7, "passed": 0, "failed": 0, "errors": []}  # Was 6
```

### 5. Run Tests
```bash
python test_all_mcp_tools_direct.py

# Output:
📋 Testing Task Tools (7 tools)
✅ task_create
✅ task_search
✅ task_get
✅ task_update
✅ get_next_task_full
✅ task_delete
✅ task_update_priority  # New tool

Total Tools: 36
Tools Passed: 36/36
Pass Rate: 100.0%
```

## Common Patterns Reference

### Pattern: List/Query Operation
```python
@mcp.tool()
async def entity_list(filter: str = "") -> Dict[str, Any]:
    data = load_json_data(project_manager.get_data_file('entity'))
    items = data["entities"]

    if filter:
        items = [i for i in items if filter in i.get("title", "")]

    return {"status": "success", "items": items, "count": len(items)}
```

### Pattern: Create Operation
```python
@mcp.tool()
async def entity_create(title: str) -> Dict[str, Any]:
    data = load_json_data(project_manager.get_data_file('entity'))

    new_item = {
        "id": create_task_id(),  # Use appropriate ID generator
        "title": title,
        "created_at": get_timestamp(),
        "updated_at": get_timestamp()
    }

    data["entities"].append(new_item)
    save_json_data(project_manager.get_data_file('entity'), data)

    return {"status": "success", "entity": new_item}
```

### Pattern: Update Operation
```python
@mcp.tool()
async def entity_update(id: str, field: str) -> Dict[str, Any]:
    data = load_json_data(project_manager.get_data_file('entity'))

    entity = next((e for e in data["entities"] if e["id"] == id), None)
    if not entity:
        return {"status": "error", "error": f"Entity {id} not found"}

    entity["field"] = field
    entity["updated_at"] = get_timestamp()

    save_json_data(project_manager.get_data_file('entity'), data)

    return {"status": "success", "entity": entity}
```

### Pattern: Delete Operation
```python
@mcp.tool()
async def entity_delete(id: str) -> Dict[str, Any]:
    data = load_json_data(project_manager.get_data_file('entity'))

    original_count = len(data["entities"])
    data["entities"] = [e for e in data["entities"] if e["id"] != id]

    if len(data["entities"]) == original_count:
        return {"status": "error", "error": f"Entity {id} not found"}

    save_json_data(project_manager.get_data_file('entity'), data)

    return {"status": "success", "message": f"Deleted {id}"}
```

## Troubleshooting

**Tool not appearing in Claude Code**:
- Restart MCP server
- Check registration in `server.py`
- Verify import statement
- Check for syntax errors in tool function

**Tool fails with "No project directory set"**:
- Add `check_project_initialized` at start of tool
- Test with `system_set_project_directory` first

**Tests failing**:
- Check file paths match tool implementation
- Verify data structure matches expected format
- Add debug print statements
- Check for leftover test data

**Import errors**:
- Verify all imports at top of module
- Check helper function names
- Use absolute imports from project root

## Checklist

Before submitting your new tool:

- [ ] Tool follows function-based registration pattern
- [ ] Includes project initialization check
- [ ] Uses helpers for file operations
- [ ] Has comprehensive docstring
- [ ] Error handling with try/except
- [ ] Returns standard response format
- [ ] Added to appropriate tool module
- [ ] Registered in server (if new module)
- [ ] Tests added to test suite
- [ ] Tests pass (100%)
- [ ] Tool count updated in test file
- [ ] Tool works in Claude Code

## Next Steps

- Review the [Development Guide](./README.md)
- Check [Testing Guide](../testing/README.md)
- Look at existing tools for more examples
