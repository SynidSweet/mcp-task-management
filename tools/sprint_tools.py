"""Sprint management operations - Simplified"""
import json
from datetime import datetime
from typing import Dict, Any, List
from core.project_manager import ProjectManager
from utils.helpers import (
    handle_error,
    load_json_data,
    save_json_data,
    create_sprint_id,
    get_timestamp,
    validate_sprint_status,
    check_project_initialized
)
from utils.validation_wrapper import require_project_basics


def register_sprint_tools(mcp, project_manager: ProjectManager, tool_filter=None):
    """Register sprint tools with simple pattern"""

    if not tool_filter or tool_filter.should_register_tool("sprint_get_current"):
        @require_project_basics()
        @mcp.tool()
        async def sprint_get_current() -> Dict[str, Any]:
            """Get current active sprint with enhanced strategic context"""
            try:

                sprints_file = project_manager.get_data_file('sprints')
                data = load_json_data(sprints_file)

                # Find active sprint
                active_sprint = None
                for sprint in data.get("sprints", []):
                    if sprint.get("status") == "active":
                        active_sprint = sprint
                        break

                if not active_sprint:
                    return {
                        "status": "error",
                        "error": "No active sprint found"
                    }

                return {
                    "status": "success",
                    "current_sprint": active_sprint
                }

            except Exception as e:
                return handle_error(e, "sprint_get_current")
    
    @require_project_basics()
    @mcp.tool()
    async def sprint_update_strategic_context(
        sprint_id: str,
        primary_objective: str = "",
        strategic_direction: str = "",
        architectural_themes: str = "",
        description: str = ""
    ) -> Dict[str, Any]:
        """Update sprint strategic context fields"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            sprints_file = project_manager.get_data_file('sprints')
            data = load_json_data(sprints_file)
            
            # Find sprint
            sprint = None
            for s in data["sprints"]:
                if s.get("id") == sprint_id:
                    sprint = s
                    break
            
            if not sprint:
                return {
                    "status": "error",
                    "error": f"Sprint {sprint_id} not found"
                }
            
            # Update strategic context fields
            if primary_objective:
                sprint["primary_objective"] = primary_objective
            if strategic_direction:
                sprint["strategic_direction"] = strategic_direction
            if architectural_themes:
                sprint["architectural_themes"] = architectural_themes
            if description:
                sprint["description"] = description
                
            sprint["updated_at"] = get_timestamp()
            
            save_json_data(sprints_file, data)
            
            return {
                "status": "success",
                "sprint": sprint,
                "message": f"Sprint {sprint_id} strategic context updated"
            }
            
        except Exception as e:
            return handle_error(e, "sprint_update_strategic_context")
    
    @require_project_basics()
    @mcp.tool()
    async def sprint_add_task(sprint_id: str, task_id: str) -> Dict[str, Any]:
        """Add a task to a sprint"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            sprints_file = project_manager.get_data_file('sprints')
            sprint_data = load_json_data(sprints_file)
            
            # Find sprint
            sprint = None
            for s in sprint_data["sprints"]:
                if s.get("id") == sprint_id:
                    sprint = s
                    break
            
            if not sprint:
                return {
                    "status": "error",
                    "error": f"Sprint {sprint_id} not found"
                }
            
            # Add task to sprint
            if "tasks" not in sprint:
                sprint["tasks"] = []
            
            if task_id not in sprint["tasks"]:
                sprint["tasks"].append(task_id)
                sprint["updated_at"] = get_timestamp()
                
                save_json_data(sprints_file, sprint_data)
                
                # Update task with sprint_id
                tasks_file = project_manager.get_data_file('tasks')
                task_data = load_json_data(tasks_file)
                
                for task in task_data.get("tasks", []):
                    if task.get("id") == task_id:
                        task["sprint_id"] = sprint_id
                        task["updated_at"] = get_timestamp()
                        break
                
                save_json_data(tasks_file, task_data)
                
                return {
                    "status": "success",
                    "message": f"Task {task_id} added to sprint {sprint_id}"
                }
            else:
                return {
                    "status": "success",
                    "message": f"Task {task_id} already in sprint {sprint_id}"
                }
                
        except Exception as e:
            return handle_error(e, "sprint_add_task")
    
    @require_project_basics()
    @mcp.tool()
    async def sprint_remove_task(sprint_id: str, task_id: str) -> Dict[str, Any]:
        """Remove a task from a sprint"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            sprints_file = project_manager.get_data_file('sprints')
            sprint_data = load_json_data(sprints_file)
            
            # Find sprint
            sprint = None
            for s in sprint_data["sprints"]:
                if s.get("id") == sprint_id:
                    sprint = s
                    break
            
            if not sprint:
                return {
                    "status": "error",
                    "error": f"Sprint {sprint_id} not found"
                }
            
            # Remove task from sprint
            if "tasks" in sprint and task_id in sprint["tasks"]:
                sprint["tasks"].remove(task_id)
                sprint["updated_at"] = get_timestamp()
                
                save_json_data(sprints_file, sprint_data)
                
                # Remove sprint_id from task
                tasks_file = project_manager.get_data_file('tasks')
                task_data = load_json_data(tasks_file)
                
                for task in task_data.get("tasks", []):
                    if task.get("id") == task_id:
                        task.pop("sprint_id", None)
                        task["updated_at"] = get_timestamp()
                        break
                
                save_json_data(tasks_file, task_data)
                
                return {
                    "status": "success",
                    "message": f"Task {task_id} removed from sprint {sprint_id}"
                }
            else:
                return {
                    "status": "success", 
                    "message": f"Task {task_id} not in sprint {sprint_id}"
                }
                
        except Exception as e:
            return handle_error(e, "sprint_remove_task")
    
    @require_project_basics()
    @mcp.tool()
    async def sprint_update(
        sprint_id: str,
        title: str = "",
        description: str = "",
        start_date: str = "",
        end_date: str = "",
        capacity: str = "",
        duration: str = "",
        scope_in_scope: str = "",
        scope_out_of_scope: str = "",
        validation_criteria: str = "",
        update_justification: str = ""
    ) -> Dict[str, Any]:
        """Comprehensive sprint update tool - handles all sprint fields except status"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            sprints_file = project_manager.get_data_file('sprints')
            data = load_json_data(sprints_file)
            
            # Find sprint
            sprint = None
            for s in data["sprints"]:
                if s.get("id") == sprint_id:
                    sprint = s
                    break
            
            if not sprint:
                return {
                    "status": "error",
                    "error": f"Sprint {sprint_id} not found"
                }
            
            # Update provided fields
            if title:
                sprint["title"] = title
            if description:
                sprint["description"] = description
            if start_date:
                sprint["start_date"] = start_date
            if end_date:
                sprint["end_date"] = end_date
            if capacity:
                sprint["capacity"] = capacity
            if duration:
                sprint["duration"] = duration
            if scope_in_scope:
                sprint["scope_in_scope"] = scope_in_scope
            if scope_out_of_scope:
                sprint["scope_out_of_scope"] = scope_out_of_scope
            if validation_criteria:
                sprint["validation_criteria"] = validation_criteria
            if update_justification:
                sprint["update_justification"] = update_justification
                
            sprint["updated_at"] = get_timestamp()

            save_json_data(sprints_file, data)

            return {
                "status": "success",
                "sprint": sprint,
                "message": f"Sprint {sprint_id} updated successfully"
            }
            
        except Exception as e:
            return handle_error(e, "sprint_update")
    
    
