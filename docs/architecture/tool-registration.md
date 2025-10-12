# Tool Registration System

*Deep dive into function-based tool registration with FastMCP*

## Overview

The MCP server uses a **modular, function-based registration** pattern that prioritizes simplicity and clear separation of concerns. Each tool module registers its tools with the FastMCP server using a standard registration function.

## Registration Pattern

### Standard Registration Function
```python
def register_*_tools(mcp, project_manager: ProjectManager):
    """Register [domain] tools with FastMCP server"""

    @mcp.tool()
    async def tool_name(param: str, optional: str = "default") -> Dict[str, Any]:
        """
        Tool description shown in Claude Code

        Args:
            param: Parameter description
            optional: Optional parameter description

        Returns:
            Dict with status and result
        """
        try:
            # Implementation
            return {"status": "success", "result": data}
        except Exception as e:
            return handle_error(e, "tool_name")
```

### Registration in server.py
```python
class MCPServer:
    def __init__(self, project_dir: Optional[Path] = None):
        self.mcp = FastMCP("claude-tasks")
        self.project_manager = ProjectManager(project_dir)
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all tools using simplified function-based architecture"""

        tool_registrations = [
            ("SystemTools", register_system_tools),
            ("TaskTools", register_task_tools),
            ("SprintTools", register_sprint_tools),
            ("JournalTools", register_journal_tools),
            ("GitTools", register_git_tools),
            ("SpecificationTools", register_specification_tools),
            ("TemplateTools", register_template_tools),
            ("DocumentTools", lambda mcp, pm: register_document_tools(mcp, pm, self))
        ]

        for module_name, register_func in tool_registrations:
            try:
                register_func(self.mcp, self.project_manager)
                print(f"✅ Registered {module_name}")
            except Exception as e:
                print(f"❌ Failed to register {module_name}: {str(e)}")
```

## Tool Modules

### 1. System Tools (`system_tools.py`)
**Purpose**: Project initialization and health checks
**Tools**: 3 tools

```python
def register_system_tools(mcp, project_manager: ProjectManager):
    @mcp.tool()
    async def system_set_project_directory(project_dir: str):
        """Set project directory"""
        return project_manager.set_project_directory(project_dir)

    @mcp.tool()
    async def system_health_check():
        """Check system health"""
        # Check files exist
        return {"status": "success", "health": data}

    @mcp.tool()
    async def workflow_load_context():
        """Load project context"""
        return {"status": "success", "context": data}
```

### 2. Task Tools (`task_tools.py`)
**Purpose**: Task CRUD operations
**Tools**: 8 tools

```python
def register_task_tools(mcp, project_manager: ProjectManager):
    @require_project_basics()
    @mcp.tool()
    async def task_create(title: str, description: str = "", priority: str = "medium"):
        """Create task"""
        tasks_file = project_manager.get_data_file('tasks')
        data = load_json_data(tasks_file)

        new_task = {
            "id": generate_task_id(),
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": get_timestamp()
        }

        data['tasks'].append(new_task)
        save_json_data(tasks_file, data)

        return {"status": "success", "task": new_task}

    @require_project_basics()
    @mcp.tool()
    async def task_update(task_id: str, status: str = "", priority: str = ""):
        """Update task"""
        # Find and update task
        return {"status": "success", "task": updated_task}

    @require_project_basics()
    @mcp.tool()
    async def task_list(status: str = "", limit: str = "10"):
        """List tasks"""
        # Filter and return tasks
        return {"status": "success", "tasks": filtered_tasks}

    # ... 5 more task tools
```

### 3. Sprint Tools (`sprint_tools.py`)
**Purpose**: Sprint management
**Tools**: 5 tools

```python
def register_sprint_tools(mcp, project_manager: ProjectManager):
    @require_project_basics()
    @mcp.tool()
    async def sprint_get_current():
        """Get current active sprint"""
        sprints_file = project_manager.get_data_file('sprints')
        data = load_json_data(sprints_file)

        # Find active sprint
        active = next((s for s in data['sprints'] if s['status'] == 'active'), None)

        return {"status": "success", "sprint": active}

    # ... 4 more sprint tools
```

