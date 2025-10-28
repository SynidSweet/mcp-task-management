#!/usr/bin/env python3
"""
Data Integrity Checker for MCP Task Management System

Validates database integrity, Dual-ID consistency, and architecture compliance.
See docs/specifications/data-integrity-checker.md for full specification.
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.document_tools import get_supabase_client, get_or_create_project_id
from tools.specification_tools import resolve_specification_id, is_uuid_format
from core.machine_id import get_machine_id
from core.project_manager import ProjectManager


class IntegrityIssue:
    """Represents a single integrity issue."""

    def __init__(self, severity: str, category: str, entity_type: str,
                 entity_id: str, message: str, fix_suggestion: str = None):
        self.severity = severity  # CRITICAL, WARNING, INFO
        self.category = category  # dual_id, referential, architecture, consistency, schema
        self.entity_type = entity_type  # specifications, tasks, projects
        self.entity_id = entity_id
        self.message = message
        self.fix_suggestion = fix_suggestion
        self.timestamp = datetime.now().isoformat()


class IntegrityChecker:
    """Main integrity checker with all validation logic."""

    def __init__(self, project_path: str = None, verbose: bool = False):
        self.project_path = project_path or str(Path.cwd())
        self.verbose = verbose
        self.issues: List[IntegrityIssue] = []
        self.stats = {
            'specifications_checked': 0,
            'tasks_checked': 0,
            'sprints_checked': 0,
            'agents_checked': 0,
            'commands_checked': 0,
            'template_tasks_checked': 0,
            'template_sprints_checked': 0,
            'documentation_checked': 0,
            'projects_checked': 0,
            'specifications_validated_checked': 0,
            'requirements_validated_checked': 0,
            'constraints_validated_checked': 0,
            'critical_issues': 0,
            'warnings': 0,
            'info_issues': 0
        }

        # Get database connection
        self.client, error = get_supabase_client()
        if error:
            raise Exception(f"Database connection failed: {error}")

        # Get project context
        self.project_id, error = get_or_create_project_id(self.project_path)
        if error:
            raise Exception(f"Project setup failed: {error}")

        self.machine_id = get_machine_id()

    def add_issue(self, severity: str, category: str, entity_type: str,
                  entity_id: str, message: str, fix_suggestion: str = None):
        """Add an issue to the list."""
        issue = IntegrityIssue(severity, category, entity_type, entity_id, message, fix_suggestion)
        self.issues.append(issue)

        # Update stats
        if severity == 'CRITICAL':
            self.stats['critical_issues'] += 1
        elif severity == 'WARNING':
            self.stats['warnings'] += 1
        else:
            self.stats['info_issues'] += 1

    def check_dual_id_integrity(self, specifications: List[Dict[str, Any]]):
        """Validate Dual-ID system consistency for specifications."""
        if self.verbose:
            print("  Checking Dual-ID integrity...")

        for spec in specifications:
            spec_display_id = spec.get('display_id', 'UNKNOWN')
            parent_display_id = spec.get('parent_display_id')
            parent_id = spec.get('parent_id')

            # Check 1: Null parent_id with non-null parent_display_id
            if parent_display_id and not parent_id:
                self.add_issue(
                    'CRITICAL',
                    'dual_id',
                    'specifications',
                    spec_display_id,
                    f"parent_display_id='{parent_display_id}' but parent_id is NULL",
                    f"Run with --fix to auto-repair Dual-ID mismatches"
                )

            # Check 2: Non-null parent_id with null parent_display_id
            elif parent_id and not parent_display_id:
                self.add_issue(
                    'CRITICAL',
                    'dual_id',
                    'specifications',
                    spec_display_id,
                    f"parent_id='{parent_id}' but parent_display_id is NULL",
                    f"Manually set parent_display_id or clear parent_id"
                )

            # Check 3: Verify parent_id matches resolved parent_display_id
            elif parent_display_id and parent_id:
                expected_uuid, error = resolve_specification_id(
                    parent_display_id,
                    self.project_id,
                    self.machine_id
                )

                if error:
                    self.add_issue(
                        'WARNING',
                        'dual_id',
                        'specifications',
                        spec_display_id,
                        f"Cannot resolve parent_display_id '{parent_display_id}': {error}",
                        f"Verify parent exists or update parent_display_id"
                    )
                elif expected_uuid != parent_id:
                    self.add_issue(
                        'CRITICAL',
                        'dual_id',
                        'specifications',
                        spec_display_id,
                        f"parent_id mismatch: stored='{parent_id}', expected='{expected_uuid}'",
                        f"Run with --fix to sync parent_id with parent_display_id"
                    )

            # Check 4: Missing display_id
            if not spec.get('display_id'):
                self.add_issue(
                    'CRITICAL',
                    'dual_id',
                    'specifications',
                    spec.get('id', 'UNKNOWN'),
                    "Missing display_id field",
                    "Manually add display_id to this specification"
                )

    def check_referential_integrity(self, specifications: List[Dict[str, Any]]):
        """Validate FK relationships and prevent orphaned references."""
        if self.verbose:
            print("  Checking referential integrity...")

        # Build ID maps for quick lookups
        spec_uuids = {spec['id'] for spec in specifications}
        spec_display_ids = {spec['display_id'] for spec in specifications if spec.get('display_id')}

        for spec in specifications:
            spec_display_id = spec.get('display_id', 'UNKNOWN')
            parent_id = spec.get('parent_id')
            parent_display_id = spec.get('parent_display_id')

            # Check 1: Orphaned parent_id UUID
            if parent_id and parent_id not in spec_uuids:
                self.add_issue(
                    'CRITICAL',
                    'referential',
                    'specifications',
                    spec_display_id,
                    f"parent_id '{parent_id}' points to non-existent specification",
                    f"Update parent_id to existing specification or set to NULL"
                )

            # Check 2: Orphaned parent_display_id
            if parent_display_id and parent_display_id not in spec_display_ids:
                self.add_issue(
                    'CRITICAL',
                    'referential',
                    'specifications',
                    spec_display_id,
                    f"parent_display_id '{parent_display_id}' points to non-existent specification",
                    f"Update parent_display_id to existing specification or set to NULL"
                )

        # Check 3: Detect circular references
        self._check_circular_references(specifications)

    def _check_circular_references(self, specifications: List[Dict[str, Any]]):
        """Detect circular parent-child relationships."""
        # Build parent map
        parent_map = {}
        for spec in specifications:
            if spec.get('parent_id'):
                parent_map[spec['id']] = spec['parent_id']

        # Check each specification for cycles
        for spec in specifications:
            visited = set()
            current = spec['id']
            path = [spec.get('display_id', spec['id'])]

            while current in parent_map:
                parent = parent_map[current]

                if parent in visited:
                    # Found cycle
                    cycle_spec = next((s for s in specifications if s['id'] == current), None)
                    self.add_issue(
                        'CRITICAL',
                        'referential',
                        'specifications',
                        spec.get('display_id', 'UNKNOWN'),
                        f"Circular reference detected in path: {' → '.join(path)}",
                        f"Break the cycle by updating parent_id for one of the specifications"
                    )
                    break

                visited.add(current)
                current = parent

                # Add to path for better error messages
                parent_spec = next((s for s in specifications if s['id'] == parent), None)
                if parent_spec:
                    path.append(parent_spec.get('display_id', parent))

    def _check_task_circular_references(self, tasks: List[Dict[str, Any]]):
        """Detect circular parent-child relationships in tasks."""
        # Build parent map
        parent_map = {}
        for task in tasks:
            if task.get('parent_task_id'):
                parent_map[task['id']] = task['parent_task_id']

        # Check each task for cycles
        for task in tasks:
            visited = set()
            current = task['id']
            path = [task.get('id')]

            while current in parent_map:
                parent = parent_map[current]

                if parent in visited:
                    # Found cycle
                    self.add_issue(
                        'CRITICAL',
                        'architecture',
                        'tasks',
                        task.get('id', 'UNKNOWN'),
                        f"Circular reference detected in task hierarchy: {' → '.join(path)}",
                        f"Break the cycle by updating parent_task_id for one of the tasks"
                    )
                    break

                visited.add(current)
                current = parent

                # Add to path for better error messages
                parent_task = next((t for t in tasks if t['id'] == parent), None)
                if parent_task:
                    path.append(parent_task.get('id'))

    def check_sprint_task_relationships(self, tasks: List[Dict[str, Any]], sprints: List[Dict[str, Any]]):
        """Validate sprint-task relationship integrity."""
        if self.verbose:
            print("  Checking sprint-task relationships...")

        task_ids = {t["id"] for t in tasks}
        sprint_ids = {s["id"] for s in sprints}

        # Check 1: Validate task.sprint_id references existing sprint
        for task in tasks:
            sprint_id = task.get('sprint_id')
            if sprint_id and sprint_id not in sprint_ids:
                self.add_issue(
                    'CRITICAL',
                    'referential',
                    'tasks',
                    task.get('id', 'UNKNOWN'),
                    f"sprint_id '{sprint_id}' references non-existent sprint",
                    f"Update sprint_id to existing sprint or set to NULL"
                )

        # Check 2: Validate sprint.task_ids array elements exist
        for sprint in sprints:
            task_id_list = sprint.get('task_ids', [])
            if task_id_list:
                for task_id in task_id_list:
                    if task_id not in task_ids:
                        self.add_issue(
                            'WARNING',
                            'referential',
                            'sprints',
                            sprint.get('id', 'UNKNOWN'),
                            f"task_ids contains non-existent task '{task_id}'",
                            f"Remove '{task_id}' from task_ids array"
                        )

        # Check 3: Validate reciprocal relationships (task.sprint_id ↔ sprint.task_ids)
        for task in tasks:
            task_id = task.get('id')
            sprint_id = task.get('sprint_id')

            if sprint_id:
                # Find the sprint
                sprint = next((s for s in sprints if s['id'] == sprint_id), None)
                if sprint:
                    task_id_list = sprint.get('task_ids', [])
                    if task_id not in task_id_list:
                        self.add_issue(
                            'WARNING',
                            'consistency',
                            'tasks',
                            task_id,
                            f"Task assigned to sprint '{sprint_id}' but not in sprint's task_ids array",
                            f"Add '{task_id}' to sprint.task_ids or clear task.sprint_id"
                        )

        # Check 4: Reverse check - tasks in sprint.task_ids should have sprint_id set
        for sprint in sprints:
            sprint_id = sprint.get('id')
            task_id_list = sprint.get('task_ids', [])

            for task_id in task_id_list:
                task = next((t for t in tasks if t['id'] == task_id), None)
                if task and task.get('sprint_id') != sprint_id:
                    self.add_issue(
                        'WARNING',
                        'consistency',
                        'sprints',
                        sprint_id,
                        f"Sprint contains task '{task_id}' but task.sprint_id is '{task.get('sprint_id')}' (should be '{sprint_id}')",
                        f"Update task.sprint_id to '{sprint_id}' or remove from sprint.task_ids"
                    )

    def check_sprint_data_quality(self, sprints: List[Dict[str, Any]]):
        """Validate sprint-specific data quality."""
        if self.verbose:
            print("  Checking sprint data quality...")

        for sprint in sprints:
            sprint_id = sprint.get('id', 'UNKNOWN')

            # Check date consistency
            start_date = sprint.get('start_date')
            end_date = sprint.get('end_date')

            if start_date and end_date:
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(str(start_date))
                    end = datetime.fromisoformat(str(end_date))

                    if end <= start:
                        self.add_issue(
                            'WARNING',
                            'consistency',
                            'sprints',
                            sprint_id,
                            f"end_date ({end_date}) is not after start_date ({start_date})",
                            f"Adjust sprint dates so end_date > start_date"
                        )
                except Exception as e:
                    self.add_issue(
                        'WARNING',
                        'consistency',
                        'sprints',
                        sprint_id,
                        f"Invalid date format: {e}",
                        f"Use ISO date format (YYYY-MM-DD)"
                    )

    def check_global_resources_basic(self,
                              commands: List[Dict[str, Any]],
                              agents: List[Dict[str, Any]],
                              documentation: List[Dict[str, Any]]):
        """Validate global resource tables (commands, agents, documentation)."""
        if self.verbose:
            print("  Checking global resources...")

        # Validate commands
        for command in commands:
            cmd_id = command.get('id', 'UNKNOWN')

            # Required fields
            if not command.get('command_name'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'commands',
                    cmd_id,
                    "Missing required field: command_name",
                    "Set command_name"
                )

            if not command.get('content'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'commands',
                    cmd_id,
                    "Missing command content",
                    "Add markdown content for command"
                )

        # Validate agents
        for agent in agents:
            agent_id = agent.get('id', 'UNKNOWN')

            # Required fields
            if not agent.get('agent_name'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'agents',
                    agent_id,
                    "Missing required field: agent_name",
                    "Set agent_name"
                )

            if not agent.get('content'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'agents',
                    agent_id,
                    "Missing agent content",
                    "Add markdown content for agent"
                )

            # Validate tools_config is valid JSON
            tools_config = agent.get('tools_config')
            if tools_config and not isinstance(tools_config, dict):
                self.add_issue(
                    'WARNING',
                    'schema',
                    'agents',
                    agent_id,
                    f"tools_config must be JSONB dict, found: {type(tools_config).__name__}",
                    "Convert tools_config to valid JSON object"
                )

        # Validate documentation
        for doc in documentation:
            doc_id = doc.get('id', 'UNKNOWN')

            # Required fields
            if not doc.get('doc_title'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'documentation',
                    doc_id,
                    "Missing doc_title",
                    "Set doc_title from file or header"
                )

            if not doc.get('file_path'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'documentation',
                    doc_id,
                    "Missing required field: file_path",
                    "Set file_path for document"
                )

    def check_template_tables(self, template_tasks: List[Dict[str, Any]],
                             template_sprints: List[Dict[str, Any]]):
        """
        Validate normalized template tables (template_tasks, template_sprints).

        Checks:
        - Required fields present
        - Scope consistency
        - Template composition (references_template_id exists)
        - Hierarchy integrity (parent-child relationships)
        - Sprint task references exist
        - No circular references
        """
        if self.verbose:
            print("  Checking template tables...")

        # Build template_id index for reference validation
        template_ids = {t['template_id'] for t in template_tasks}

        # Validate template_tasks
        for template in template_tasks:
            template_id = template.get('template_id', 'UNKNOWN')

            # Required fields
            if not template.get('template_name'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'template_tasks',
                    template_id,
                    "Missing required field: template_name",
                    "Set template_name"
                )

            if not template.get('title'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'template_tasks',
                    template_id,
                    "Missing required field: title",
                    "Set title"
                )

            # Scope consistency
            scope = template.get('scope')
            is_global = template.get('is_global')
            if scope and is_global is not None:
                if (scope == 'global' and not is_global) or (scope == 'project' and is_global):
                    self.add_issue(
                        'WARNING',
                        'consistency',
                        'template_tasks',
                        template_id,
                        f"scope='{scope}' but is_global={is_global} (inconsistent)",
                        f"Set is_global={scope == 'global'}"
                    )

            # Validate template composition (references)
            if template.get('references_template_id'):
                ref_template_id = template['references_template_id']
                if ref_template_id not in template_ids:
                    self.add_issue(
                        'CRITICAL',
                        'referential',
                        'template_tasks',
                        template_id,
                        f"References non-existent template: {ref_template_id}",
                        f"Create template '{ref_template_id}' or remove reference"
                    )

            # Validate hierarchy (parent-child)
            if template.get('parent_template_id'):
                parent_id = template['parent_template_id']
                if parent_id not in template_ids:
                    self.add_issue(
                        'CRITICAL',
                        'referential',
                        'template_tasks',
                        template_id,
                        f"Parent template not found: {parent_id}",
                        f"Create parent template or set parent_template_id to null"
                    )

            # Validate children exist
            for child_id in template.get('child_template_ids', []):
                if child_id not in template_ids:
                    self.add_issue(
                        'CRITICAL',
                        'referential',
                        'template_tasks',
                        template_id,
                        f"Child template not found: {child_id}",
                        f"Create child template or remove from child_template_ids"
                    )

        # Validate template_sprints
        for sprint in template_sprints:
            sprint_id = sprint.get('template_id', 'UNKNOWN')

            # Required fields
            if not sprint.get('template_name'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'template_sprints',
                    sprint_id,
                    "Missing required field: template_name",
                    "Set template_name"
                )

            if not sprint.get('title'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'template_sprints',
                    sprint_id,
                    "Missing required field: title",
                    "Set title"
                )

            # Validate task references (mirrors sprints.task_ids)
            for task_id in sprint.get('task_ids', []):
                if task_id not in template_ids:
                    self.add_issue(
                        'CRITICAL',
                        'referential',
                        'template_sprints',
                        sprint_id,
                        f"Task template not found: {task_id}",
                        f"Create template task '{task_id}' or remove from task_ids"
                    )

        # Check for circular references in template composition
        self._check_template_circular_references(template_tasks)

    def _check_template_circular_references(self, template_tasks: List[Dict[str, Any]]):
        """Check for circular references in template composition using DFS."""
        if self.verbose:
            print("    Checking for circular template references...")

        # Build reference graph
        ref_graph = {}
        for template in template_tasks:
            template_id = template.get('template_id')
            refs = []
            if template.get('references_template_id'):
                refs.append(template['references_template_id'])
            for child_id in template.get('child_template_ids', []):
                refs.append(child_id)
            ref_graph[template_id] = refs

        # DFS to detect cycles
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in ref_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Check each template
        for template_id in ref_graph:
            visited = set()
            rec_stack = set()
            if has_cycle(template_id, visited, rec_stack):
                self.add_issue(
                    'CRITICAL',
                    'referential',
                    'template_tasks',
                    template_id,
                    "Circular reference detected in template composition",
                    "Break the circular reference chain"
                )

    def check_template_references(self):
        """
        DEPRECATED: This method checked file-based templates.
        Now using check_template_tables() for normalized database templates.
        Keeping for backward compatibility but does nothing.
        """
        if self.verbose:
            print("  Template reference check skipped (using normalized tables)")
        return

        # Load all templates from file system (source of truth)
        template_files = [
            Path.home() / ".claude" / ".claude-tasks" / "templates" / "task_templates.json",
            Path(self.project_path) / ".claude-tasks" / "templates" / "task_templates.json",
            Path.home() / ".claude" / ".claude-tasks" / "templates" / "sprint_templates.json",
            Path(self.project_path) / ".claude-tasks" / "templates" / "sprint_templates.json"
        ]

        all_templates = {}
        for template_file in template_files:
            if template_file.exists():
                try:
                    with open(template_file) as f:
                        data = json.load(f)
                        templates_collection = data.get("templates", {})
                        all_templates.update(templates_collection)
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Failed to load {template_file}: {e}")

        if not all_templates:
            if self.verbose:
                print("    No templates found to check")
            return

        # Build dependency graph: template_id -> [referenced_template_ids]
        dependency_graph = {}
        for template_id, template_data in all_templates.items():
            # Collect all tasks in template
            tasks = []
            tasks.extend(template_data.get("subtasks", []))
            tasks.extend(template_data.get("planning_tasks", []))
            tasks.extend(template_data.get("milestone_tasks", []))

            # Extract template references
            refs = []
            for task in tasks:
                if "template_ref" in task:
                    ref_name = task["template_ref"]
                    refs.append(ref_name)

                    # Check if referenced template exists
                    if ref_name not in all_templates:
                        self.add_issue(
                            'CRITICAL',
                            'template_references',
                            'templates',
                            template_id,
                            f"References non-existent template '{ref_name}'",
                            f"Create template '{ref_name}' or remove reference"
                        )

            dependency_graph[template_id] = refs

        # Detect circular references using DFS
        def find_cycle_dfs(node, visited, rec_stack, path):
            """DFS to detect cycles in dependency graph."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Visit all dependencies
            for neighbor in dependency_graph.get(node, []):
                if neighbor not in all_templates:
                    continue  # Skip non-existent templates (already reported above)

                if neighbor not in visited:
                    # Recursive DFS
                    cycle = find_cycle_dfs(neighbor, visited, rec_stack, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found a cycle!
                    cycle_start_idx = path.index(neighbor)
                    return path[cycle_start_idx:] + [neighbor]

            # Backtrack
            path.pop()
            rec_stack.remove(node)
            return None

        # Check each template for cycles
        visited = set()
        for template_id in dependency_graph:
            if template_id not in visited:
                cycle = find_cycle_dfs(template_id, visited, set(), [])
                if cycle:
                    cycle_path = " → ".join(cycle)
                    self.add_issue(
                        'CRITICAL',
                        'template_references',
                        'templates',
                        template_id,
                        f"Circular reference detected: {cycle_path}",
                        f"Break the cycle by removing one of the template references in the chain"
                    )

    def check_architecture_compliance(self, tasks: List[Dict[str, Any]],
                                     specifications: List[Dict[str, Any]]):
        """Validate architecture-specific rules (tasks hierarchical, specs hierarchical)."""
        if self.verbose:
            print("  Checking architecture compliance...")

        # Check 1: Task hierarchy integrity
        task_ids = {t["id"] for t in tasks}
        for task in tasks:
            parent_id = task.get('parent_task_id')

            # Validate parent_task_id references exist
            if parent_id and parent_id not in task_ids:
                self.add_issue(
                    'CRITICAL',
                    'architecture',
                    'tasks',
                    task.get('id', 'UNKNOWN'),
                    f"parent_task_id '{parent_id}' references non-existent task",
                    f"Update parent_task_id to existing task or set to NULL"
                )

            # Validate child_task_ids array consistency
            child_ids = task.get('child_task_ids', [])
            if child_ids:
                for child_id in child_ids:
                    # Check child exists
                    child_task = next((t for t in tasks if t["id"] == child_id), None)
                    if not child_task:
                        self.add_issue(
                            'WARNING',
                            'architecture',
                            'tasks',
                            task.get('id', 'UNKNOWN'),
                            f"child_task_ids contains non-existent task '{child_id}'",
                            f"Remove '{child_id}' from child_task_ids array"
                        )
                    elif child_task.get('parent_task_id') != task["id"]:
                        self.add_issue(
                            'WARNING',
                            'architecture',
                            'tasks',
                            task.get('id', 'UNKNOWN'),
                            f"Inconsistency: child '{child_id}' doesn't reference this task as parent",
                            f"Update child's parent_task_id to '{task['id']}' or remove from child_task_ids"
                        )

        # Check 2: Detect circular references in task hierarchy
        self._check_task_circular_references(tasks)

        # Check 3: Validate task dependencies structure
        for task in tasks:
            deps = task.get('dependencies')
            if deps is not None:
                if not isinstance(deps, dict):
                    self.add_issue(
                        'WARNING',
                        'architecture',
                        'tasks',
                        task.get('id', 'UNKNOWN'),
                        f"dependencies must be JSONB dict, found: {type(deps).__name__}",
                        "Convert to {'blocks': [], 'blocked_by': [], 'related': []}"
                    )
                else:
                    # Validate required keys
                    required_keys = {'blocks', 'blocked_by', 'related'}
                    missing_keys = required_keys - set(deps.keys())
                    if missing_keys:
                        self.add_issue(
                            'WARNING',
                            'architecture',
                            'tasks',
                            task.get('id', 'UNKNOWN'),
                            f"dependencies missing keys: {missing_keys}",
                            f"Add missing keys: {missing_keys}"
                        )

                    # Check 4: Validate dependency references exist (orphaned dependencies)
                    for dep_type in ['blocks', 'blocked_by', 'related']:
                        dep_list = deps.get(dep_type, [])
                        if isinstance(dep_list, list):
                            for dep_id in dep_list:
                                if dep_id not in task_ids:
                                    self.add_issue(
                                        'WARNING',
                                        'architecture',
                                        'tasks',
                                        task.get('id', 'UNKNOWN'),
                                        f"dependencies.{dep_type} contains non-existent task '{dep_id}'",
                                        f"Remove '{dep_id}' from {dep_type} or create the referenced task"
                                    )

        # Check 3: Specifications should have hierarchy fields
        for spec in specifications:
            # These are optional but should be consistent if used
            if spec.get('parent_display_id') and not spec.get('parent_id'):
                # Already caught by dual_id checks, skip here
                pass

    def check_uniqueness(self, specifications: List[Dict[str, Any]], tasks: List[Dict[str, Any]]):
        """Validate uniqueness constraints."""
        if self.verbose:
            print("  Checking uniqueness constraints...")

        # Check display_id uniqueness within project/machine scope (specifications)
        display_id_map = {}
        for spec in specifications:
            display_id = spec.get('display_id')
            if display_id:
                key = (display_id, spec.get('project_id'), spec.get('machine_id'))
                if key not in display_id_map:
                    display_id_map[key] = []
                display_id_map[key].append(spec)

        # Report duplicates
        for (display_id, project_id, machine_id), specs in display_id_map.items():
            if len(specs) > 1:
                spec_ids = ', '.join([s.get('display_id', s.get('id', 'UNKNOWN')) for s in specs])
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'specifications',
                    display_id,
                    f"Duplicate display_id found {len(specs)} times: {spec_ids}",
                    f"Rename duplicates to unique display_ids"
                )

        # Check task ID uniqueness within project/machine scope
        task_id_map = {}
        for task in tasks:
            task_id = task.get('id')
            if task_id:
                key = (task_id, task.get('project_id'), task.get('machine_id'))
                if key not in task_id_map:
                    task_id_map[key] = []
                task_id_map[key].append(task)

        # Report duplicate task IDs
        for (task_id, project_id, machine_id), task_list in task_id_map.items():
            if len(task_list) > 1:
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'tasks',
                    task_id,
                    f"Duplicate task ID found {len(task_list)} times",
                    f"Task IDs must be unique - fix ID generation or remove duplicates"
                )

    def check_required_fields(self, specifications: List[Dict[str, Any]],
                             tasks: List[Dict[str, Any]]):
        """Validate required fields and field values."""
        if self.verbose:
            print("  Checking required fields and values...")

        # Valid values
        VALID_STATUSES = {'pending', 'in_progress', 'completed', 'blocked'}
        VALID_PRIORITIES = {'low', 'medium', 'high', 'critical'}

        # Specifications required fields
        for spec in specifications:
            if not spec.get('display_id'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'specifications',
                    spec.get('id', 'UNKNOWN'),
                    "Missing required field: display_id",
                    "Add display_id to specification"
                )
            if not spec.get('specification_name'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'specifications',
                    spec.get('display_id', 'UNKNOWN'),
                    "Missing required field: specification_name",
                    "Add specification_name to specification"
                )
            if not spec.get('specification_type'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'specifications',
                    spec.get('display_id', 'UNKNOWN'),
                    "Missing required field: specification_type",
                    "Add specification_type to specification"
                )

        # Tasks required fields
        for task in tasks:
            task_id = task.get('id', 'UNKNOWN')

            # Required: id
            if not task.get('id'):
                self.add_issue(
                    'CRITICAL',
                    'consistency',
                    'tasks',
                    'UNKNOWN',
                    "Missing required field: id",
                    "Task must have an ID"
                )

            # Required: title
            if not task.get('title'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'tasks',
                    task_id,
                    "Missing required field: title",
                    "Add title to task"
                )

            # Required: status
            if not task.get('status'):
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'tasks',
                    task_id,
                    "Missing required field: status",
                    "Set status (pending, in_progress, completed, blocked)"
                )
            elif task.get('status') not in VALID_STATUSES:
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'tasks',
                    task_id,
                    f"Invalid status value: '{task.get('status')}' (must be one of: {', '.join(VALID_STATUSES)})",
                    f"Set status to one of: {', '.join(VALID_STATUSES)}"
                )

            # Priority validation
            if task.get('priority') and task.get('priority') not in VALID_PRIORITIES:
                self.add_issue(
                    'WARNING',
                    'consistency',
                    'tasks',
                    task_id,
                    f"Invalid priority value: '{task.get('priority')}' (must be one of: {', '.join(VALID_PRIORITIES)})",
                    f"Set priority to one of: {', '.join(VALID_PRIORITIES)}"
                )

            # Task ID format validation
            if task.get('id'):
                import re
                if not re.match(r'^TASK-\d{4}-\d{3,}$', task.get('id')):
                    self.add_issue(
                        'INFO',
                        'schema',
                        'tasks',
                        task_id,
                        f"Task ID doesn't match expected format 'TASK-YYYY-NNN': '{task.get('id')}'",
                        "Consider using standard format for consistency"
                    )

    def check_schema_compliance(self, specifications: List[Dict[str, Any]]):
        """Check for deprecated or unused fields."""
        if self.verbose:
            print("  Checking schema compliance...")

        for spec in specifications:
            # Check for deprecated specification_path field
            if 'specification_path' in spec and spec['specification_path']:
                self.add_issue(
                    'INFO',
                    'schema',
                    'specifications',
                    spec.get('display_id', 'UNKNOWN'),
                    "Uses deprecated field 'specification_path' (no longer stored)",
                    "Field will be ignored - path is calculated on-demand"
                )

    def check_validation_tables_integrity(self,
                                         specifications: List[Dict[str, Any]],
                                         validated_specs: List[Dict[str, Any]],
                                         validated_requirements: List[Dict[str, Any]],
                                         validated_constraints: List[Dict[str, Any]]):
        """Validate validation tables (specifications_validated, etc.) integrity."""
        if self.verbose:
            print("  Checking validation tables integrity...")

        # Build lookup maps
        spec_ids = {s['id'] for s in specifications}
        validated_spec_ids = {v['id'] for v in validated_specs}

        # Check 1: Orphaned validated specifications (validated but no current spec)
        for validated_spec in validated_specs:
            validated_id = validated_spec.get('id')
            if validated_id not in spec_ids:
                self.add_issue(
                    'WARNING',
                    'referential',
                    'specifications_validated',
                    validated_id,
                    "Validated specification has no matching current specification",
                    "This may indicate the specification was deleted without cleanup"
                )

        # Check 2: Validated requirements reference existing validated specs
        for req in validated_requirements:
            spec_id = req.get('specification_id')
            if spec_id and spec_id not in validated_spec_ids:
                self.add_issue(
                    'CRITICAL',
                    'referential',
                    'specification_requirements_validated',
                    req.get('id', 'UNKNOWN'),
                    f"References non-existent validated specification '{spec_id}'",
                    f"Delete this requirement or update specification_id to valid validated spec"
                )

        # Check 3: Validated constraints reference existing validated specs
        for const in validated_constraints:
            spec_id = const.get('specification_id')
            if spec_id and spec_id not in validated_spec_ids:
                self.add_issue(
                    'CRITICAL',
                    'referential',
                    'specification_constraints_validated',
                    const.get('id', 'UNKNOWN'),
                    f"References non-existent validated specification '{spec_id}'",
                    f"Delete this constraint or update specification_id to valid validated spec"
                )

        # Check 4: Validated specs should have validated_at timestamp
        for validated_spec in validated_specs:
            if not validated_spec.get('validated_at'):
                self.add_issue(
                    'WARNING',
                    'schema',
                    'specifications_validated',
                    validated_spec.get('id', 'UNKNOWN'),
                    "Missing validated_at timestamp",
                    "Set validated_at to the validation timestamp"
                )

        # Check 5: Validated specs should match schema of current specs
        required_fields = {'id', 'project_id', 'machine_id', 'specification_name',
                          'specification_type', 'display_id'}
        for validated_spec in validated_specs:
            missing_fields = required_fields - set(validated_spec.keys())
            if missing_fields:
                self.add_issue(
                    'CRITICAL',
                    'schema',
                    'specifications_validated',
                    validated_spec.get('id', 'UNKNOWN'),
                    f"Missing required fields: {missing_fields}",
                    f"Add missing fields: {missing_fields}"
                )

    def run_checks(self, table: str = None) -> Dict[str, Any]:
        """Run all integrity checks."""
        print(f"\n{'='*60}")
        print(f"  DATA INTEGRITY CHECK - MCP Task Management System")
        print(f"{'='*60}\n")
        print(f"Project: {self.project_path}")
        print(f"Database: Connected")
        print(f"Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Load data from database
        specifications = []
        tasks = []
        sprints = []
        agents = []
        commands = []
        template_tasks = []
        template_sprints = []
        documentation = []
        validated_specs = []
        validated_requirements = []
        validated_constraints = []

        if not table or table == 'specifications':
            print("Loading specifications...")
            result = self.client.table('specifications').select('*').eq('project_id', self.project_id).eq('machine_id', self.machine_id).execute()
            specifications = result.data or []
            self.stats['specifications_checked'] = len(specifications)

            # Load validated tables
            print("Loading validated specifications...")
            try:
                result = self.client.table('specifications_validated').select('*').eq('project_id', self.project_id).eq('machine_id', self.machine_id).execute()
                validated_specs = result.data or []
                self.stats['specifications_validated_checked'] = len(validated_specs)
            except Exception as e:
                print(f"  Note: specifications_validated table not found (may not exist yet): {e}")

            try:
                result = self.client.table('specification_requirements_validated').select('*').execute()
                validated_requirements = result.data or []
                self.stats['requirements_validated_checked'] = len(validated_requirements)
            except Exception as e:
                print(f"  Note: specification_requirements_validated table not found (may not exist yet): {e}")

            try:
                result = self.client.table('specification_constraints_validated').select('*').execute()
                validated_constraints = result.data or []
                self.stats['constraints_validated_checked'] = len(validated_constraints)
            except Exception as e:
                print(f"  Note: specification_constraints_validated table not found (may not exist yet): {e}")

        if not table or table == 'tasks':
            print("Loading tasks...")
            result = self.client.table('tasks').select('*').eq('project_id', self.project_id).eq('machine_id', self.machine_id).execute()
            tasks = result.data or []
            self.stats['tasks_checked'] = len(tasks)

        if not table or table == 'sprints':
            print("Loading sprints...")
            result = self.client.table('sprints').select('*').eq('project_id', self.project_id).eq('machine_id', self.machine_id).execute()
            sprints = result.data or []
            self.stats['sprints_checked'] = len(sprints)

        # Load global resources (no table filter - always check if present)
        if not table:
            print("Loading global resources...")
            try:
                result = self.client.table('agents').select('*').execute()
                agents = result.data or []
                self.stats['agents_checked'] = len(agents)
            except:
                pass

            try:
                result = self.client.table('commands').select('*').execute()
                commands = result.data or []
                self.stats['commands_checked'] = len(commands)
            except:
                pass

            try:
                result = self.client.table('template_tasks').select('*').execute()
                template_tasks = result.data or []
                self.stats['template_tasks_checked'] = len(template_tasks)
            except Exception as e:
                if self.verbose:
                    print(f"  Note: template_tasks table not found: {e}")

            try:
                result = self.client.table('template_sprints').select('*').execute()
                template_sprints = result.data or []
                self.stats['template_sprints_checked'] = len(template_sprints)
            except Exception as e:
                if self.verbose:
                    print(f"  Note: template_sprints table not found: {e}")

            try:
                result = self.client.table('documentation').select('*').execute()
                documentation = result.data or []
                self.stats['documentation_checked'] = len(documentation)
            except:
                pass

        print()

        # Run validation checks
        if specifications:
            self.check_dual_id_integrity(specifications)
            self.check_referential_integrity(specifications)
            self.check_schema_compliance(specifications)

        # Check validation tables if present
        if validated_specs or validated_requirements or validated_constraints:
            self.check_validation_tables_integrity(
                specifications, validated_specs,
                validated_requirements, validated_constraints
            )

        if sprints:
            self.check_sprint_data_quality(sprints)

        if tasks and sprints:
            self.check_sprint_task_relationships(tasks, sprints)

        if commands or agents or documentation:
            self.check_global_resources_basic(commands, agents, documentation)

        # Check template tables (normalized schema)
        if template_tasks or template_sprints:
            self.check_template_tables(template_tasks, template_sprints)

        if specifications or tasks:
            self.check_uniqueness(specifications, tasks)
            self.check_architecture_compliance(tasks, specifications)
            self.check_required_fields(specifications, tasks)

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate formatted integrity report."""
        print(f"{'='*60}")
        print(f"\n📊 SUMMARY")
        print(f"  ✓ Specifications checked: {self.stats['specifications_checked']}")

        # Show validated tables if any were checked
        validated_count = (self.stats['specifications_validated_checked'] +
                          self.stats['requirements_validated_checked'] +
                          self.stats['constraints_validated_checked'])
        if validated_count > 0:
            print(f"  ✓ Validated specs: {self.stats['specifications_validated_checked']} specs, "
                  f"{self.stats['requirements_validated_checked']} requirements, "
                  f"{self.stats['constraints_validated_checked']} constraints")

        print(f"  ✓ Tasks checked: {self.stats['tasks_checked']}")
        print(f"  ✓ Sprints checked: {self.stats['sprints_checked']}")

        # Show global resources if any were checked
        global_count = (self.stats['agents_checked'] + self.stats['commands_checked'] +
                       self.stats['template_tasks_checked'] + self.stats['template_sprints_checked'] +
                       self.stats['documentation_checked'])
        if global_count > 0:
            print(f"  ✓ Global resources: {self.stats['agents_checked']} agents, "
                  f"{self.stats['commands_checked']} commands, "
                  f"{self.stats['template_tasks_checked']} template_tasks, "
                  f"{self.stats['template_sprints_checked']} template_sprints, "
                  f"{self.stats['documentation_checked']} docs")
        total_issues = self.stats['critical_issues'] + self.stats['warnings'] + self.stats['info_issues']

        if total_issues == 0:
            print(f"  ✓ No issues found - All checks passed!")
        else:
            print(f"  ⚠  Issues found: {total_issues} ({self.stats['critical_issues']} critical, {self.stats['warnings']} warnings, {self.stats['info_issues']} info)")

        print(f"\n{'='*60}\n")

        # Group issues by severity
        critical_issues = [i for i in self.issues if i.severity == 'CRITICAL']
        warnings = [i for i in self.issues if i.severity == 'WARNING']
        info_issues = [i for i in self.issues if i.severity == 'INFO']

        # Display critical issues
        if critical_issues:
            print("🔴 CRITICAL ISSUES\n")
            for idx, issue in enumerate(critical_issues, 1):
                print(f"[{idx}] {issue.category.upper()} - {issue.entity_type.title()}: \"{issue.entity_id}\"")
                print(f"    {issue.message}")
                if issue.fix_suggestion:
                    print(f"    Fix: {issue.fix_suggestion}")
                print()

        # Display warnings
        if warnings:
            print(f"{'='*60}\n")
            print("⚠️  WARNINGS\n")
            for idx, issue in enumerate(warnings, 1):
                print(f"[{idx}] {issue.category.upper()} - {issue.entity_type.title()}: \"{issue.entity_id}\"")
                print(f"    {issue.message}")
                if issue.fix_suggestion:
                    print(f"    Fix: {issue.fix_suggestion}")
                print()

        # Display info issues
        if info_issues:
            print(f"{'='*60}\n")
            print("ℹ️  INFORMATION\n")
            for idx, issue in enumerate(info_issues, 1):
                print(f"[{idx}] {issue.category.upper()} - {issue.entity_type.title()}: \"{issue.entity_id}\"")
                print(f"    {issue.message}")
                if issue.fix_suggestion:
                    print(f"    Note: {issue.fix_suggestion}")
                print()

        # Recommendations
        if total_issues > 0:
            print(f"{'='*60}\n")
            print("💡 RECOMMENDATIONS\n")
            if critical_issues:
                print("  • Fix critical issues immediately - they may cause system failures")
            if any(i.category == 'dual_id' for i in critical_issues):
                print("  • Run with --fix to auto-repair Dual-ID mismatches")
            if warnings:
                print("  • Review warnings - they indicate potential problems")
            print("  • Consider running check after every schema migration")
            print(f"\nRun 'python check_data_integrity.py --help' for options\n")

        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'issues': [
                {
                    'severity': i.severity,
                    'category': i.category,
                    'entity_type': i.entity_type,
                    'entity_id': i.entity_id,
                    'message': i.message,
                    'fix_suggestion': i.fix_suggestion
                }
                for i in self.issues
            ]
        }

    def auto_repair(self) -> int:
        """Auto-repair safe issues. Returns number of fixes applied."""
        print("\n🔧 AUTO-REPAIR MODE\n")
        fixes_applied = 0

        # Only fix Dual-ID mismatches (safe operation)
        dual_id_issues = [i for i in self.issues if i.category == 'dual_id' and i.severity == 'CRITICAL']

        for issue in dual_id_issues:
            if "parent_display_id" in issue.message and "parent_id is NULL" in issue.message:
                # Safe to repair: Look up and set parent_id
                print(f"Fixing: {issue.entity_id}")

                # Get the specification
                result = self.client.table('specifications').select('*').eq('display_id', issue.entity_id).eq('project_id', self.project_id).eq('machine_id', self.machine_id).execute()

                if result.data and len(result.data) > 0:
                    spec = result.data[0]
                    parent_display_id = spec.get('parent_display_id')

                    if parent_display_id:
                        # Resolve to UUID
                        parent_uuid, error = resolve_specification_id(parent_display_id, self.project_id, self.machine_id)

                        if parent_uuid and not error:
                            # Update parent_id
                            update_result = self.client.table('specifications').update({'parent_id': parent_uuid}).eq('id', spec['id']).execute()

                            if update_result.data:
                                print(f"  ✓ Updated parent_id for '{issue.entity_id}'")
                                fixes_applied += 1
                            else:
                                print(f"  ✗ Failed to update '{issue.entity_id}'")
                        else:
                            print(f"  ✗ Cannot resolve parent '{parent_display_id}': {error}")

        print(f"\n✅ Applied {fixes_applied} fixes\n")
        return fixes_applied


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='Data Integrity Checker for MCP Task Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_data_integrity.py                    # Check only (safe)
  python check_data_integrity.py --verbose          # Detailed output
  python check_data_integrity.py --fix              # Auto-repair safe issues
  python check_data_integrity.py --table specifications  # Check one table
  python check_data_integrity.py --format json > report.json  # JSON output
        """
    )

    parser.add_argument('--project-dir', type=str, help='Project directory path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fix', action='store_true', help='Auto-repair safe issues')
    parser.add_argument('--table', type=str, choices=['specifications', 'tasks', 'sprints'], help='Check specific table only')
    parser.add_argument('--format', type=str, choices=['text', 'json'], default='text', help='Output format')

    args = parser.parse_args()

    try:
        # Initialize checker
        checker = IntegrityChecker(
            project_path=args.project_dir,
            verbose=args.verbose
        )

        # Run checks
        report = checker.run_checks(table=args.table)

        # Auto-repair if requested
        if args.fix:
            fixes_applied = checker.auto_repair()
            report['fixes_applied'] = fixes_applied

            # Re-run checks to verify
            if fixes_applied > 0:
                print("\n🔄 Re-running checks after repair...\n")
                checker.issues = []
                report = checker.run_checks(table=args.table)

        # Output format
        if args.format == 'json':
            print(json.dumps(report, indent=2))

        # Exit code
        total_issues = checker.stats['critical_issues'] + checker.stats['warnings']
        sys.exit(1 if total_issues > 0 else 0)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
