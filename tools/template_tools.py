"""Template management MCP tools - Normalized schema architecture

This module provides tools for managing task and sprint templates using normalized
database tables (template_tasks, template_sprints) that mirror the structure of
actual tasks and sprints.

Key Features:
- Templates stored in queryable normalized tables
- Support for template composition (templates referencing other templates)
- Unlimited nesting depth with circular reference detection
- Entry tasks vs nested tasks distinction
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime

from core.project_manager import ProjectManager
from utils.helpers import handle_error, get_timestamp, create_task_id, create_sprint_id, load_json_data, save_json_data
from utils.validation_wrapper import validation_wrapper

logger = logging.getLogger(__name__)

# Database client (imported on demand to avoid circular imports)
def get_db_client():
    """Get Supabase database client"""
    from tools.document_tools import get_supabase_client
    client, _ = get_supabase_client()
    return client


def register_template_tools(mcp, project_manager: ProjectManager, tool_filter=None):
    """Register template tools with MCP server"""
    
    # ========================================================================
    # TASK TEMPLATE TOOLS
    # ========================================================================
    
    @validation_wrapper(require_machine_id=True, require_project=True)
    @mcp.tool()
    async def template_list(
        scope: str = "all",
        category: str = None,
        entry_tasks_only: bool = True
    ) -> Dict[str, Any]:
        """
        List available task templates from normalized database.

        Args:
            scope: Filter by scope ("all", "global", "project")
            category: Filter by category (e.g., "infrastructure", "quality")
            entry_tasks_only: If True, only show entry tasks (not nested subtasks)

        Returns:
            List of task templates with metadata
        """
        try:
            client = get_db_client()
            
            # Build query
            query = client.table('template_tasks').select(
                'template_id, template_name, description, category, scope, '
                'is_entry_task, variables, child_template_ids, references_template_id'
            )
            
            # Apply filters
            if scope != "all":
                query = query.eq('scope', scope)
            
            if category:
                query = query.eq('category', category)
            
            if entry_tasks_only:
                query = query.eq('is_entry_task', True)
            
            # Execute query
            result = query.execute()
            
            # Format response
            templates = []
            for task in result.data:
                template_summary = {
                    "name": task['template_id'],
                    "display_name": task['template_name'],
                    "description": task['description'] or "No description",
                    "category": task['category'],
                    "scope": task['scope'],
                    "variables_count": len(task.get('variables', [])),
                    "child_count": len(task.get('child_template_ids', [])),
                    "is_reference": task.get('references_template_id') is not None,
                    "template_type": "task"
                }
                templates.append(template_summary)
            
            logger.info(f"Listed {len(templates)} task templates (scope={scope}, entry_only={entry_tasks_only})")
            return {
                "status": "success",
                "templates": templates,
                "count": len(templates),
                "scope": scope,
                "entry_tasks_only": entry_tasks_only
            }

        except Exception as e:
            return handle_error(e, "template_list")

    @mcp.tool()
    async def template_get(
        template_id: str,
        resolve_references: bool = True,
        resolve_children: bool = True
    ) -> Dict[str, Any]:
        """
        Get a task template with optional resolution of references and children.
        
        Args:
            template_id: The template_id to retrieve
            resolve_references: If True, recursively resolve referenced templates
            resolve_children: If True, include resolved children in response
        
        Returns:
            Complete template definition with resolved structure
        """
        try:
            client = get_db_client()
            
            # Load main template
            result = client.table('template_tasks').select('*').eq('template_id', template_id).execute()
            
            if not result.data:
                return {
                    "status": "error",
                    "error": f"Template '{template_id}' not found",
                    "template_id": template_id
                }
            
            template_data = result.data[0]
            
            # Resolve references and children if requested
            if resolve_references or resolve_children:
                template_data = await _resolve_template_task_full(
                    template_id,
                    resolve_refs=resolve_references,
                    resolve_children=resolve_children
                )
            
            logger.info(f"Retrieved template: {template_id} (resolve_refs={resolve_references}, resolve_children={resolve_children})")
            return {
                "status": "success",
                "template": template_data,
                "template_id": template_id
            }

        except Exception as e:
            return handle_error(e, "template_get")
    
    # ========================================================================
    # SPRINT TEMPLATE TOOLS
    # ========================================================================
    
    @validation_wrapper(require_machine_id=True, require_project=True)
    @mcp.tool()
    async def sprint_template_list(
        scope: str = "all"
    ) -> Dict[str, Any]:
        """
        List available sprint templates from normalized database.

        Args:
            scope: Filter by scope ("all", "global", "project")

        Returns:
            List of sprint templates with metadata
        """
        try:
            client = get_db_client()
            
            # Build query
            query = client.table('template_sprints').select(
                'template_id, template_name, description, scope, '
                'variables, task_ids'
            )
            
            # Apply scope filter
            if scope != "all":
                query = query.eq('scope', scope)
            
            # Execute query
            result = query.execute()
            
            # Format response
            templates = []
            for sprint in result.data:
                template_summary = {
                    "name": sprint['template_id'],
                    "display_name": sprint['template_name'],
                    "description": sprint['description'] or "No description",
                    "scope": sprint['scope'],
                    "variables_count": len(sprint.get('variables', [])),
                    "tasks_count": len(sprint.get('task_ids', [])),
                    "template_type": "sprint"
                }
                templates.append(template_summary)
            
            logger.info(f"Listed {len(templates)} sprint templates (scope={scope})")
            return {
                "status": "success",
                "templates": templates,
                "count": len(templates),
                "scope": scope,
                "type": "sprint_template"
            }

        except Exception as e:
            return handle_error(e, "sprint_template_list")
    
    @mcp.tool()
    async def sprint_template_get(
        template_id: str,
        resolve_tasks: bool = True
    ) -> Dict[str, Any]:
        """
        Get a sprint template with optional task resolution.

        Args:
            template_id: The sprint template_id to retrieve
            resolve_tasks: If True, resolve all assigned task templates

        Returns:
            Complete sprint template with resolved tasks
        """
        try:
            client = get_db_client()
            
            # Load sprint template
            result = client.table('template_sprints').select('*').eq('template_id', template_id).execute()
            
            if not result.data:
                return {
                    "status": "error",
                    "error": f"Sprint template '{template_id}' not found",
                    "template_id": template_id
                }
            
            sprint_data = result.data[0]
            
            # Resolve tasks if requested
            if resolve_tasks:
                resolved_tasks = []
                for task_id in sprint_data.get('task_ids', []):
                    task = await _resolve_template_task_full(task_id, resolve_refs=True, resolve_children=True)
                    resolved_tasks.append(task)

                sprint_data['resolved_tasks'] = resolved_tasks
            
            logger.info(f"Retrieved sprint template: {template_id} (resolve_tasks={resolve_tasks})")
            return {
                "status": "success",
                "template": sprint_data,
                "template_id": template_id,
                "type": "sprint_template"
            }

        except Exception as e:
            return handle_error(e, "sprint_template_get")
    
    # ========================================================================
    # TEMPLATE INSTANTIATION TOOLS
    # ========================================================================
    
    @mcp.tool()
    async def task_create_from_template(
        template_id: str,
        variables: Dict[str, Any] = None,
        sprint_id: str = None,
        priority_override: str = None
    ) -> Dict[str, Any]:
        """
        Create actual task(s) from a task template.
        
        Args:
            template_id: The task template to instantiate
            variables: Variable values for substitution
            sprint_id: Optional sprint to assign tasks to
            priority_override: Optional priority override
        
        Returns:
            Created task IDs and details
        """
        try:
            if variables is None:
                variables = {}
            
            # Load and resolve template
            template_data = await _resolve_template_task_full(
                template_id,
                resolve_refs=True,
                resolve_children=True
            )
            
            # Validate required variables
            missing_vars = []
            for var_def in template_data.get('variables', []):
                var_name = var_def.get('name')
                if var_def.get('required', True) and var_name not in variables:
                    if 'default' not in var_def:
                        missing_vars.append(var_name)
            
            if missing_vars:
                return {
                    "status": "error",
                    "error": f"Missing required variables: {', '.join(missing_vars)}",
                    "template_id": template_id,
                    "missing_variables": missing_vars
                }
            
            # Create tasks from template
            created_tasks = await _create_tasks_from_template_recursive(
                template_data,
                variables,
                sprint_id,
                priority_override,
                project_manager
            )
            
            return {
                "status": "success",
                "template_id": template_id,
                "created_tasks": created_tasks,
                "tasks_count": len(created_tasks),
                "variables_applied": variables,
                "message": f"Successfully created {len(created_tasks)} task(s) from template '{template_id}'"
            }
            
        except Exception as e:
            return handle_error(e, "task_create_from_template")
    
    @mcp.tool()
    async def sprint_create_from_template(
        template_id: str,
        variables: Dict[str, Any] = None,
        start_date: str = None,
        duration_override: str = None
    ) -> Dict[str, Any]:
        """
        Create actual sprint from a sprint template.
        
        Args:
            template_id: The sprint template to instantiate
            variables: Variable values for substitution
            start_date: Optional start date override
            duration_override: Optional duration override
        
        Returns:
            Created sprint and task details
        """
        try:
            if variables is None:
                variables = {}
            
            # Load sprint template with resolved tasks
            template_result = await sprint_template_get(template_id, resolve_tasks=True)
            if template_result.get('status') != 'success':
                return template_result
            
            template_data = template_result['template']
            
            # Validate required variables
            missing_vars = []
            for var_def in template_data.get('variables', []):
                var_name = var_def.get('name')
                if var_def.get('required', True) and var_name not in variables:
                    if 'default' not in var_def:
                        missing_vars.append(var_name)
            
            if missing_vars:
                return {
                    "status": "error",
                    "error": f"Missing required variables: {', '.join(missing_vars)}",
                    "template_id": template_id,
                    "missing_variables": missing_vars
                }
            
            # Create sprint from template
            sprint_result = await _create_sprint_from_template_full(
                template_data,
                variables,
                start_date,
                duration_override,
                project_manager
            )
            
            return sprint_result
            
        except Exception as e:
            return handle_error(e, "sprint_create_from_template")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _resolve_template_task_full(
    template_id: str,
    resolve_refs: bool = True,
    resolve_children: bool = True,
    visited: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Fully resolve a template task including references and children.
    
    Args:
        template_id: Template to resolve
        resolve_refs: If True, resolve referenced templates
        resolve_children: If True, recursively resolve children
        visited: Set of visited template IDs (for circular detection)
    
    Returns:
        Fully resolved template data
    
    Raises:
        ValueError: If circular reference detected
    """
    if visited is None:
        visited = set()
    
    # Circular reference detection
    if template_id in visited:
        cycle_path = " -> ".join(visited) + f" -> {template_id}"
        raise ValueError(f"Circular reference detected: {cycle_path}")
    
    visited.add(template_id)
    
    # Load template from database
    client = get_db_client()
    result = client.table('template_tasks').select('*').eq('template_id', template_id).execute()
    
    if not result.data:
        raise ValueError(f"Template '{template_id}' not found")
    
    task = dict(result.data[0])  # Make mutable copy
    
    # If this is a reference, load the referenced template
    if task.get('references_template_id') and resolve_refs:
        referenced = await _resolve_template_task_full(
            task['references_template_id'],
            resolve_refs=True,
            resolve_children=resolve_children,
            visited=visited.copy()  # Copy to avoid cross-branch pollution
        )
        
        # Merge: use referenced template's content with local overrides
        task = _merge_template_reference(task, referenced)
    
    # Resolve children if requested
    if resolve_children and task.get('child_template_ids'):
        resolved_children = []
        for child_id in task['child_template_ids']:
            try:
                child = await _resolve_template_task_full(
                    child_id,
                    resolve_refs=resolve_refs,
                    resolve_children=True,
                    visited=visited.copy()
                )
                resolved_children.append(child)
            except Exception as e:
                logger.warning(f"Failed to resolve child {child_id}: {e}")
        
        task['resolved_children'] = resolved_children
    
    return task