### 4. Journal Tools (`journal_tools.py`)
**Purpose**: Session tracking and work history
**Tools**: 3 tools

```python
def register_journal_tools(mcp, project_manager: ProjectManager):
    @require_project_basics()
    @mcp.tool()
    async def journal_create_session(
        session_type: str,
        duration_minutes: float,
        tasks_worked: str
    ):
        """Create session entry"""
        journal_file = project_manager.get_data_file('journal')
        data = load_json_data(journal_file)

        session = {
            "id": f"SESSION-{get_timestamp()}",
            "session_type": session_type,
            "duration_minutes": duration_minutes,
            "tasks_worked": json.loads(tasks_worked),
            "created_at": get_timestamp()
        }

        data['sessions'].append(session)
        save_json_data(journal_file, data)

        return {"status": "success", "session": session}

    # ... 2 more journal tools
```

### 5. Git Tools (`git_tools.py`)
**Purpose**: Git repository validation
**Tools**: 4 tools

```python
def register_git_tools(mcp, project_manager: ProjectManager):
    @require_project_basics()
    @mcp.tool()
    async def git_validate_repository():
        """Validate Git setup"""
        # Check if Git repo
        # Check current branch
        # Check remote
        return {"status": "success", "validation": results}

    # ... 3 more git tools
```

### 6. Specification Tools (`specification_tools.py`)
**Purpose**: Requirements entity management
**Tools**: 10 tools

```python
def register_specification_tools(mcp, project_manager: ProjectManager):
    @require_project_basics()
    @mcp.tool()
    async def specification_create_entity(
        entity_name: str,
        entity_type: str,
        display_id: str
    ):
        """Create requirements entity"""
        requirements_file = project_manager.get_data_file('requirements')
        data = load_json_data(requirements_file)

        entity = {
            "id": str(uuid.uuid4()),
            "entity_name": entity_name,
            "entity_type": entity_type,
            "display_id": display_id,
            "created_at": get_timestamp()
        }

        data['requirements'].append(entity)
        save_json_data(requirements_file, data)

        return {"status": "success", "entity": entity}

    # ... 9 more specification tools
```

### 7. Template Tools (`template_tools.py`)
**Purpose**: Task and sprint template management
**Tools**: 2 tools

```python
def register_template_tools(mcp, project_manager: ProjectManager):
    @require_project_basics()
    @mcp.tool()
    async def template_list(scope: str = "all"):
        """List available templates"""
        # Load templates
        return {"status": "success", "templates": templates}

    @require_project_basics()
    @mcp.tool()
    async def template_get(template_name: str):
        """Get template definition"""
        # Load specific template
        return {"status": "success", "template": template}
```

### 8. Document Tools (`document_tools.py`)
**Purpose**: Document management with approval workflow
**Tools**: 6 tools

```python
def register_document_tools(mcp, project_manager: ProjectManager, server):
    @require_project_basics()
    @mcp.tool()
    async def document_create(
        document_title: str,
        document_type: str,
        description: str = ""
    ):
        """Create document"""
        documents_file = project_manager.get_data_file('documents')
        data = load_json_data(documents_file)

        document = {
            "id": str(uuid.uuid4()),
            "document_title": document_title,
            "document_type": document_type,
            "description": description,
            "status": "draft",
            "created_at": get_timestamp()
        }

        data['documents'].append(document)
        save_json_data(documents_file, data)

        return {"status": "success", "document": document}

    # ... 5 more document tools
```

## Decorator Patterns

### @mcp.tool()
**Purpose**: Register function as MCP tool
**Usage**: All tools must use this decorator

```python
@mcp.tool()
async def tool_name(param: str) -> Dict[str, Any]:
    """Tool description"""
    return {"status": "success"}
```

