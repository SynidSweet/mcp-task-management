"""System-level operations and health checks - Simplified"""
from typing import Dict, Any
from datetime import datetime
from core.project_manager import ProjectManager
from utils.helpers import handle_error, check_project_initialized


def register_system_tools(mcp, project_manager: ProjectManager):
    """Register system tools with simple pattern"""
    
    @mcp.tool()
    async def system_set_project_directory(project_dir: str) -> Dict[str, Any]:
        """Set project directory - simplified (no ContextDetector needed)"""
        try:
            return project_manager.set_project_directory(project_dir)
        except Exception as e:
            return handle_error(e, "system_set_project_directory")
    
    @mcp.tool() 
    async def system_health_check() -> Dict[str, Any]:
        """Health check - simplified (no complex validation)"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return {**init_error, "status": "not_initialized"}
            
            # Simple file existence check
            data_files = {}
            for data_type in ["tasks", "sprints", "backlog", "journal"]:
                try:
                    file_path = project_manager.get_data_file(data_type)
                    data_files[data_type] = {
                        "path": str(file_path),
                        "exists": file_path.exists()
                    }
                except Exception as e:
                    data_files[data_type] = {"error": str(e)}
            
            return {
                "status": "success",
                "project_path": str(project_manager.project_path),
                "data_files": data_files
            }
        except Exception as e:
            return handle_error(e, "system_health_check")

    @mcp.tool()
    async def workflow_load_context(
        context_detail_level: str = "standard",
        include_session_history: bool = True,
        include_sprint_details: bool = True,
        include_system_state: bool = True,
        include_task_selection: bool = True,
        max_response_size: str = "standard"
    ) -> Dict[str, Any]:
        """Load comprehensive context for agent workflows"""
        try:
            init_error = check_project_initialized(project_manager)
            if init_error:
                return init_error
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "project_overview": {
                    "purpose": "MCP Task Management System",
                    "status": "Simplified Architecture - Post-simplification"
                },
                "system_state": {
                    "initialized": project_manager.is_initialized(),
                    "project_path": str(project_manager.project_path),
                    "architecture": "Simplified - Function-based tools"
                },
                "note": "Simplified architecture - direct function-based implementation"
            }
        except Exception as e:
            return handle_error(e, "workflow_load_context")