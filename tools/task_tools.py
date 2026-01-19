"""Task management operations - Simplified"""
import json
from datetime import datetime
from typing import Dict, Any, List
from core.project_manager import ProjectManager
from core.machine_id import get_machine_id
from utils.helpers import (
    handle_error,
    check_project_initialized,
    load_json_data,
    save_json_data,
    create_task_id,
    get_timestamp,
    validate_priority,
    validate_status
)
from utils.validation_wrapper import require_project_basics


def register_task_tools(mcp, project_manager: ProjectManager, tool_filter=None):
    """Register task tools with simple pattern"""

    if not tool_filter or tool_filter.should_register_tool("task_create"):
        @require_project_basics()
        @mcp.tool()
        async def task_create(
            title: str,
            description: str = "",
            priority: str = "medium",
            parent_task_id: str = ""
        ) -> Dict[str, Any]:
            """Create task with optional parent for hierarchy support"""
            try:
                if not validate_priority(priority):
                    return {
                        "status": "error",
                        "error": f"Invalid priority: {priority}. Must be one of: low, medium, high, critical"
                    }

                tasks_file = project_manager.get_data_file('tasks')
                data = load_json_data(tasks_file)

                # Validate parent exists if provided
                parent_task = None
                if parent_task_id:
                    tasks_list = data.get('tasks', data.get('task', []))
                    for t in tasks_list:
                        if t.get("id") == parent_task_id:
                            parent_task = t
                            break

                    if not parent_task:
                        return {
                            "status": "error",
                            "error": f"Parent task {parent_task_id} not found"
                        }

                # Create task with simple ID generation (handle both 'tasks' and 'task' keys)
                tasks_list = data.get('tasks', data.get('task', []))
                task_id = f"TASK-{datetime.now().strftime('%Y')}-{len(tasks_list) + 1:03d}"
                new_task = {
                    "id": task_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": "pending",
                    "parent_task_id": parent_task_id if parent_task_id else None,
                    "child_task_ids": [],
                    "project_id": project_manager.get_or_generate_project_id(),
                    "machine_id": get_machine_id(),
                    "created_at": get_timestamp(),
                    "updated_at": get_timestamp()
                }

                # Update parent's child_task_ids if this is a subtask
                if parent_task and parent_task_id:
                    if "child_task_ids" not in parent_task:
                        parent_task["child_task_ids"] = []
                    parent_task["child_task_ids"].append(task_id)
                    parent_task["updated_at"] = get_timestamp()

                # Add to appropriate key (handle both formats)
                if "tasks" in data:
                    data["tasks"].append(new_task)
                else:
                    if "task" not in data:
                        data["task"] = []
                    data["task"].append(new_task)
                save_json_data(tasks_file, data)

                return {
                    "status": "success",
                    "task": new_task,
                    "message": f"Task {task_id} created successfully"
                }

            except Exception as e:
                return handle_error(e, "task_create")

    @require_project_basics()
    @mcp.tool()
    async def task_update(
        task_id: str,
        status: str = "",
        priority: str = "",
        notes: str = "",
        dependencies: str = "",  # Format: "blocked_by:TASK-001,TASK-002;blocks:TASK-003"
        parent_task_id: str = ""  # New parent (use "none" to clear parent)
    ) -> Dict[str, Any]:
        """Update task status, priority, notes, dependencies, or parent"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error

            # Validate inputs
            if status and not validate_status(status):
                return {
                    "status": "error",
                    "error": f"Invalid status: {status}. Must be one of: pending, in_progress, completed, blocked"
                }

            if priority and not validate_priority(priority):
                return {
                    "status": "error",
                    "error": f"Invalid priority: {priority}. Must be one of: low, medium, high, critical"
                }

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

            # Update fields
            if status:
                task["status"] = status
                # Add completed_at timestamp when completing
                if status == "completed":
                    task["completed_at"] = get_timestamp()
            if priority:
                task["priority"] = priority
            if notes:
                task["notes"] = notes

            # Handle parent_task_id update
            if parent_task_id:
                old_parent_id = task.get("parent_task_id")

                # Handle clearing parent
                if parent_task_id.lower() == "none":
                    # Remove from old parent's child list
                    if old_parent_id:
                        for t in data["tasks"]:
                            if t.get("id") == old_parent_id:
                                child_ids = t.get("child_task_ids", [])
                                if task_id in child_ids:
                                    child_ids.remove(task_id)
                                    t["updated_at"] = get_timestamp()
                                break
                    task["parent_task_id"] = None
                else:
                    # Validate new parent exists
                    new_parent = None
                    for t in data["tasks"]:
                        if t.get("id") == parent_task_id:
                            new_parent = t
                            break

                    if not new_parent:
                        return {
                            "status": "error",
                            "error": f"Parent task {parent_task_id} not found"
                        }

                    # Remove from old parent's child list
                    if old_parent_id and old_parent_id != parent_task_id:
                        for t in data["tasks"]:
                            if t.get("id") == old_parent_id:
                                child_ids = t.get("child_task_ids", [])
                                if task_id in child_ids:
                                    child_ids.remove(task_id)
                                    t["updated_at"] = get_timestamp()
                                break

                    # Add to new parent's child list
                    if "child_task_ids" not in new_parent:
                        new_parent["child_task_ids"] = []
                    if task_id not in new_parent["child_task_ids"]:
                        new_parent["child_task_ids"].append(task_id)
                        new_parent["updated_at"] = get_timestamp()

                    task["parent_task_id"] = parent_task_id

            # Handle dependencies update
            if dependencies:
                if "dependencies" not in task:
                    task["dependencies"] = {"blocks": [], "blocked_by": [], "related": []}

                # Parse dependencies string: "blocked_by:TASK-001,TASK-002;blocks:TASK-003"
                for dep_entry in dependencies.split(";"):
                    if ":" not in dep_entry:
                        continue
                    dep_type, dep_ids = dep_entry.split(":", 1)
                    dep_type = dep_type.strip()

                    if dep_type not in ["blocks", "blocked_by", "related"]:
                        return {
                            "status": "error",
                            "error": f"Invalid dependency type: {dep_type}. Must be: blocks, blocked_by, related"
                        }

                    # Add each dependency ID
                    for dep_id in dep_ids.split(","):
                        dep_id = dep_id.strip()
                        if dep_id and dep_id not in task["dependencies"][dep_type]:
                            task["dependencies"][dep_type].append(dep_id)

            task["updated_at"] = get_timestamp()

            save_json_data(tasks_file, data)

            return {
                "status": "success",
                "task": task,
                "message": f"Task {task_id} updated successfully"
            }

        except Exception as e:
            return handle_error(e, "task_update")
    
    @require_project_basics()
    @mcp.tool()
    async def task_delete(task_ids: str, cascade: bool = False) -> Dict[str, Any]:
        """Delete tasks with optional cascade to children. Use cascade=True to delete subtasks too."""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            # Parse task IDs (comma-separated string)
            if not task_ids:
                return {
                    "status": "error",
                    "error": "No task IDs provided"
                }
            
            id_list = [tid.strip() for tid in task_ids.split(",") if tid.strip()]
            
            if not id_list:
                return {
                    "status": "error", 
                    "error": "No valid task IDs found in input"
                }
            
            # Load data
            tasks_file = project_manager.get_data_file('tasks')
            data = load_json_data(tasks_file)
            tasks = data.get("tasks", [])
            
            # Find tasks to delete (with cascade if requested)
            tasks_to_delete = []
            tasks_to_keep = []
            deleted_ids = set()
            not_found_ids = []

            # First pass: collect explicitly requested tasks
            for task in tasks:
                if task.get("id") in id_list:
                    tasks_to_delete.append(task)
                    deleted_ids.add(task["id"])

            # Check for missing IDs
            for task_id in id_list:
                if task_id not in deleted_ids:
                    not_found_ids.append(task_id)

            # If cascade mode, recursively collect all children
            if cascade:
                def collect_children(parent_id):
                    """Recursively collect all children of a task."""
                    for task in tasks:
                        if task.get("parent_task_id") == parent_id and task["id"] not in deleted_ids:
                            tasks_to_delete.append(task)
                            deleted_ids.add(task["id"])
                            collect_children(task["id"])  # Recurse for nested children

                # Collect children for all tasks to delete
                for task_id in list(deleted_ids):
                    collect_children(task_id)

            # Check if any tasks have children (without cascade mode)
            if not cascade:
                for task in tasks_to_delete:
                    children = [t for t in tasks if t.get("parent_task_id") == task["id"]]
                    if children:
                        return {
                            "status": "error",
                            "error": f"Task {task['id']} has {len(children)} children. Use cascade=True to delete children too.",
                            "children": [{"id": c["id"], "title": c.get("title")} for c in children]
                        }

            # Separate kept vs deleted
            tasks_to_keep = [t for t in tasks if t["id"] not in deleted_ids]
            
            if not tasks_to_delete:
                return {
                    "status": "error",
                    "error": f"None of the specified tasks found: {id_list}",
                    "not_found": not_found_ids
                }
            
            # Clean up dependencies, sprint references, and parent-child relationships
            cleanup_stats = {
                "dependency_cleanups": 0,
                "sprint_cleanups": 0,
                "parent_child_cleanups": 0
            }

            # Remove dependency references
            for task in tasks_to_keep:
                deps = task.get("dependencies", {})
                for dep_type in ["blocks", "blocked_by", "related"]:
                    original_count = len(deps.get(dep_type, []))
                    deps[dep_type] = [d for d in deps.get(dep_type, []) if d not in deleted_ids]
                    cleanup_stats["dependency_cleanups"] += original_count - len(deps[dep_type])

                # Remove deleted tasks from child_task_ids arrays
                if "child_task_ids" in task:
                    original_count = len(task["child_task_ids"])
                    task["child_task_ids"] = [cid for cid in task["child_task_ids"] if cid not in deleted_ids]
                    cleanup_stats["parent_child_cleanups"] += original_count - len(task["child_task_ids"])
            
            # Remove from sprints
            sprints_file = project_manager.get_data_file('sprints')
            sprint_data = load_json_data(sprints_file)
            
            for sprint in sprint_data.get("sprints", []):
                original_count = len(sprint.get("task_ids", []))
                sprint["task_ids"] = [tid for tid in sprint.get("task_ids", []) if tid not in deleted_ids]
                cleanup_stats["sprint_cleanups"] += original_count - len(sprint["task_ids"])
            
            save_json_data(sprints_file, sprint_data)
            
            # Save updated tasks (only keeping tasks not in delete list)
            data["tasks"] = tasks_to_keep
            save_json_data(tasks_file, data)
            
            return {
                "status": "success",
                "message": f"Bulk deleted {len(deleted_ids)} tasks",
                "deleted_tasks": [{"id": t["id"], "title": t.get("title")} for t in tasks_to_delete],
                "deleted_count": len(deleted_ids),
                "not_found": not_found_ids,
                "cleanup_stats": cleanup_stats,
                "warning": "Tasks permanently deleted - this action cannot be undone"
            }
            
        except Exception as e:
            return handle_error(e, "task_delete")

    @require_project_basics()
    @mcp.tool()
    async def get_next_task_full() -> Dict[str, Any]:
        """Get next optimal task with complete execution details, sprint context, and dependency status"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            # Step 1: Get tasks ready to execute (dependency-cleared)
            tasks_file = project_manager.get_data_file('tasks')
            data = load_json_data(tasks_file)
            
            # Get all pending tasks
            pending_tasks = [t for t in data.get('tasks', []) if t.get('status') == 'pending']
            
            # Get all completed task IDs
            completed_task_ids = {t['id'] for t in data.get('tasks', []) if t.get('status') == 'completed'}
            
            # Find tasks ready to execute (all dependencies completed)
            ready_tasks = []
            for task in pending_tasks:
                dependencies = task.get('dependencies', {})
                blocked_by = dependencies.get('blocked_by', [])
                
                # Check if all blocking dependencies are completed
                if all(dep_id in completed_task_ids for dep_id in blocked_by):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                return {
                    "status": "info",
                    "message": "No tasks ready to execute",
                    "pipeline_status": "standby",
                    "pending_count": len(pending_tasks),
                    "blocking_info": "All tasks waiting for dependencies to complete",
                    "next_available": "Complete blocking dependencies first"
                }
            
            # Step 2: Get the highest priority ready task
            priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            ready_tasks.sort(key=lambda t: priority_order.get(t.get('priority', 'medium'), 0), reverse=True)
            selected_task = ready_tasks[0]
            
            # Step 3: Get current sprint context
            sprints_file = project_manager.get_data_file('sprints')
            sprint_data = load_json_data(sprints_file)
            current_sprint = None
            for sprint in sprint_data.get("sprints", []):
                if sprint.get("status") == "active":
                    current_sprint = sprint
                    break
            
            # Step 4: Compile complete execution package
            execution_package = {
                "status": "success",
                "pipeline_status": "ready",
                "selected_task": {
                    "id": selected_task["id"],
                    "title": selected_task["title"], 
                    "description": selected_task["description"],
                    "priority": selected_task["priority"],
                    "complexity": selected_task.get("complexity", "medium"),
                    "phase": selected_task.get("phase"),
                    "estimated_hours": selected_task.get("estimated_hours"),
                    "template_id": selected_task.get("template_id"),
                    "template_name": selected_task.get("template_name"),
                    "task_type": selected_task.get("task_type"),
                    "tags": selected_task.get("tags", []),
                    "dependencies_completed": len(selected_task.get("dependencies", {}).get("blocked_by", [])),
                    "blocks_count": len(selected_task.get("dependencies", {}).get("blocks", [])),
                    "created_at": selected_task.get("created_at"),
                    "sprint_id": selected_task.get("sprint_id")
                },
                "sprint_context": {
                    "has_active_sprint": current_sprint is not None,
                    "sprint_title": current_sprint.get("title") if current_sprint else None,
                    "primary_objective": current_sprint.get("focus", {}).get("primary_objective") if current_sprint else None,
                    "scope_boundaries": current_sprint.get("focus", {}).get("scope_boundaries") if current_sprint else None,
                    "strategic_direction": current_sprint.get("strategic_direction") if current_sprint else None,
                    "architectural_themes": current_sprint.get("architectural_themes") if current_sprint else None
                },
                "execution_readiness": {
                    "dependency_status": "clear",
                    "ready_tasks_count": len(ready_tasks),
                    "pending_tasks_count": len(pending_tasks),
                    "blocking_dependencies": [],
                    "pipeline_position": f"Task 1 of {len(ready_tasks)} ready"
                },
                "agent_guidance": {
                    "mission": "Execute this scoped task exactly to its defined boundaries",
                    "role": "Crucial pipeline component - other agents depend on your precise execution", 
                    "scope_adherence": "No scope creep - complete task as specified",
                    "quality_focus": "Follow established patterns and documentation rules",
                    "completion_workflow": "Use task completion workflow for validation and documentation"
                }
            }
            
            return execution_package
            
        except Exception as e:
            return handle_error(e, "get_next_task_full")
    
    @require_project_basics()
    @mcp.tool()
    async def task_get(task_id: str) -> Dict[str, Any]:
        """Get single task with full details"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
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
            
            return {
                "status": "success",
                "task": task
            }
            
        except Exception as e:
            return handle_error(e, "task_get")
    
    @require_project_basics()
    @mcp.tool()
    async def task_search(
        query: str = "",
        status: str = "",
        priority: str = "",
        limit: str = "50",
        sprint_id: str = "",
        tags: str = ""
    ) -> Dict[str, Any]:
        """Search tasks with comprehensive filtering"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            tasks_file = project_manager.get_data_file('tasks')
            data = load_json_data(tasks_file)
            
            tasks = data.get("tasks", [])
            
            # Apply filters
            if query:
                query = query.lower()
                tasks = [t for t in tasks if 
                        query in t.get("title", "").lower() or 
                        query in t.get("description", "").lower()]
            
            if status:
                tasks = [t for t in tasks if t.get("status") == status]
                
            if priority:
                tasks = [t for t in tasks if t.get("priority") == priority]
            
            if sprint_id:
                tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
            
            # Apply limit
            try:
                limit_num = int(limit)
                tasks = tasks[:limit_num]
            except ValueError:
                pass
            
            return {
                "status": "success",
                "tasks": tasks,
                "total_matches": len(tasks)
            }
            
        except Exception as e:
            return handle_error(e, "task_search")

    @require_project_basics()
    @mcp.tool()
    async def task_get_children(task_id: str) -> Dict[str, Any]:
        """Get direct children (subtasks) of a task"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error

            tasks_file = project_manager.get_data_file('tasks')
            data = load_json_data(tasks_file)

            # Find parent task
            parent_task = None
            for t in data.get("tasks", []):
                if t.get("id") == task_id:
                    parent_task = t
                    break

            if not parent_task:
                return {
                    "status": "error",
                    "error": f"Task {task_id} not found"
                }

            # Get children using parent_task_id
            children = [t for t in data.get("tasks", []) if t.get("parent_task_id") == task_id]

            return {
                "status": "success",
                "parent_task_id": task_id,
                "parent_title": parent_task.get("title"),
                "children": children,
                "children_count": len(children)
            }

        except Exception as e:
            return handle_error(e, "task_get_children")

    @require_project_basics()
    @mcp.tool()
    async def task_get_subtree(task_id: str, depth: int = -1) -> Dict[str, Any]:
        """Get task and all descendants up to specified depth (-1 = unlimited)"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error

            tasks_file = project_manager.get_data_file('tasks')
            data = load_json_data(tasks_file)
            all_tasks = data.get("tasks", [])

            # Find root task
            root_task = None
            for t in all_tasks:
                if t.get("id") == task_id:
                    root_task = t
                    break

            if not root_task:
                return {
                    "status": "error",
                    "error": f"Task {task_id} not found"
                }

            # Build task map for quick lookups
            task_map = {t["id"]: t for t in all_tasks}

            # Recursively collect subtree
            def collect_subtree(tid, current_depth):
                """Recursively collect tasks up to specified depth."""
                if depth >= 0 and current_depth > depth:
                    return []

                task = task_map.get(tid)
                if not task:
                    return []

                result = [task]

                # Get children
                children = [t for t in all_tasks if t.get("parent_task_id") == tid]
                for child in children:
                    result.extend(collect_subtree(child["id"], current_depth + 1))

                return result

            subtree = collect_subtree(task_id, 0)

            return {
                "status": "success",
                "root_task_id": task_id,
                "root_title": root_task.get("title"),
                "subtree": subtree,
                "total_tasks": len(subtree),
                "depth_limit": depth if depth >= 0 else "unlimited"
            }

        except Exception as e:
            return handle_error(e, "task_get_subtree")

