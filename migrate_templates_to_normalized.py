#!/usr/bin/env python3
"""
Migrate existing template JSON files to normalized database tables.

This script:
1. Reads task_templates.json and sprint_templates.json
2. Breaks apart templates into individual template_task and template_sprint records
3. Inserts into new normalized tables
4. Preserves template composition via references
"""

import json
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

# Import database client
from tools.document_tools import get_supabase_client
from core.project_manager import ProjectManager
from utils.helpers import get_timestamp

# Initialize clients
client, _ = get_supabase_client()

async def get_project_id(project_path: str) -> str:
    """Get or create project ID for templates"""
    try:
        result = client.table('projects').select('id').eq('path', project_path).execute()
        if result.data:
            return result.data[0]['id']
        else:
            # Create project
            result = client.table('projects').insert({
                'path': project_path,
                'name': Path(project_path).name,
                'machine_id': 'migration_script'
            }).execute()
            return result.data[0]['id']
    except Exception as e:
        print(f"Error getting project ID: {e}")
        return None

async def insert_template_task(task_data: Dict[str, Any]) -> None:
    """Insert a template task record"""
    try:
        result = client.table('template_tasks').insert(task_data).execute()
        if result.data:
            print(f"  ✓ Inserted template_task: {task_data['template_id']}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"  ✗ Error inserting template_task {task_data.get('template_id')}: {e}")
        return None

async def insert_template_sprint(sprint_data: Dict[str, Any]) -> None:
    """Insert a template sprint record"""
    try:
        result = client.table('template_sprints').insert(sprint_data).execute()
        if result.data:
            print(f"  ✓ Inserted template_sprint: {sprint_data['template_id']}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"  ✗ Error inserting template_sprint {sprint_data.get('template_id')}: {e}")
        return None

async def migrate_task_template(
    template_id: str,
    template_data: Dict[str, Any],
    project_id: str,
    scope: str = 'project',
    parent_template_id: Optional[str] = None,
    is_entry: bool = True
) -> List[str]:
    """
    Migrate a single task template recursively.
    Returns list of child template IDs created.
    """
    metadata = template_data.get('metadata', {})
    task_def = template_data.get('task_definition', {})

    # Build main template task record
    template_task = {
        'template_id': template_id,
        'project_id': project_id if scope == 'project' else None,
        'machine_id': 'migration_script',
        'template_name': metadata.get('name', template_id),
        'description': metadata.get('description', ''),
        'category': metadata.get('category', 'general'),
        'scope': scope,
        'is_global': scope == 'global',
        'version': metadata.get('version', '1.0'),
        'is_entry_task': is_entry,
        'parent_template_id': parent_template_id,
        'title': task_def.get('title', ''),
        'task_description': task_def.get('description', ''),
        'priority': task_def.get('priority', 'medium'),
        'notes': task_def.get('notes', ''),
        'variables': metadata.get('variables', []),
        'child_template_ids': [],  # Will update after processing children
        'references_template_id': None,  # Not a reference
        'override_variables': {},
        'dependencies': task_def.get('dependencies', {'blocks': [], 'blocked_by': [], 'related': []}),
        'created_at': get_timestamp(),
        'updated_at': get_timestamp()
    }

    # Insert main record
    await insert_template_task(template_task)

    # Process subtasks
    child_ids = []
    subtasks = template_data.get('subtasks', [])
    for idx, subtask in enumerate(subtasks):
        if 'template_ref' in subtask:
            # Reference subtask
            child_id = f"{template_id}_ref_{idx}"
            ref_task = {
                'template_id': child_id,
                'project_id': project_id if scope == 'project' else None,
                'machine_id': 'migration_script',
                'template_name': f"Reference to {subtask['template_ref']}",
                'description': '',
                'category': metadata.get('category', 'general'),
                'scope': scope,
                'is_global': scope == 'global',
                'version': '1.0',
                'is_entry_task': False,
                'parent_template_id': template_id,
                'title': subtask.get('title', ''),  # Override title if provided
                'task_description': '',
                'priority': subtask.get('priority', 'medium'),
                'notes': '',
                'variables': [],
                'child_template_ids': [],
                'references_template_id': subtask['template_ref'],  # KEY: Points to referenced template
                'override_variables': subtask.get('variables', {}),  # Variable overrides
                'dependencies': {'blocks': [], 'blocked_by': [], 'related': []},
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
            await insert_template_task(ref_task)
            child_ids.append(child_id)
        else:
            # Inline subtask
            child_id = f"{template_id}_child_{idx}"
            child_template_data = {
                'metadata': {'category': metadata.get('category', 'general')},
                'task_definition': subtask,
                'subtasks': subtask.get('subtasks', [])  # Support nested subtasks
            }
            # Recursively migrate (may create more children)
            await migrate_task_template(
                child_id,
                child_template_data,
                project_id,
                scope,
                parent_template_id=template_id,
                is_entry=False
            )
            child_ids.append(child_id)

    # Update main record with child IDs
    if child_ids:
        try:
            client.table('template_tasks').update({
                'child_template_ids': child_ids
            }).eq('template_id', template_id).execute()
            print(f"  ✓ Updated {template_id} with {len(child_ids)} children")
        except Exception as e:
            print(f"  ✗ Error updating child_template_ids for {template_id}: {e}")

    return child_ids

async def migrate_sprint_template(
    template_id: str,
    template_data: Dict[str, Any],
    project_id: str,
    scope: str = 'project'
) -> None:
    """Migrate a single sprint template"""
    metadata = template_data.get('metadata', {})
    sprint_def = template_data.get('sprint_definition', {})

    # Build sprint template record
    template_sprint = {
        'template_id': template_id,
        'project_id': project_id if scope == 'project' else None,
        'machine_id': 'migration_script',
        'template_name': metadata.get('name', template_id),
        'description': metadata.get('description', ''),
        'category': 'sprint',
        'scope': scope,
        'is_global': scope == 'global',
        'version': metadata.get('version', '1.0'),
        'title': sprint_def.get('title', ''),
        'sprint_description': sprint_def.get('description', ''),
        'start_date': sprint_def.get('start_date'),
        'end_date': sprint_def.get('end_date'),
        'focus': sprint_def.get('focus', {}),
        'variables': metadata.get('variables', []),
        'task_ids': [],  # Will populate after creating task templates
        'created_at': get_timestamp(),
        'updated_at': get_timestamp()
    }

    # Collect all task IDs
    all_task_ids = []

    # Process planning tasks
    for task in template_data.get('planning_tasks', []):
        task_id = task.get('template_id', f"{template_id}_planning_{len(all_task_ids)}")

        if 'template_ref' in task:
            # Create reference task template
            ref_task = {
                'template_id': task_id,
                'project_id': project_id if scope == 'project' else None,
                'machine_id': 'migration_script',
                'template_name': f"Sprint task reference to {task['template_ref']}",
                'description': '',
                'category': metadata.get('category', 'sprint'),
                'scope': scope,
                'is_global': scope == 'global',
                'version': '1.0',
                'is_entry_task': True,  # Entry task for this sprint (not globally)
                'parent_template_id': None,
                'title': task.get('title', ''),
                'task_description': task.get('description', ''),
                'priority': task.get('priority', 'medium'),
                'notes': task.get('notes', ''),
                'variables': [],
                'child_template_ids': [],
                'references_template_id': task['template_ref'],
                'override_variables': task.get('variables', {}),
                'dependencies': task.get('dependencies', {'blocks': [], 'blocked_by': [], 'related': []}),
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
            await insert_template_task(ref_task)
        else:
            # Inline planning task
            inline_task_data = {
                'metadata': {'category': 'sprint'},
                'task_definition': task,
                'subtasks': []
            }
            await migrate_task_template(
                task_id,
                inline_task_data,
                project_id,
                scope,
                is_entry=True
            )

        all_task_ids.append(task_id)

    # Process milestone tasks
    for task in template_data.get('milestone_tasks', []):
        task_id = task.get('template_id', f"{template_id}_milestone_{len(all_task_ids)}")

        if 'template_ref' in task:
            # Create reference task template
            ref_task = {
                'template_id': task_id,
                'project_id': project_id if scope == 'project' else None,
                'machine_id': 'migration_script',
                'template_name': f"Sprint task reference to {task['template_ref']}",
                'description': '',
                'category': metadata.get('category', 'sprint'),
                'scope': scope,
                'is_global': scope == 'global',
                'version': '1.0',
                'is_entry_task': True,
                'parent_template_id': None,
                'title': task.get('title', ''),
                'task_description': task.get('description', ''),
                'priority': task.get('priority', 'high'),
                'notes': '',
                'variables': [],
                'child_template_ids': [],
                'references_template_id': task['template_ref'],
                'override_variables': task.get('variables', {}),
                'dependencies': {'blocks': [], 'blocked_by': [], 'related': []},
                'created_at': get_timestamp(),
                'updated_at': get_timestamp()
            }
            await insert_template_task(ref_task)
        else:
            # Inline milestone task
            inline_task_data = {
                'metadata': {'category': 'sprint'},
                'task_definition': task,
                'subtasks': []
            }
            await migrate_task_template(
                task_id,
                inline_task_data,
                project_id,
                scope,
                is_entry=True
            )

        all_task_ids.append(task_id)

    # Update sprint with all task IDs (mirrors sprints.task_ids)
    template_sprint['task_ids'] = all_task_ids

    # Insert sprint template
    await insert_template_sprint(template_sprint)

async def main():
    """Main migration function"""
    print("=" * 80)
    print("TEMPLATE NORMALIZATION MIGRATION")
    print("=" * 80)

    # Get project directory
    project_path = Path.cwd()
    print(f"\nProject: {project_path}")

    # Get or create project ID
    project_id = await get_project_id(str(project_path))
    if not project_id:
        print("✗ Failed to get project ID. Exiting.")
        return
    print(f"Project ID: {project_id}")

    # Load task templates
    task_templates_file = project_path / '.claude-tasks' / 'templates' / 'task_templates.json'
    if task_templates_file.exists():
        print(f"\n📄 Loading task templates from {task_templates_file}")
        with open(task_templates_file, 'r') as f:
            task_templates_data = json.load(f)

        templates = task_templates_data.get('templates', {})
        print(f"Found {len(templates)} task templates")

        for template_id, template_data in templates.items():
            print(f"\n→ Migrating task template: {template_id}")
            scope = template_data.get('metadata', {}).get('scope', 'project')
            await migrate_task_template(template_id, template_data, project_id, scope)
    else:
        print(f"\n⚠ Task templates file not found: {task_templates_file}")

    # Load sprint templates
    sprint_templates_file = project_path / '.claude-tasks' / 'templates' / 'sprint_templates.json'
    if sprint_templates_file.exists():
        print(f"\n📄 Loading sprint templates from {sprint_templates_file}")
        with open(sprint_templates_file, 'r') as f:
            sprint_templates_data = json.load(f)

        templates = sprint_templates_data.get('templates', {})
        print(f"Found {len(templates)} sprint templates")

        for template_id, template_data in templates.items():
            print(f"\n→ Migrating sprint template: {template_id}")
            scope = template_data.get('metadata', {}).get('scope', 'project')
            await migrate_sprint_template(template_id, template_data, project_id, scope)
    else:
        print(f"\n⚠ Sprint templates file not found: {sprint_templates_file}")

    # Validation
    print("\n" + "=" * 80)
    print("MIGRATION VALIDATION")
    print("=" * 80)

    # Count template_tasks
    result = client.table('template_tasks').select('*', count='exact').execute()
    task_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"\n✓ template_tasks: {task_count} records")

    # Count entry tasks
    result = client.table('template_tasks').select('*', count='exact').eq('is_entry_task', True).execute()
    entry_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"  - Entry tasks: {entry_count}")

    # Count nested tasks
    print(f"  - Nested tasks: {task_count - entry_count}")

    # Count template_sprints
    result = client.table('template_sprints').select('*', count='exact').execute()
    sprint_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"\n✓ template_sprints: {sprint_count} records")

    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Verify data in database")
    print("2. Test template retrieval with new tools")
    print("3. Test template instantiation")
    print("4. After validation, can optionally rename 'templates' table to 'templates_deprecated'")

if __name__ == '__main__':
    asyncio.run(main())
