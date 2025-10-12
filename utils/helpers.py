"""Simple utility functions for MCP tools"""
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import os


def handle_error(error: Exception, tool_name: str) -> Dict[str, Any]:
    """Simple error handling utility"""
    return {
        "status": "error",
        "error": str(error),
        "tool": tool_name,
        "details": {
            "type": type(error).__name__,
            "message": str(error)
        }
    }


def check_project_initialized(project_manager) -> Optional[Dict[str, Any]]:
    """Check if project is initialized, return error dict if not"""
    if not project_manager.is_initialized():
        return {
            "status": "error",
            "error": "No project directory set - MCP server not properly configured for this project",
            "solution": "Use system_set_project_directory tool to set correct project directory",
            "immediate_fix": 'Use: mcp__claude-tasks__system_set_project_directory with project_dir: "."',
            "permanent_fix": 'Re-register MCP server: claude mcp add claude-tasks /home/ubuntu/.claude/task-sprint-system/mcp-server/venv/bin/python /home/ubuntu/.claude/task-sprint-system/mcp-server/server.py -- --project-dir "$(pwd)"',
            "explanation": "Template operations require correct project context to avoid cross-project contamination"
        }
    return None




def load_json_data(file_path: Path) -> Dict[str, Any]:
    """Simple JSON file loading with defaults"""
    if not file_path.exists():
        return get_default_data(file_path.stem)
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        # Return default data if file is corrupted
        return get_default_data(file_path.stem)


def save_json_data(file_path: Path, data: Dict[str, Any]) -> None:
    """Simple JSON file saving with atomic writes"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Atomic write
    temp_path = file_path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)
    temp_path.rename(file_path)


def get_default_data(data_type: str) -> Dict[str, Any]:
    """Return default data structure for data type"""
    defaults = {
        'tasks': {"tasks": [], "metadata": {"version": "1.0"}},
        'sprints': {"sprints": [], "metadata": {"version": "1.0"}},
        'journal': {"journal": [], "metadata": {"version": "1.0"}},
        'backlog': {"backlog": [], "metadata": {"version": "1.0"}}
    }
    
    default_data = defaults.get(data_type, {})
    if "metadata" in default_data:
        default_data["metadata"]["created_at"] = datetime.now().isoformat()
    
    return default_data


def create_task_id() -> str:
    """Generate a new task ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"TASK-{timestamp}"


def create_sprint_id() -> str:
    """Generate a new sprint ID"""  
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"SPRINT-{timestamp}"


def create_session_id() -> str:
    """Generate a new session ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
    return f"SESSION-{timestamp}"


def get_timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.now().isoformat()


def validate_priority(priority: str) -> bool:
    """Validate priority value"""
    return priority in ["low", "medium", "high", "critical"]


def validate_status(status: str) -> bool:
    """Validate status value"""
    return status in ["pending", "in_progress", "completed", "blocked"]


def validate_sprint_status(status: str) -> bool:
    """Validate sprint status value"""
    return status in ["planning", "active", "completed", "cancelled"]