### @require_project_basics()
**Purpose**: Ensure project is initialized before tool execution
**Usage**: Most tools (except system_set_project_directory)

```python
@require_project_basics()
@mcp.tool()
async def tool_name(param: str) -> Dict[str, Any]:
    """Tool that requires project setup"""
    # Project guaranteed to be initialized here
    return {"status": "success"}
```

**Implementation**:
```python
def require_project_basics():
    """Decorator to check project initialization"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            project_manager = kwargs.get('project_manager') or args[0] if args else None

            if not project_manager or not project_manager.is_initialized():
                return {
                    "status": "error",
                    "error": "No project directory set",
                    "solution": "Use system_set_project_directory first"
                }

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

## Tool Implementation Patterns

### Pattern 1: Simple CRUD
```python
@require_project_basics()
@mcp.tool()
async def entity_create(name: str, type: str):
    """Create entity"""
    # 1. Validate inputs
    if not name:
        return {"status": "error", "error": "Name required"}

    # 2. Load data
    data_file = project_manager.get_data_file('entities')
    data = load_json_data(data_file)

    # 3. Create entity
    entity = {
        "id": generate_id(),
        "name": name,
        "type": type,
        "created_at": get_timestamp()
    }

    # 4. Save
    data['entities'].append(entity)
    save_json_data(data_file, data)

    # 5. Return
    return {"status": "success", "entity": entity}
```

### Pattern 2: Query/Search
```python
@require_project_basics()
@mcp.tool()
async def entity_search(query: str, type: str = ""):
    """Search entities"""
    # 1. Load data
    data_file = project_manager.get_data_file('entities')
    data = load_json_data(data_file)

    # 2. Filter
    entities = data['entities']
    if type:
        entities = [e for e in entities if e['type'] == type]
    if query:
        entities = [e for e in entities if query.lower() in e['name'].lower()]

    # 3. Return
    return {"status": "success", "entities": entities, "count": len(entities)}
```

### Pattern 3: Complex Operation
```python
@require_project_basics()
@mcp.tool()
async def entity_archive_old(days: int = 30):
    """Archive old entities"""
    try:
        # 1. Load data
        data_file = project_manager.get_data_file('entities')
        data = load_json_data(data_file)

        # 2. Find old entities
        cutoff = datetime.now() - timedelta(days=days)
        old_entities = [
            e for e in data['entities']
            if datetime.fromisoformat(e['created_at']) < cutoff
        ]

        # 3. Archive
        for entity in old_entities:
            entity['archived'] = True
            entity['archived_at'] = get_timestamp()

        # 4. Save
        save_json_data(data_file, data)

        # 5. Return summary
        return {
            "status": "success",
            "archived_count": len(old_entities),
            "archived_ids": [e['id'] for e in old_entities]
        }
    except Exception as e:
        return handle_error(e, "entity_archive_old")
```

## Adding a New Tool Category

### Step 1: Create Tool Module
Create `tools/new_category_tools.py`:

```python
"""New category operations - Simplified"""
from typing import Dict, Any
from core.project_manager import ProjectManager
from utils.helpers import (
    handle_error,
    check_project_initialized,
    load_json_data,
    save_json_data,
    get_timestamp
)
from utils.validation_wrapper import require_project_basics


def register_new_category_tools(mcp, project_manager: ProjectManager):
    """Register new category tools"""

    @require_project_basics()
    @mcp.tool()
    async def new_category_create(name: str) -> Dict[str, Any]:
        """Create new category item"""
        try:
            # Implementation
            return {"status": "success"}
        except Exception as e:
            return handle_error(e, "new_category_create")

    @require_project_basics()
    @mcp.tool()
    async def new_category_list() -> Dict[str, Any]:
        """List category items"""
        try:
            # Implementation
            return {"status": "success"}
        except Exception as e:
            return handle_error(e, "new_category_list")
