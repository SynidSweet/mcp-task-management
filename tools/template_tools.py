"""Template management MCP tools - Simplified architecture"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.project_manager import ProjectManager
from utils.helpers import handle_error
from utils.validation_wrapper import validation_wrapper

logger = logging.getLogger(__name__)

def register_template_tools(mcp, project_manager: ProjectManager):
    """Register template tools with simple pattern"""
    
    @validation_wrapper(require_machine_id=True, require_project=True)
    @mcp.tool()
    async def template_list(scope: str = "all") -> Dict[str, Any]:
        """List available task templates by scope (global/project/all)"""
        try:
            
            # Use legacy file scanning for reliable template discovery
            return await _legacy_template_list(project_manager, scope)
            
        except Exception as e:
            return handle_error(e, "template_list")
    
    @validation_wrapper(require_machine_id=True, require_project=True)
    @mcp.tool()
    async def sprint_template_list(scope: str = "all") -> Dict[str, Any]:
        """List available sprint templates by scope (global/project/all)"""
        try:
            
            # Use legacy file scanning for sprint template discovery
            return await _legacy_sprint_template_list(project_manager, scope)
            
        except Exception as e:
            return handle_error(e, "sprint_template_list")
    
    @mcp.tool()
    async def template_get(template_name: str) -> Dict[str, Any]:
        """Get complete template definition with metadata and source information"""
        try:
            # Use legacy file scanning for reliable template retrieval
            return await _legacy_template_get(project_manager, template_name)
            
        except Exception as e:
            return handle_error(e, "template_get")
    
    @mcp.tool()
    async def sprint_template_get(template_name: str) -> Dict[str, Any]:
        """Get complete sprint template definition with metadata and source information"""
        try:
            # Use legacy file scanning for sprint template retrieval
            return await _legacy_sprint_template_get(project_manager, template_name)
            
        except Exception as e:
            return handle_error(e, "sprint_template_get")
    
    @mcp.tool()
    async def task_create_from_template(
        template_name: str,
        variables: Dict[str, Any] = None,
        sprint_id: str = None,
        priority_override: str = None
    ) -> Dict[str, Any]:
        """Create task hierarchy from template with variable substitution and store in task system"""
        try:
            if variables is None:
                variables = {}
            
            # Get template using legacy method
            template_result = await _legacy_template_get(project_manager, template_name)
            if template_result.get("status") != "success":
                return template_result
            
            template_data = template_result["template"]
            
            # Validate variables against template
            metadata = template_data.get("metadata", {})
            template_variables = metadata.get("variables", [])
            
            # Check for missing required variables
            missing_vars = []
            for var_def in template_variables:
                var_name = var_def["name"]
                if var_def.get("required", True) and var_name not in variables:
                    if "default" not in var_def:
                        missing_vars.append(var_name)
            
            if missing_vars:
                return {
                    "status": "error", 
                    "error": f"Missing required variables: {', '.join(missing_vars)}",
                    "template_name": template_name,
                    "missing_variables": missing_vars
                }
            
            # Apply variable substitution
            processed_template = _substitute_template_variables(template_data, variables)
            
            # Apply overrides
            if sprint_id:
                processed_template["task_definition"]["sprint_id"] = sprint_id
            if priority_override:
                processed_template["task_definition"]["priority"] = priority_override
            
            return {
                "status": "success",
                "template_name": template_name,
                "processed_template": processed_template,
                "variables_applied": variables,
                "message": f"Successfully processed template '{template_name}' with {len(variables)} variables"
            }
            
        except Exception as e:
            return handle_error(e, "task_create_from_template")
    
    @mcp.tool()
    async def sprint_create_from_template(
        template_name: str,
        variables: Dict[str, Any] = None,
        start_date: str = None,
        duration_override: str = None
    ) -> Dict[str, Any]:
        """Create sprint from template with variable substitution and store in sprint system"""
        try:
            if variables is None:
                variables = {}
            
            # Get sprint template using legacy method
            template_result = await _legacy_sprint_template_get(project_manager, template_name)
            if template_result.get("status") != "success":
                return template_result
            
            template_data = template_result["template"]
            
            # Validate variables against template
            metadata = template_data.get("metadata", {})
            template_variables = metadata.get("variables", [])
            
            # Check for missing required variables
            missing_vars = []
            for var_def in template_variables:
                var_name = var_def["name"]
                if var_def.get("required", True) and var_name not in variables:
                    if "default" not in var_def:
                        missing_vars.append(var_name)
            
            if missing_vars:
                return {
                    "status": "error", 
                    "error": f"Missing required variables: {', '.join(missing_vars)}",
                    "template_name": template_name,
                    "missing_variables": missing_vars
                }
            
            # Apply variable substitution
            processed_template = _substitute_template_variables(template_data, variables)
            
            # Apply overrides
            if start_date:
                processed_template["sprint_definition"]["start_date"] = start_date
            if duration_override:
                processed_template["sprint_definition"]["duration"] = duration_override
            
            # Create the actual sprint using the processed template
            sprint_result = await _create_sprint_from_processed_template(
                project_manager, processed_template, template_name, variables
            )
            
            return sprint_result
            
        except Exception as e:
            return handle_error(e, "sprint_create_from_template")

async def _legacy_template_list(project_manager: ProjectManager, scope: str) -> Dict[str, Any]:
    """Template listing using dual storage format."""
    templates = []
    
    # Get project path
    if hasattr(project_manager, 'project_path') and project_manager.project_path:
        project_dir = Path(project_manager.project_path)
    else:
        project_dir = Path('.')
    
    # Check project templates (dual storage format)
    if scope in ["all", "project"]:
        project_templates_file = project_dir / ".claude-tasks" / "templates" / "task_templates.json"
        if project_templates_file.exists():
            templates.extend(_scan_dual_storage_templates(project_templates_file, "project"))
    
    # Check global templates (dual storage format)
    if scope in ["all", "global"]:
        global_templates_file = Path.home() / ".claude" / ".claude-tasks" / "templates" / "task_templates.json"
        if global_templates_file.exists():
            templates.extend(_scan_dual_storage_templates(global_templates_file, "global"))
    
    logger.info(f"Listed {len(templates)} templates from scope: {scope} (legacy)")
    return {
        "status": "success",
        "templates": templates,
        "count": len(templates),
        "scope": scope,
        "mode": "legacy"
    }

async def _legacy_template_get(project_manager: ProjectManager, template_name: str) -> Dict[str, Any]:
    """Template retrieval using dual storage format."""
    # Get project path
    if hasattr(project_manager, 'project_path') and project_manager.project_path:
        project_dir = Path(project_manager.project_path)
    else:
        project_dir = Path('.')
    
    # Look for template in dual storage format (project first, then global)
    template_data = None
    source = None
    
    # Check project templates (dual storage format)
    project_templates_file = project_dir / ".claude-tasks" / "templates" / "task_templates.json"
    if project_templates_file.exists():
        template_data = _get_template_from_dual_storage(project_templates_file, template_name)
        if template_data:
            source = "project"
    
    # Check global templates if not found (dual storage format)
    if not template_data:
        global_templates_file = Path.home() / ".claude" / ".claude-tasks" / "templates" / "task_templates.json"
        if global_templates_file.exists():
            template_data = _get_template_from_dual_storage(global_templates_file, template_name)
            if template_data:
                source = "global"
    
    if not template_data:
        return {
            "status": "error",
            "error": f"Template '{template_name}' not found",
            "template_name": template_name
        }
    
    template_data["source"] = source
    
    logger.info(f"Retrieved template: {template_name} (legacy)")
    return {
        "status": "success",
        "template": template_data,
        "template_name": template_name,
        "source": source
    }

def _scan_templates(directory: Path, source: str) -> List[Dict[str, Any]]:
    """Scan directory for template files and return metadata."""
    templates = []
    
    for template_file in directory.glob("*.json"):
        try:
            template_data = _load_template_file(template_file)
            if template_data and "metadata" in template_data:
                metadata = template_data["metadata"]
                template_summary = {
                    "name": metadata.get("name", template_file.stem),
                    "description": metadata.get("description", "No description"),
                    "category": metadata.get("category", "general"),
                    "source": source,
                    "variables_count": len(metadata.get("variables", [])),
                    "subtasks_count": len(template_data.get("subtasks", [])),
                    "requirements_count": len(template_data.get("requirements", [])),
                    "version": metadata.get("version", "1.0")
                }
                templates.append(template_summary)
        except Exception as e:
            logger.warning(f"Failed to load template {template_file}: {e}")
    
    return templates

def _load_template_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load template from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load template {file_path}: {e}")
        return None

def _substitute_template_variables(template_data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """Substitute template variables in the template data."""
    import copy
    
    # Deep copy to avoid modifying original
    result = copy.deepcopy(template_data)
    
    # Add default values for missing optional variables
    metadata = template_data.get("metadata", {})
    for var_def in metadata.get("variables", []):
        var_name = var_def["name"]
        if var_name not in variables and "default" in var_def:
            variables[var_name] = var_def["default"]
    
    # Recursively substitute variables
    def substitute_in_obj(obj):
        if isinstance(obj, dict):
            return {k: substitute_in_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute_in_obj(item) for item in obj]
        elif isinstance(obj, str):
            result_str = obj
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                result_str = result_str.replace(placeholder, str(var_value))
            return result_str
        else:
            return obj
    
    return substitute_in_obj(result)

async def _legacy_sprint_template_list(project_manager: ProjectManager, scope: str) -> Dict[str, Any]:
    """Sprint template listing using dual storage format."""
    templates = []
    
    # Get project path
    if hasattr(project_manager, 'project_path') and project_manager.project_path:
        project_dir = Path(project_manager.project_path)
    else:
        project_dir = Path('.')
    
    # Check project sprint templates (dual storage format)
    if scope in ["all", "project"]:
        project_templates_file = project_dir / ".claude-tasks" / "templates" / "sprint_templates.json"
        if project_templates_file.exists():
            templates.extend(_scan_dual_storage_sprint_templates(project_templates_file, "project"))
    
    # Check global sprint templates (dual storage format)
    if scope in ["all", "global"]:
        global_templates_file = Path.home() / ".claude" / ".claude-tasks" / "templates" / "sprint_templates.json"
        if global_templates_file.exists():
            templates.extend(_scan_dual_storage_sprint_templates(global_templates_file, "global"))
    
    logger.info(f"Listed {len(templates)} sprint templates from scope: {scope} (legacy)")
    return {
        "status": "success",
        "templates": templates,
        "count": len(templates),
        "scope": scope,
        "mode": "legacy",
        "type": "sprint_template"
    }

async def _legacy_sprint_template_get(project_manager: ProjectManager, template_name: str) -> Dict[str, Any]:
    """Sprint template retrieval using dual storage format."""
    # Get project path
    if hasattr(project_manager, 'project_path') and project_manager.project_path:
        project_dir = Path(project_manager.project_path)
    else:
        project_dir = Path('.')
    
    # Look for sprint template in dual storage format (project first, then global)
    template_data = None
    source = None
    
    # Check project sprint templates (dual storage format)
    project_templates_file = project_dir / ".claude-tasks" / "templates" / "sprint_templates.json"
    if project_templates_file.exists():
        template_data = _get_template_from_dual_storage(project_templates_file, template_name)
        if template_data:
            source = "project"
    
    # Check global sprint templates if not found (dual storage format)
    if not template_data:
        global_templates_file = Path.home() / ".claude" / ".claude-tasks" / "templates" / "sprint_templates.json"
        if global_templates_file.exists():
            template_data = _get_template_from_dual_storage(global_templates_file, template_name)
            if template_data:
                source = "global"
    
    if not template_data:
        return {
            "status": "error",
            "error": f"Sprint template '{template_name}' not found",
            "template_name": template_name
        }
    
    # Validate it's a sprint template
    if template_data.get("metadata", {}).get("category") != "sprint" and "sprint_definition" not in template_data:
        return {
            "status": "error",
            "error": f"Template '{template_name}' is not a valid sprint template",
            "template_name": template_name
        }
    
    template_data["source"] = source
    
    logger.info(f"Retrieved sprint template: {template_name} (legacy)")
    return {
        "status": "success",
        "template": template_data,
        "template_name": template_name,
        "source": source,
        "type": "sprint_template"
    }

def _scan_sprint_templates(directory: Path, source: str) -> List[Dict[str, Any]]:
    """Scan directory for sprint template files and return metadata."""
    templates = []
    
    # Look for files named sprint_*.json or files with category "sprint"
    for template_file in directory.glob("sprint_*.json"):
        try:
            template_data = _load_template_file(template_file)
            if template_data and _is_sprint_template(template_data):
                metadata = template_data.get("metadata", {})
                template_name = template_file.stem.replace("sprint_", "")
                template_summary = {
                    "name": template_name,
                    "description": metadata.get("description", "No description"),
                    "category": "sprint",
                    "source": source,
                    "variables_count": len(metadata.get("variables", [])),
                    "planning_tasks_count": len(template_data.get("planning_tasks", [])),
                    "milestone_tasks_count": len(template_data.get("milestone_tasks", [])),
                    "validation_criteria_count": len(template_data.get("validation_criteria", [])),
                    "version": metadata.get("version", "1.0"),
                    "template_type": "sprint"
                }
                templates.append(template_summary)
        except Exception as e:
            logger.warning(f"Failed to load sprint template {template_file}: {e}")
    
    # Also check regular .json files that might be sprint templates
    for template_file in directory.glob("*.json"):
        if template_file.name.startswith("sprint_"):
            continue  # Already processed above
        
        try:
            template_data = _load_template_file(template_file)
            if template_data and _is_sprint_template(template_data):
                metadata = template_data.get("metadata", {})
                template_summary = {
                    "name": metadata.get("name", template_file.stem),
                    "description": metadata.get("description", "No description"),
                    "category": "sprint", 
                    "source": source,
                    "variables_count": len(metadata.get("variables", [])),
                    "planning_tasks_count": len(template_data.get("planning_tasks", [])),
                    "milestone_tasks_count": len(template_data.get("milestone_tasks", [])),
                    "validation_criteria_count": len(template_data.get("validation_criteria", [])),
                    "version": metadata.get("version", "1.0"),
                    "template_type": "sprint"
                }
                templates.append(template_summary)
        except Exception as e:
            logger.warning(f"Failed to load potential sprint template {template_file}: {e}")
    
    return templates

def _is_sprint_template(template_data: Dict[str, Any]) -> bool:
    """Check if template data represents a sprint template."""
    metadata = template_data.get("metadata", {})
    
    # Check explicit category
    if metadata.get("category") == "sprint":
        return True
    
    # Check for sprint-specific sections
    if "sprint_definition" in template_data:
        return True
    
    # Check for sprint-like structure
    if "planning_tasks" in template_data or "milestone_tasks" in template_data:
        return True
    
    return False

async def _create_sprint_from_processed_template(
    project_manager: ProjectManager, 
    processed_template: Dict[str, Any], 
    template_name: str, 
    variables: Dict[str, Any]
) -> Dict[str, Any]:
    """Create actual sprint from processed template data with robust validation."""
    from datetime import datetime
    from utils.helpers import create_sprint_id, get_timestamp, load_json_data, save_json_data
    import json
    
    # Enhanced error tracking
    operation_log = []
    
    try:
        operation_log.append(f"Starting sprint creation from template '{template_name}'")
        operation_log.append(f"Project directory: {project_manager.project_path}")
        
        # Get sprint data file
        sprints_file = project_manager.get_data_file('sprints')
        operation_log.append(f"Sprint file path: {sprints_file}")
        
        # Validate project directory and file access
        if not Path(sprints_file).parent.exists():
            error_msg = f"Sprint data directory does not exist: {Path(sprints_file).parent}"
            return {
                "status": "error",
                "error": error_msg,
                "operation_log": operation_log
            }
        
        sprint_data = load_json_data(sprints_file)
        initial_sprint_count = len(sprint_data.get('sprints', []))
        operation_log.append(f"Loaded sprint data: {initial_sprint_count} existing sprints")
        
        # Create sprint from template
        sprint_definition = processed_template.get("sprint_definition", {})
        
        sprint = {
            "id": create_sprint_id(),
            "title": sprint_definition.get("title", f"Sprint from {template_name}"),
            "description": sprint_definition.get("description", ""),
            "status": "planned",
            "created_at": get_timestamp(),
            "updated_at": get_timestamp(),
            "template_name": template_name,
            "template_variables": variables,
            "start_date": sprint_definition.get("start_date"),
            "end_date": sprint_definition.get("end_date"),
            "task_ids": [],
            "focus": sprint_definition.get("focus", {}),
            "strategic_direction": sprint_definition.get("strategic_direction", ""),
            "architectural_themes": sprint_definition.get("architectural_themes", []),
            "validation_metrics": {
                "criteria": [],
                "validation_gates": [],
                "success_threshold": 0.8
            },
            "scope_protection": {
                "boundaries": {
                    "in_scope": [],
                    "out_of_scope": []
                },
                "escalation_triggers": [],
                "approved_changes": []
            },
            "progress": {
                "completion_percentage": 0,
                "task_status_counts": {
                    "pending": 0,
                    "in_progress": 0,
                    "blocked": 0,
                    "completed": 0,
                    "failed": 0
                },
                "metrics_snapshot": {}
            },
            "history": [{
                "timestamp": get_timestamp(),
                "event": "created",
                "actor": "template_system",
                "details": f"Sprint created from template '{template_name}'"
            }]
        }
        
        # Add validation criteria from template
        validation_criteria = processed_template.get("validation_criteria", [])
        for i, criterion in enumerate(validation_criteria):
            sprint["validation_metrics"]["criteria"].append({
                "id": f"criterion_{i+1}",
                "description": criterion.get("description", ""),
                "type": criterion.get("type", "completion"),
                "target": criterion.get("target", ""),
                "weight": criterion.get("weight", 0.1),
                "automated": criterion.get("automated", False)
            })
        
        # Add the sprint
        if "sprints" not in sprint_data:
            sprint_data["sprints"] = []
        sprint_data["sprints"].append(sprint)
        operation_log.append(f"Added sprint to collection: {len(sprint_data['sprints'])} total sprints")
        
        # Save sprint data
        save_json_data(sprints_file, sprint_data)
        operation_log.append("Saved sprint data to file")
        
        # CRITICAL VALIDATION: Verify sprint was actually saved
        verification_data = load_json_data(sprints_file)
        saved_sprints = verification_data.get('sprints', [])
        sprint_exists = any(s.get('id') == sprint['id'] for s in saved_sprints)
        
        if not sprint_exists:
            error_msg = f"Sprint {sprint['id']} was not found in file after save - possible file corruption or sync conflict"
            return {
                "status": "error",
                "error": error_msg,
                "operation_log": operation_log,
                "debug_info": {
                    "expected_sprint_id": sprint['id'],
                    "sprints_in_file": len(saved_sprints),
                    "sprint_ids_found": [s.get('id') for s in saved_sprints]
                }
            }
        
        operation_log.append(f"✅ Sprint {sprint['id']} confirmed in file")
        
        # Create planning and milestone tasks from template with dependency resolution
        created_task_ids = []
        template_id_map = {}  # Maps template_id to real task IDs
        all_created_tasks = []  # Store all created tasks for dependency resolution
        
        # Get task storage
        from utils.helpers import create_task_id, load_json_data, save_json_data
        tasks_file = project_manager.get_data_file('tasks')
        tasks_data = load_json_data(tasks_file)
        if "tasks" not in tasks_data:
            tasks_data["tasks"] = []
        
        # Collect all template tasks (planning + milestone)
        all_template_tasks = []
        planning_tasks = processed_template.get("planning_tasks", [])
        milestone_tasks = processed_template.get("milestone_tasks", [])
        
        for task_template in planning_tasks:
            task_template["_task_type"] = "planning"
            all_template_tasks.append(task_template)
        
        for task_template in milestone_tasks:
            task_template["_task_type"] = "milestone"
            all_template_tasks.append(task_template)
        
        # First pass: Create all tasks without dependencies
        for task_template in all_template_tasks:
            try:
                # Generate real task ID using proper incremental format
                task_id = f"TASK-{datetime.now().strftime('%Y')}-{len(tasks_data['tasks']) + len(all_created_tasks) + 1:03d}"
                
                # Map template_id to real ID
                template_id = task_template.get("template_id")
                if template_id:
                    template_id_map[template_id] = task_id
                
                # Create task with basic fields
                task = {
                    "id": task_id,
                    "type": "task",
                    "breakdown_level": 0,
                    "title": task_template.get("title", "Template Task"),
                    "description": task_template.get("description", ""),
                    "priority": task_template.get("priority", "medium"),
                    "status": "pending",
                    "created_at": get_timestamp(),
                    "updated_at": get_timestamp(),
                    "location": "sprint",
                    "assignee": None,
                    "tags": task_template.get("tags", []),
                    "complexity": task_template.get("complexity", "medium"),
                    "dependencies": {
                        "blocks": [],
                        "blocked_by": [],
                        "related": []
                    },
                    "validation": {
                        "required": True,
                        "criteria": [],
                        "gates": []
                    },
                    "context": {
                        "environment": "production",
                        "domain": "documentation_audit",
                        "integration_points": []
                    },
                    "history": [{
                        "timestamp": get_timestamp(),
                        "event": "created",
                        "actor": "template_system",
                        "details": f"Task created from template '{template_name}'"
                    }],
                    # Template metadata
                    "sprint_id": sprint["id"],
                    "template_generated": True,
                    "template_name": template_name,
                    "template_id": template_id,
                    "template_dependencies": task_template.get("dependencies", []),
                    "task_type": task_template.get("_task_type"),
                    "phase": task_template.get("phase"),
                    "estimated_hours": task_template.get("estimated_hours"),
                    "milestone_type": task_template.get("milestone_type"),
                    "schedule_offset": task_template.get("schedule_offset")
                }
                
                all_created_tasks.append(task)
                created_task_ids.append(task_id)
                
            except Exception as e:
                logger.warning(f"Failed to create task from template: {e}")
        
        # Second pass: Resolve template dependencies to real IDs
        for task in all_created_tasks:
            template_dependencies = task.get("template_dependencies", [])
            
            for template_dep in template_dependencies:
                if template_dep.startswith("@"):
                    # Template reference (e.g., "@docs_inventory")
                    template_ref = template_dep[1:]  # Remove @
                    real_dep_id = template_id_map.get(template_ref)
                    
                    if real_dep_id:
                        # Add to blocked_by (this task is blocked by the dependency)
                        task["dependencies"]["blocked_by"].append(real_dep_id)
                        
                        # Find the dependency task and add this task to its blocks
                        for dep_task in all_created_tasks:
                            if dep_task["id"] == real_dep_id:
                                dep_task["dependencies"]["blocks"].append(task["id"])
                                break
                    else:
                        logger.warning(f"Template dependency '{template_ref}' not found for task {task['id']}")
                else:
                    # Assume it's a real task ID (for cross-template dependencies)
                    task["dependencies"]["blocked_by"].append(template_dep)
        
        # Save all created tasks
        tasks_data["tasks"].extend(all_created_tasks)
        save_json_data(tasks_file, tasks_data)
        
        # Update sprint with created task IDs
        sprint["task_ids"] = created_task_ids
        operation_log.append(f"Assigned {len(created_task_ids)} task IDs to sprint")
        
        save_json_data(sprints_file, sprint_data)
        operation_log.append("Updated sprint data with task assignments")
        
        # FINAL VALIDATION: Ensure complete sprint creation success
        final_verification = load_json_data(sprints_file)
        final_sprints = final_verification.get('sprints', [])
        final_sprint = None
        
        for s in final_sprints:
            if s.get('id') == sprint['id']:
                final_sprint = s
                break
        
        if not final_sprint:
            error_msg = f"Sprint {sprint['id']} disappeared after final save - critical sync or storage issue"
            return {
                "status": "error",
                "error": error_msg,
                "operation_log": operation_log,
                "debug_info": {
                    "expected_sprint_id": sprint['id'],
                    "final_sprints_count": len(final_sprints),
                    "final_sprint_ids": [s.get('id') for s in final_sprints]
                }
            }
        
        # Validate task assignments
        final_task_ids = final_sprint.get('task_ids', [])
        if len(final_task_ids) != len(created_task_ids):
            operation_log.append(f"⚠️ Task ID mismatch: expected {len(created_task_ids)}, found {len(final_task_ids)}")
        
        operation_log.append(f"✅ Final validation passed: Sprint {sprint['id']} with {len(final_task_ids)} tasks")
        
        return {
            "status": "success",
            "sprint": final_sprint,  # Return the verified sprint
            "template_name": template_name,
            "variables_applied": variables,
            "tasks_created": len(created_task_ids),
            "operation_log": operation_log,
            "message": f"Sprint '{final_sprint['title']}' created successfully from template '{template_name}'"
        }
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error creating sprint from template: {e}")
        logger.error(f"Full traceback: {error_traceback}")
        
        return {
            "status": "error",
            "error": f"Failed to create sprint from template: {str(e)}",
            "template_name": template_name,
            "operation_log": operation_log,
            "exception_details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "traceback": error_traceback
            },
            "debug_info": {
                "project_path": str(project_manager.project_path) if project_manager.project_path else "None",
                "operation_step": "See operation_log for last successful step"
            }
        }

# New dual storage scanning functions

def _scan_dual_storage_templates(file_path: Path, source: str) -> List[Dict[str, Any]]:
    """Scan dual storage task templates file and return metadata."""
    templates = []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        templates_collection = data.get('templates', {})
        for template_id, template_data in templates_collection.items():
            metadata = template_data.get('metadata', {})
            template_summary = {
                "name": template_id,  # Use template_id as name for consistent lookup
                "display_name": metadata.get("name", template_id),  # Keep original name for display
                "description": metadata.get("description", "No description"),
                "category": metadata.get("category", "general"),
                "source": source,
                "variables_count": len(metadata.get("variables", [])),
                "subtasks_count": len(template_data.get("subtasks", [])),
                "requirements_count": len(template_data.get("requirements", [])),
                "version": metadata.get("version", "1.0"),
                "template_type": "task",
                "scope": metadata.get("scope", source)
            }
            templates.append(template_summary)
            
    except Exception as e:
        logger.warning(f"Failed to load dual storage templates from {file_path}: {e}")
    
    return templates

def _scan_dual_storage_sprint_templates(file_path: Path, source: str) -> List[Dict[str, Any]]:
    """Scan dual storage sprint templates file and return metadata."""
    templates = []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        templates_collection = data.get('templates', {})
        for template_id, template_data in templates_collection.items():
            metadata = template_data.get('metadata', {})
            template_summary = {
                "name": template_id,  # Use template_id as name for consistent lookup
                "display_name": metadata.get("name", template_id),  # Keep original name for display
                "description": metadata.get("description", "No description"),
                "category": metadata.get("category", "sprint"),
                "source": source,
                "variables_count": len(metadata.get("variables", [])),
                "planning_tasks_count": len(template_data.get("planning_tasks", [])),
                "milestone_tasks_count": len(template_data.get("milestone_tasks", [])),
                "validation_criteria_count": len(template_data.get("validation_criteria", [])),
                "version": metadata.get("version", "1.0"),
                "template_type": "sprint",
                "scope": metadata.get("scope", source)
            }
            templates.append(template_summary)
            
    except Exception as e:
        logger.warning(f"Failed to load dual storage sprint templates from {file_path}: {e}")
    
    return templates

def _get_template_from_dual_storage(file_path: Path, template_name: str) -> Optional[Dict[str, Any]]:
    """Get specific template from dual storage file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        templates_collection = data.get('templates', {})
        return templates_collection.get(template_name)
        
    except Exception as e:
        logger.warning(f"Failed to get template {template_name} from {file_path}: {e}")
        return None