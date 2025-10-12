"""
Validation Wrapper System - Error Message Injection

Comprehensive validation system that intercepts tool calls and injects 
error messages when system requirements aren't met. Designed to handle 
multiple validation scenarios consistently across all MCP tools.
"""

import os
import functools
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime


class ValidationError:
    """Structured validation error with setup instructions"""
    
    def __init__(
        self,
        error_type: str,
        message: str,
        setup_commands: List[str] = None,
        documentation_links: List[str] = None,
        note: str = ""
    ):
        self.error_type = error_type
        self.message = message
        self.setup_commands = setup_commands or []
        self.documentation_links = documentation_links or []
        self.note = note
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool response format"""
        result = {
            "status": "validation_error",
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.setup_commands:
            result["setup_commands"] = self.setup_commands
            
        if self.documentation_links:
            result["documentation"] = self.documentation_links
            
        if self.note:
            result["note"] = self.note
            
        return result


class SystemValidators:
    """Collection of system-level validation checks"""
    
    @staticmethod
    def validate_machine_id() -> Optional[ValidationError]:
        """Validate machine ID configuration"""
        from core.machine_id import validate_machine_id, get_machine_config_path

        error_type = validate_machine_id()
        if not error_type:
            return None

        config_file = get_machine_config_path()
        error_messages = {
            "missing_config_file": "Machine ID configuration file not found",
            "missing_machine_id": "machine_id not found in configuration file",
            "auto_generated_id": "Machine ID appears to be auto-generated",
            "corrupted_config": "Invalid machine configuration file format"
        }

        return ValidationError(
            error_type=error_type,
            message=error_messages.get(error_type, "Machine ID validation failed"),
            setup_commands=[f'echo \'{{"machine_id": "your-descriptive-machine-name", "description": "Machine identifier", "created_at": "$(date -Iseconds)", "version": "1.0"}}\' > {config_file}'],
            note="Choose a descriptive name for this machine (e.g., 'dev-laptop-alice', 'production-server-01')"
        )
    
    @staticmethod
    def validate_project_initialized(project_manager) -> Optional[ValidationError]:
        """Validate project is properly initialized"""
        if not project_manager.is_initialized():
            return ValidationError(
                error_type="project_not_initialized",
                message="No project directory set",
                setup_commands=[
                    'claude mcp add claude-tasks python server.py --project-dir "$(pwd)"',
                    "# Or use MCP tool: system_set_project_directory"
                ],
                note="Project directory must be set before using task management tools"
            )
        return None
    
    @staticmethod
    def validate_git_repository(project_manager) -> Optional[ValidationError]:
        """Validate we're in a git repository (for git tools only)"""
        if not project_manager.is_initialized():
            return None  # Let project validation handle this
            
        git_dir = project_manager.project_path / '.git'
        if not git_dir.exists():
            return ValidationError(
                error_type="not_git_repository",
                message="Current directory is not a Git repository",
                setup_commands=[
                    "git init",
                    "# Or navigate to an existing Git repository"
                ],
                note="Git tools require a Git repository to function"
            )
        return None
    
    @staticmethod
    def validate_supabase_connection() -> Optional[ValidationError]:
        """Validate Supabase connection (for sync tools only)"""
        try:
            from supabase import create_client
        except ImportError:
            return ValidationError(
                error_type="supabase_not_available",
                message="Supabase library not installed",
                setup_commands=[
                    "pip install supabase",
                    "# Or install with: pip install -r requirements.txt"
                ],
                note="Supabase is required for data synchronization tools"
            )
        return None


def validation_wrapper(
    *,
    require_machine_id: bool = True,
    require_project: bool = True, 
    require_git: bool = False,
    require_supabase: bool = False,
    custom_validators: List[Callable[[], Optional[ValidationError]]] = None
):
    """
    Decorator that validates system requirements before executing MCP tools.
    
    Args:
        require_machine_id: Check machine ID configuration file
        require_project: Check project initialization
        require_git: Check Git repository (for git tools)
        require_supabase: Check Supabase availability (for sync tools)
        custom_validators: Additional validation functions
        
    Usage:
        @validation_wrapper(require_machine_id=True, require_project=True)
        @mcp.tool()
        async def task_create(title: str) -> Dict[str, Any]:
            # Tool implementation - only runs if validations pass
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # Extract project_manager from args (assumes it's passed to tool functions)
            project_manager = None
            if args and hasattr(args[0], 'project_path'):
                project_manager = args[0]
            elif 'project_manager' in kwargs:
                project_manager = kwargs['project_manager']
            
            # Run validation checks in order
            validators_to_run = []
            
            if require_machine_id:
                validators_to_run.append(SystemValidators.validate_machine_id)
            
            if require_project:
                validators_to_run.append(
                    lambda: SystemValidators.validate_project_initialized(project_manager)
                )
            
            if require_git:
                validators_to_run.append(
                    lambda: SystemValidators.validate_git_repository(project_manager)
                )
            
            if require_supabase:
                validators_to_run.append(SystemValidators.validate_supabase_connection)
            
            if custom_validators:
                validators_to_run.extend(custom_validators)
            
            # Execute validations
            for validator in validators_to_run:
                error = validator()
                if error:
                    # Return validation error instead of executing tool
                    return error.to_dict()
            
            # All validations passed - execute the original tool
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_tool_execution(
    tool_name: str,
    project_manager=None,
    require_machine_id: bool = True,
    require_project: bool = True,
    require_git: bool = False,
    require_supabase: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Standalone validation function for tools that don't use decorators.
    Returns validation error dict or None if all checks pass.
    
    Usage:
        def my_tool():
            error = validate_tool_execution("my_tool", project_manager)
            if error:
                return error
            # Continue with tool logic...
    """
    validators = []
    
    if require_machine_id:
        validators.append(SystemValidators.validate_machine_id)
    
    if require_project:
        validators.append(
            lambda: SystemValidators.validate_project_initialized(project_manager)
        )
    
    if require_git:
        validators.append(
            lambda: SystemValidators.validate_git_repository(project_manager)
        )
    
    if require_supabase:
        validators.append(SystemValidators.validate_supabase_connection)
    
    for validator in validators:
        error = validator()
        if error:
            return error.to_dict()
    
    return None


# Convenience functions for common validation patterns
def require_machine_id_only():
    """Decorator for tools that only need machine ID validation"""
    return validation_wrapper(
        require_machine_id=True,
        require_project=False,
        require_git=False,
        require_supabase=False
    )


def require_project_basics():
    """Decorator for standard project tools"""
    return validation_wrapper(
        require_machine_id=True,
        require_project=True,
        require_git=False,
        require_supabase=False
    )


def require_git_tools():
    """Decorator for Git-related tools"""
    return validation_wrapper(
        require_machine_id=True,
        require_project=True,
        require_git=True,
        require_supabase=False
    )


def require_sync_tools():
    """Decorator for Supabase sync tools"""
    return validation_wrapper(
        require_machine_id=True,
        require_project=True,
        require_git=False,
        require_supabase=True
    )