def _merge_template_reference(ref_task: Dict[str, Any], referenced_task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge a reference task with its referenced template.
    
    The reference task can override certain fields from the referenced template.
    
    Args:
        ref_task: The task that references another template
        referenced_task: The template being referenced
    
    Returns:
        Merged template data
    """
    merged = dict(referenced_task)  # Start with referenced template
    
    # Override with reference task's values (if not empty)
    if ref_task.get('title'):
        merged['title'] = ref_task['title']
    if ref_task.get('task_description'):
        merged['task_description'] = ref_task['task_description']
    if ref_task.get('priority'):
        merged['priority'] = ref_task['priority']
    if ref_task.get('notes'):
        merged['notes'] = ref_task['notes']
    
    # Merge variables (reference overrides take precedence)
    merged['override_variables'] = ref_task.get('override_variables', {})
    
    # Keep reference metadata
    merged['_is_reference'] = True
    merged['_reference_to'] = ref_task['references_template_id']
    merged['_reference_id'] = ref_task['template_id']
    
    return merged


def _substitute_variables(template_data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Substitute variables in template data.
    
    Recursively replaces {{variable_name}} placeholders with actual values.
    
    Args:
        template_data: Template data containing placeholders
        variables: Variable values for substitution
    
    Returns:
        Template data with variables substituted
    """
    import copy
    
    result = copy.deepcopy(template_data)
    
    # Add default values for missing optional variables
    for var_def in template_data.get('variables', []):
        var_name = var_def.get('name')
        if var_name not in variables and 'default' in var_def:
            variables[var_name] = var_def['default']
    
    # Recursively substitute
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


async def _create_tasks_from_template_recursive(
    template_data: Dict[str, Any],
    variables: Dict[str, Any],
    sprint_id: Optional[str],
    priority_override: Optional[str],
    project_manager: ProjectManager,
    parent_task_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Create actual tasks from template data recursively.
    
    Args:
        template_data: Resolved template data
        variables: Variable values
        sprint_id: Optional sprint assignment
        priority_override: Optional priority override
        project_manager: Project manager instance
        parent_task_id: Optional parent task ID for hierarchy
    
    Returns:
        List of created tasks
    """
    # Substitute variables
    processed = _substitute_variables(template_data, variables)
    
    # Load tasks data
    tasks_file = project_manager.get_data_file('tasks')
    tasks_data = load_json_data(tasks_file)
    if 'tasks' not in tasks_data:
        tasks_data['tasks'] = []
    
    # Create main task
    task_id = create_task_id()
    actual_task = {
        'id': task_id,
        'title': processed.get('title', 'Untitled Task'),
        'description': processed.get('task_description', ''),
        'priority': priority_override or processed.get('priority', 'medium'),
        'status': 'pending',
        'notes': processed.get('notes', ''),
        'sprint_id': sprint_id,
        'parent_task_id': parent_task_id,
        'child_task_ids': [],
        'dependencies': processed.get('dependencies', {'blocks': [], 'blocked_by': [], 'related': []}),
        'created_at': get_timestamp(),
        'updated_at': get_timestamp(),
        'completed_at': None
    }
    
    # Save task
    tasks_data['tasks'].append(actual_task)
    save_json_data(tasks_file, tasks_data)
    
    created_tasks = [actual_task]
    child_ids = []
    
    # Recursively create children
    if processed.get('resolved_children'):
        for child_template in processed['resolved_children']:
            child_tasks = await _create_tasks_from_template_recursive(
                child_template,
                variables,
                sprint_id,
                None,  # Don't override priority for children
                project_manager,
                parent_task_id=task_id
            )
            created_tasks.extend(child_tasks)
            if child_tasks:
                child_ids.append(child_tasks[0]['id'])
    
    # Update parent with child IDs
    if child_ids:
        # Reload to get fresh data
        tasks_data = load_json_data(tasks_file)
        for task in tasks_data['tasks']:
            if task['id'] == task_id:
                task['child_task_ids'] = child_ids
                break
        save_json_data(tasks_file, tasks_data)
    
    return created_tasks


async def _create_sprint_from_template_full(
    template_data: Dict[str, Any],
    variables: Dict[str, Any],
    start_date: Optional[str],
    duration_override: Optional[str],
    project_manager: ProjectManager
) -> Dict[str, Any]:
    """
    Create actual sprint from template data with all tasks.
    
    Args:
        template_data: Resolved sprint template data
        variables: Variable values
        start_date: Optional start date override
        duration_override: Optional duration override
        project_manager: Project manager instance
    
    Returns:
        Created sprint and tasks
    """
    from utils.helpers import create_sprint_id
    
    # Substitute variables
    processed = _substitute_variables(template_data, variables)
    
    # Load sprint data
    sprints_file = project_manager.get_data_file('sprints')
    sprint_data = load_json_data(sprints_file)
    if 'sprints' not in sprint_data:
        sprint_data['sprints'] = []
    
    # Create sprint
    sprint_id = create_sprint_id()
    focus = processed.get('focus', {})
    if not isinstance(focus, dict):
        focus = {}
    
    sprint = {
        'id': sprint_id,
        'title': processed.get('title', 'Untitled Sprint'),
        'description': processed.get('sprint_description', ''),
        'status': 'planning',
        'task_ids': [],
        'start_date': start_date or processed.get('start_date'),
        'end_date': processed.get('end_date'),
        'focus': focus,
        'created_at': get_timestamp(),
        'updated_at': get_timestamp()
    }
    
    # Save sprint
    sprint_data['sprints'].append(sprint)
    save_json_data(sprints_file, sprint_data)
    
    # Create tasks from template
    all_created_tasks = []

    # Create all tasks
    for task_template in processed.get('resolved_tasks', []):
        tasks = await _create_tasks_from_template_recursive(
            task_template,
            variables,
            sprint_id,
            None,
            project_manager
        )
        all_created_tasks.extend(tasks)
    
    # Update sprint with task IDs
    task_ids = [task['id'] for task in all_created_tasks]
    sprint_data = load_json_data(sprints_file)
    for s in sprint_data['sprints']:
        if s['id'] == sprint_id:
            s['task_ids'] = task_ids
            break
    save_json_data(sprints_file, sprint_data)
    
    return {
        'status': 'success',
        'sprint': sprint,
        'created_tasks': all_created_tasks,
        'tasks_count': len(all_created_tasks),
        'variables_applied': variables,
        'message': f"Sprint '{sprint['title']}' created successfully from template with {len(all_created_tasks)} tasks"
    }