```

### Step 2: Import in server.py
```python
from tools.new_category_tools import register_new_category_tools
```

### Step 3: Register in _register_all_tools()
```python
tool_registrations = [
    # ... existing registrations
    ("NewCategoryTools", register_new_category_tools),
]
```

### Step 4: Add Data File Support
Update `ProjectManager._ensure_project_structure()`:
```python
for filename in [
    "tasks.json",
    "sprints.json",
    # ... existing files
    "new_category.json"  # Add new file
]:
    # ... initialization code
```

### Step 5: Test
```python
# Test basic functionality
async def test_new_category():
    project_manager = ProjectManager(Path("test_project"))
    result = await new_category_create("Test Item")
    assert result['status'] == 'success'
```

## Tool Naming Conventions

### Convention
- **Module**: `{category}_tools.py`
- **Registration Function**: `register_{category}_tools()`
- **Tool Names**: `{category}_{action}()`

### Examples
- `task_tools.py` → `register_task_tools()` → `task_create()`, `task_list()`
- `sprint_tools.py` → `register_sprint_tools()` → `sprint_get_current()`
- `journal_tools.py` → `register_journal_tools()` → `journal_create_session()`

## Best Practices

### 1. Keep Tools Focused
Each tool should do one thing well:
```python
# Good: Clear single purpose
async def task_create(title: str):
    """Create task"""

# Bad: Multiple purposes
async def task_create_and_assign(title: str, sprint_id: str, user_id: str):
    """Create task, assign to sprint, and assign to user"""
```

### 2. Use Clear Parameter Names
```python
# Good: Clear what it does
async def task_list(status: str = "", limit: str = "10"):

# Bad: Unclear abbreviations
async def task_list(st: str = "", lim: str = "10"):
```

### 3. Return Consistent Format
```python
# Success
return {
    "status": "success",
    "result_key": result_data
}

# Error
return {
    "status": "error",
    "error": "Human-readable message",
    "solution": "How to fix"  # optional
}
```

### 4. Add Docstrings
```python
@mcp.tool()
async def tool_name(param: str) -> Dict[str, Any]:
    """
    One-line description shown in Claude Code.

    Args:
        param: Parameter description

    Returns:
        Dict with status and result
    """
```

### 5. Use Helper Functions
```python
# Reuse validation
if not validate_priority(priority):
    return {"status": "error", "error": "Invalid priority"}

# Reuse error handling
try:
    # operation
except Exception as e:
    return handle_error(e, "tool_name")
```

## Performance Considerations

### 1. Load Data Once
```python
# Good: Single load
data = load_json_data(file_path)
tasks = data['tasks']
# ... multiple operations on tasks

# Bad: Multiple loads
for task_id in task_ids:
    data = load_json_data(file_path)  # Slow!
```

### 2. Filter in Python
```python
# JSON files are small enough to filter in Python
data = load_json_data(file_path)
filtered = [t for t in data['tasks'] if t['status'] == status]
```

### 3. Atomic Saves
```python
# Helper handles atomic write with temp file
save_json_data(file_path, data)
```

## Testing Tools

### Unit Testing
```python
async def test_tool_name():
    # Setup
    project_manager = ProjectManager(temp_dir)

    # Execute
    result = await tool_name("test_param")

    # Assert
    assert result['status'] == 'success'
    assert 'result_key' in result
```

### Integration Testing
```python
async def test_tool_integration():
    # Create
    create_result = await entity_create("Test")
    entity_id = create_result['entity']['id']

    # Update
    update_result = await entity_update(entity_id, status="active")

    # Verify
    list_result = await entity_list()
    assert any(e['id'] == entity_id for e in list_result['entities'])
```

## Summary

The tool registration system provides:

1. **Modularity**: Each domain has its own module
2. **Simplicity**: Function-based, no complex classes
3. **Consistency**: Standard patterns across all tools
4. **Maintainability**: Easy to add, modify, or remove tools
5. **Testability**: Simple to test in isolation or integration

**Key Principle**: Keep tools simple, direct, and focused. Use the minimum code necessary to accomplish the task.
