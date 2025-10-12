"""
Unified file monitoring for automatic sync of all Claude Code data.

Single monitoring service using Watchdog Observer to detect file changes
and automatically sync to Supabase database.

Monitored Entity Types:
- Tasks, Sprints, Journal, Requirements (project-specific)
- Documents (TODO: not yet implemented)
- Templates (global + project)
- Commands, Agents (global + project)
- Documentation (global + project, recursive)
- MCP configs (global only)

Architecture:
- One Watchdog Observer monitors all paths
- File changes trigger appropriate _sync_* functions
- Each entity type syncs to its dedicated database table
- Supports both global (~/.claude) and project-specific paths
"""

import asyncio
import json
import hashlib
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class UnifiedFileEventHandler(FileSystemEventHandler):
    """
    Unified event handler for all file types

    Routes file events to appropriate sync handlers based on file patterns
    """

    def __init__(self, sync_callback: Callable):
        """
        Initialize unified event handler

        Args:
            sync_callback: Async function(file_path, change_type, file_info)
        """
        super().__init__()
        self.sync_callback = sync_callback
        self.loop = None

    def set_event_loop(self, loop):
        """Set the event loop for async callbacks"""
        self.loop = loop

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification"""
        if not event.is_directory:
            self._schedule_sync(event.src_path, 'modified')

    def on_created(self, event: FileSystemEvent):
        """Handle file creation"""
        if not event.is_directory:
            self._schedule_sync(event.src_path, 'created')

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion"""
        if not event.is_directory:
            self._schedule_sync(event.src_path, 'deleted')

    def _schedule_sync(self, file_path: str, change_type: str):
        """Schedule async sync operation"""
        if self.loop and not self.loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.sync_callback(file_path, change_type),
                    self.loop
                )
            except Exception as e:
                print(f"⚠️ Failed to schedule sync for {file_path}: {e}")


class UnifiedFileMonitor:
    """
    Unified file monitor for all Claude Code data

    Single Observer instance monitoring:
    - Global resources: ~/.claude/{commands,agents,templates,.claude-mcp-config.json}
    - Project resources: .claude-tasks/data/{tasks,sprints,journal,documents,requirements}.json
    - Project templates: .claude-tasks/templates/*.json
    """

    def __init__(self):
        """Initialize unified file monitor"""
        self.observer = Observer()
        self.event_handler = None
        self.loop = None
        self.monitoring = False

        # Track registered projects
        self.projects: Dict[str, Dict[str, Any]] = {}  # project_id -> project_info
        self.watched_paths: Set[str] = set()  # Track all watched paths

        # Global paths (shared across all projects)
        self.claude_home = Path.home() / '.claude'
        self.global_initialized = False

        # Sync loop prevention system
        self._sync_in_progress: Set[str] = set()  # Track operations in progress
        self._last_sync_hashes: Dict[str, str] = {}  # Track content hashes by file path
        self._db_sync_in_progress: Set[str] = set()  # Track database sync operations

        # Database subscription management
        self.db_subscriptions = []
        self.db_listening = False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file contents for change detection"""
        try:
            if not file_path.exists():
                return ""

            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _should_skip_sync(self, file_path: Path, from_database: bool = False) -> bool:
        """
        Check if sync should be skipped to prevent loops

        Args:
            file_path: File being synced
            from_database: True if triggered by database change

        Returns:
            True if sync should be skipped
        """
        sync_key = str(file_path)

        # Skip if sync already in progress for this file
        if sync_key in self._sync_in_progress:
            return True

        # Skip if database sync in progress and this is a file change
        if not from_database and sync_key in self._db_sync_in_progress:
            return True

        # Check content hash to detect actual changes
        current_hash = self._calculate_file_hash(file_path)
        last_hash = self._last_sync_hashes.get(sync_key)

        if current_hash and current_hash == last_hash:
            return True  # No actual change, skip sync

        return False

    async def initialize(self):
        """Initialize monitoring system"""
        try:
            # Get event loop
            self.loop = asyncio.get_running_loop()

            # Create unified event handler
            self.event_handler = UnifiedFileEventHandler(self._handle_file_change)
            self.event_handler.set_event_loop(self.loop)

            print("✅ Unified file monitor initialized")
            return True

        except Exception as e:
            print(f"❌ Unified file monitor initialization failed: {e}")
            return False

    async def register_global_resources(self):
        """
        Register user-global resources (once for all projects)

        Monitors:
        - ~/.claude/commands/*.md
        - ~/.claude/agents/*.md
        - ~/.claude/.claude-tasks/templates/*.json
        - ~/.claude/.claude-mcp-config.json
        """
        if self.global_initialized:
            return  # Already registered

        try:
            # Monitor global commands
            global_commands = self.claude_home / 'commands'
            if global_commands.exists():
                self._schedule_watch(global_commands, recursive=False)

            # Monitor global agents
            global_agents = self.claude_home / 'agents'
            if global_agents.exists():
                self._schedule_watch(global_agents, recursive=False)

            # Monitor global templates
            global_templates = self.claude_home / '.claude-tasks' / 'templates'
            if global_templates.exists():
                self._schedule_watch(global_templates, recursive=False)

            # Monitor global MCP config (single file)
            global_mcp_config = self.claude_home / '.claude-mcp-config.json'
            if global_mcp_config.exists():
                # Watch parent directory, filter in handler
                self._schedule_watch(self.claude_home, recursive=False)

            # Monitor global docs folder (recursive for subdirectories)
            global_docs = self.claude_home / 'docs'
            if global_docs.exists():
                self._schedule_watch(global_docs, recursive=True)

            self.global_initialized = True
            print(f"✅ Global resources registered for monitoring")

        except Exception as e:
            print(f"⚠️ Failed to register global resources: {e}")

    async def register_project(self, project_id: str, project_path: Path, project_manager):
        """
        Register a project for monitoring

        Args:
            project_id: Unique project identifier (typically str(project_path))
            project_path: Path to project directory
            project_manager: ProjectManager instance for this project
        """
        if project_id in self.projects:
            print(f"⚠️ Project {project_id} already registered")
            return

        try:
            project_info = {
                'project_path': project_path,
                'project_manager': project_manager,
                'watched_paths': []
            }

            # Monitor project data files
            data_dir = project_path / '.claude-tasks' / 'data'
            if data_dir.exists():
                self._schedule_watch(data_dir, recursive=False)
                project_info['watched_paths'].append(str(data_dir))

            # Monitor project templates
            templates_dir = project_path / '.claude-tasks' / 'templates'
            if templates_dir.exists():
                self._schedule_watch(templates_dir, recursive=False)
                project_info['watched_paths'].append(str(templates_dir))

            # Monitor project commands
            project_commands = project_path / '.claude' / 'commands'
            if project_commands.exists():
                self._schedule_watch(project_commands, recursive=False)
                project_info['watched_paths'].append(str(project_commands))

            # Monitor project agents
            project_agents = project_path / '.claude' / 'agents'
            if project_agents.exists():
                self._schedule_watch(project_agents, recursive=False)
                project_info['watched_paths'].append(str(project_agents))

            # Monitor project docs folder (recursive for subdirectories)
            project_docs = project_path / 'docs'
            if project_docs.exists():
                self._schedule_watch(project_docs, recursive=True)
                project_info['watched_paths'].append(str(project_docs))

            self.projects[project_id] = project_info
            print(f"✅ Project registered: {project_path.name} ({len(project_info['watched_paths'])} paths)")

            # Perform initial sync for project data files
            await self._initial_sync_project(project_id, project_path, project_manager)

        except Exception as e:
            print(f"⚠️ Failed to register project {project_id}: {e}")

    def _schedule_watch(self, path: Path, recursive: bool = False):
        """Schedule a path for watching (deduplicates)

        Note: Initial sync is performed separately in register_project/register_global_resources
        after all paths are scheduled, to avoid partial syncs.
        """
        path_str = str(path)
        if path_str not in self.watched_paths:
            self.observer.schedule(self.event_handler, path_str, recursive=recursive)
            self.watched_paths.add(path_str)

    async def start_monitoring(self):
        """Start unified file monitoring and database subscriptions"""
        if not await self.initialize():
            return False

        try:
            print("\n" + "="*60)
            print("🔄 STARTING UNIFIED FILE MONITORING")
            print("="*60)

            # Register global resources first
            await self.register_global_resources()

            # Start observer
            self.observer.start()
            self.monitoring = True

            print(f"\n✅ Monitoring {len(self.watched_paths)} paths:")
            for path in sorted(self.watched_paths):
                print(f"   📁 {path}")
            print(f"\n🔄 Auto-sync active for all file changes")
            print("="*60 + "\n")

            # Start database subscriptions for bidirectional sync
            await self.start_database_subscriptions()

            return True

        except Exception as e:
            print(f"❌ Failed to start unified monitoring: {e}")
            return False

    async def _handle_file_change(self, file_path: str, change_type: str):
        """
        Handle file change events and route to appropriate sync

        Routes based on file location and type:
        - *.json in .claude-tasks/data/ -> sync_data_file()
        - *.json in .claude-tasks/templates/ -> sync_template_file()
        - *.md in commands/ -> sync_command_file()
        - *.md in agents/ -> sync_agent_file()
        - *.md in docs/ -> sync_doc_markdown_file()
        - .claude-mcp-config.json -> sync_mcp_config()
        """
        try:
            file_path_obj = Path(file_path)

            # Determine file type and route to appropriate sync
            if file_path.endswith('.json'):
                if '/.claude-tasks/data/' in file_path:
                    await self._sync_data_file(file_path_obj, change_type)
                elif '/.claude-tasks/templates/' in file_path:
                    await self._sync_template_file(file_path_obj, change_type)
                elif file_path.endswith('.claude-mcp-config.json'):
                    await self._sync_mcp_config(file_path_obj, change_type)

            elif file_path.endswith('.md'):
                if '/commands/' in file_path:
                    await self._sync_command_file(file_path_obj, change_type)
                elif '/agents/' in file_path:
                    await self._sync_agent_file(file_path_obj, change_type)
                elif '/docs/' in file_path:
                    await self._sync_doc_markdown_file(file_path_obj, change_type)

        except Exception as e:
            print(f"❌ Error handling file change {file_path}: {e}")

    async def _sync_data_file(self, file_path: Path, change_type: str):
        """Sync data files (tasks.json, sprints.json, journal.json, etc.) to Supabase"""
        file_name = file_path.name
        print(f"🔄 Data file {change_type}: {file_name}")

        # Find which project this file belongs to
        project_manager = self._find_project_for_file(file_path)
        if not project_manager:
            print(f"⚠️ No project found for {file_path}")
            return

        # Route to appropriate sync based on file name
        # Note: documents.json removed - using /docs/*.md files only
        if file_name == 'tasks.json':
            await self._sync_tasks(file_path, change_type, project_manager)
        elif file_name == 'sprints.json':
            await self._sync_sprints(file_path, change_type, project_manager)
        elif file_name == 'journal.json':
            await self._sync_journal(file_path, change_type, project_manager)
        elif file_name == 'specifications.json':
            await self._sync_specifications(file_path, change_type, project_manager)

    async def _sync_template_file(self, file_path: Path, change_type: str, from_database: bool = False):
        """Sync template files (task_templates.json or sprint_templates.json) to Supabase templates table with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            import uuid
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            print(f"🔄 Template {change_type}: {file_path.name}")

            # Read template file
            with open(file_path, 'r') as f:
                templates_data = json.load(f)

            if not templates_data:
                print(f"   ℹ️  No templates to sync")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            machine_id = get_machine_id()

            # Determine scope and project_id
            is_user_scope = str(file_path).startswith(str(self.claude_home))
            scope = 'global' if is_user_scope else 'project'

            if is_user_scope:
                project_id = None
            else:
                project_manager = self._find_project_for_file(file_path)
                if project_manager:
                    project_id, _ = get_or_create_project_id(project_manager.project_path)
                else:
                    project_id = None

            # Determine template type from filename
            template_type = 'task_template' if 'task' in file_path.name else 'sprint_template'

            # Sync all templates to Supabase templates table (upsert strategy)
            synced_count = 0
            for template_name, template_data in templates_data.items():
                if not isinstance(template_data, dict):
                    continue

                try:
                    # Create template record
                    template_record = {
                        'id': str(uuid.uuid4()),
                        'project_id': project_id,
                        'template_type': template_type,
                        'scope': scope,
                        'is_global': is_user_scope,
                        'data': template_data,  # Store as JSONB
                        'updated_at': 'now()',
                        'version': 1,
                        'hash': str(hash(json.dumps(template_data, sort_keys=True)))
                    }

                    # Upsert to templates table (conflict on project_id + template_type + template name in data)
                    result = client.table('templates').upsert(template_record).execute()
                    if result.data:
                        synced_count += 1

                except Exception as e:
                    print(f"   ⚠️  Failed to sync template {template_name}: {e}")

            print(f"   ✅ Synced {synced_count}/{len(templates_data)} templates to cloud")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Template sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_command_file(self, file_path: Path, change_type: str, from_database: bool = False):
        """Sync command .md file to Supabase commands table with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import uuid
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            print(f"🔄 Command {change_type}: {file_path.name}")

            # Read command file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content:
                print(f"   ℹ️  Empty command file")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            machine_id = get_machine_id()

            # Determine scope (user vs project)
            is_user_scope = str(file_path).startswith(str(self.claude_home))
            scope = 'global' if is_user_scope else 'project'

            if is_user_scope:
                project_id = None
                relative_path = str(file_path.relative_to(self.claude_home / 'commands'))
            else:
                project_manager = self._find_project_for_file(file_path)
                if project_manager:
                    project_id, _ = get_or_create_project_id(project_manager)
                    relative_path = str(file_path.relative_to(project_manager.project_path / '.claude' / 'commands'))
                else:
                    project_id = None
                    relative_path = file_path.name

            # Extract description from content (first non-header line)
            description = ""
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and len(stripped) > 10:
                    description = stripped[:200]
                    break

            # Check if command already exists (to preserve ID for upsert)
            existing_query = client.table('commands').select('id').eq('command_name', file_path.stem)
            if project_id:
                existing_query = existing_query.eq('project_id', project_id)
            else:
                existing_query = existing_query.is_('project_id', 'null')

            existing = existing_query.execute()
            command_id = existing.data[0]['id'] if existing.data else str(uuid.uuid4())

            # Create command record
            command_record = {
                'id': command_id,
                'project_id': project_id,
                'machine_id': machine_id,
                'command_name': file_path.stem,
                'file_path': relative_path,
                'description': description,
                'content': content,
                'scope': scope,
                'is_global': is_user_scope,
                'created_at': 'now()',
                'updated_at': 'now()'
            }

            # Upsert to commands table
            result = client.table('commands').upsert(command_record).execute()
            if result.data:
                print(f"   ✅ Synced command {file_path.stem} to cloud")
            else:
                print(f"   ⚠️  Failed to sync command")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Command sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_agent_file(self, file_path: Path, change_type: str, from_database: bool = False):
        """Sync agent .md file to Supabase agents table with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import yaml
            import uuid
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            print(f"🔄 Agent {change_type}: {file_path.name}")

            # Read agent file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content:
                print(f"   ℹ️  Empty agent file")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            machine_id = get_machine_id()

            # Parse YAML frontmatter if present
            agent_config = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    try:
                        agent_config = yaml.safe_load(yaml_content) or {}
                    except yaml.YAMLError:
                        pass

            # Determine scope (user vs project)
            is_user_scope = str(file_path).startswith(str(self.claude_home))
            scope = 'global' if is_user_scope else 'project'

            if is_user_scope:
                project_id = None
                relative_path = str(file_path.relative_to(self.claude_home / 'agents'))
            else:
                project_manager = self._find_project_for_file(file_path)
                if project_manager:
                    project_id, _ = get_or_create_project_id(project_manager)
                    relative_path = str(file_path.relative_to(project_manager.project_path / '.claude' / 'agents'))
                else:
                    project_id = None
                    relative_path = file_path.name

            # Check if agent already exists (to preserve ID for upsert)
            agent_name = agent_config.get('name', file_path.stem)
            existing_query = client.table('agents').select('id').eq('agent_name', agent_name)
            if project_id:
                existing_query = existing_query.eq('project_id', project_id)
            else:
                existing_query = existing_query.is_('project_id', 'null')

            existing = existing_query.execute()
            agent_id = existing.data[0]['id'] if existing.data else str(uuid.uuid4())

            # Create agent record
            agent_record = {
                'id': agent_id,
                'project_id': project_id,
                'machine_id': machine_id,
                'agent_name': agent_name,
                'file_path': relative_path,
                'description': agent_config.get('description', ''),
                'content': content,
                'tools_config': str(agent_config.get('tools', '*')),
                'scope': scope,
                'is_global': is_user_scope,
                'created_at': 'now()',
                'updated_at': 'now()'
            }

            # Upsert to agents table
            result = client.table('agents').upsert(agent_record).execute()
            if result.data:
                print(f"   ✅ Synced agent {file_path.stem} to cloud")
            else:
                print(f"   ⚠️  Failed to sync agent")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Agent sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_mcp_config(self, file_path: Path, change_type: str, from_database: bool = False):
        """Sync MCP config file (.claude-mcp-config.json) to Supabase mcp_configs table with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            import uuid
            from tools.document_tools import get_supabase_client
            from core.machine_id import get_machine_id

            print(f"🔄 MCP config {change_type}: {file_path.name}")

            # Only sync if this is the MCP config file
            if file_path.name != '.claude-mcp-config.json':
                return

            # Read MCP config file
            with open(file_path, 'r') as f:
                config_data = json.load(f)

            if not config_data:
                print(f"   ℹ️  Empty MCP config")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            machine_id = get_machine_id()

            # Create MCP config record
            mcp_config_record = {
                'id': str(uuid.uuid4()),
                'machine_id': machine_id,
                'config_name': 'claude_mcp_config',
                'file_path': str(file_path.relative_to(self.claude_home)),
                'config_data': config_data,  # Store as JSONB
                'scope': 'global',
                'is_global': True,
                'created_at': 'now()',
                'updated_at': 'now()'
            }

            # Upsert to mcp_configs table
            result = client.table('mcp_configs').upsert(mcp_config_record).execute()
            if result.data:
                print(f"   ✅ Synced MCP config to cloud")
            else:
                print(f"   ⚠️  Failed to sync MCP config")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ MCP config sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_doc_markdown_file(self, file_path: Path, change_type: str, from_database: bool = False):
        """Sync documentation .md file from docs/ folder to Supabase documentation table with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import uuid
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            print(f"🔄 Doc {change_type}: {file_path.name}")

            # Read doc file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content:
                print(f"   ℹ️  Empty doc file")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            machine_id = get_machine_id()

            # Determine scope: check if file belongs to a registered project first
            project_manager = self._find_project_for_file(file_path)

            if project_manager:
                # Project docs: found a registered project
                is_user_scope = False
                scope = 'project'
                project_path = project_manager.project_path
                relative_path = file_path.relative_to(project_path / 'docs')

                # Get project ID for project-scoped docs
                project_id, project_error = get_or_create_project_id(project_path)
                if project_error:
                    print(f"   ⚠️  Project ID error: {project_error}")
                    project_id = None
            elif str(file_path).startswith(str(self.claude_home / 'docs')):
                # Global docs: ~/.claude/docs/... (but not part of a project)
                is_user_scope = True
                scope = 'global'
                relative_path = file_path.relative_to(self.claude_home / 'docs')
                project_id = None
            else:
                # Unknown location
                print(f"   ⚠️  File not in known docs location: {file_path}")
                return

            # Create doc path identifier (e.g., "architecture/overview.md" or "setup/installation.md")
            doc_path = str(relative_path).replace('\\', '/')

            # Extract title from first # header if present, otherwise use filename
            title = file_path.stem
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('# '):
                    title = stripped[2:].strip()
                    break

            # Extract description from content (first non-header paragraph)
            description = ""
            in_frontmatter = False
            for line in content.split('\n'):
                stripped = line.strip()

                # Skip YAML frontmatter
                if stripped == '---':
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter:
                    continue

                # Skip headers and empty lines
                if stripped and not stripped.startswith('#') and len(stripped) > 10:
                    description = stripped[:200]
                    break

            # Check if document already exists (to preserve ID for upsert)
            existing_query = client.table('documentation').select('id').eq('file_path', doc_path)
            if project_id:
                existing_query = existing_query.eq('project_id', project_id)
            else:
                existing_query = existing_query.is_('project_id', 'null')

            existing = existing_query.execute()
            doc_id = existing.data[0]['id'] if existing.data else str(uuid.uuid4())

            # Create documentation record
            doc_record = {
                'id': doc_id,
                'project_id': project_id,
                'machine_id': machine_id,
                'doc_title': title,
                'file_path': doc_path,
                'description': description,
                'content': content,
                'scope': scope,
                'is_global': is_user_scope,
                'created_at': 'now()',
                'updated_at': 'now()'
            }

            # Upsert to documentation table
            result = client.table('documentation').upsert(doc_record).execute()
            if result.data:
                print(f"   ✅ Synced doc {doc_path} to cloud")
            else:
                print(f"   ⚠️  Failed to sync doc")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Doc sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    # ============================================================================
    # Unified Sync Implementation Functions
    # ============================================================================

    async def _sync_tasks(self, file_path: Path, change_type: str, project_manager, from_database: bool = False):
        """Sync tasks.json to Supabase with loop prevention"""
        # Check loop prevention BEFORE doing work
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            # Read tasks.json
            with open(file_path, 'r') as f:
                data = json.load(f)

            tasks = data.get('tasks', data.get('task', []))
            if not tasks:
                print(f"   ℹ️  No tasks to sync")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            # Get project ID
            project_id, project_error = get_or_create_project_id(project_manager.project_path)
            if project_error:
                print(f"   ⚠️  Project ID error: {project_error}")
                return

            machine_id = get_machine_id()

            # Database schema: only these fields are supported
            SUPPORTED_TASK_FIELDS = {
                'id', 'title', 'description', 'status', 'priority', 'notes',
                'dependencies', 'completed_at', 'created_at', 'updated_at',
                'project_id', 'machine_id'
            }

            # Sync all tasks to Supabase (upsert strategy)
            synced_count = 0
            for task in tasks:
                try:
                    # Filter to only supported fields
                    cloud_task = {
                        k: v for k, v in task.items()
                        if k in SUPPORTED_TASK_FIELDS
                    }
                    cloud_task['project_id'] = project_id
                    cloud_task['machine_id'] = machine_id

                    # Upsert (insert or update)
                    result = client.table('tasks').upsert(cloud_task).execute()
                    if result.data:
                        synced_count += 1

                except Exception as e:
                    print(f"   ⚠️  Failed to sync task {task.get('id', 'unknown')}: {e}")

            print(f"   ✅ Synced {synced_count}/{len(tasks)} tasks to cloud")

            # Update hash after successful sync
            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Tasks sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_sprints(self, file_path: Path, change_type: str, project_manager, from_database: bool = False):
        """Sync sprints.json to Supabase with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            # Read sprints.json
            with open(file_path, 'r') as f:
                data = json.load(f)

            sprints = data.get('sprints', [])
            if not sprints:
                print(f"   ℹ️  No sprints to sync")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            # Get project ID
            project_id, project_error = get_or_create_project_id(project_manager.project_path)
            if project_error:
                print(f"   ⚠️  Project ID error: {project_error}")
                return

            machine_id = get_machine_id()

            # Database schema: only these fields are supported (based on actual schema)
            SUPPORTED_SPRINT_FIELDS = {
                'id', 'title', 'description', 'status',
                'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            # Sync all sprints to Supabase (upsert strategy)
            synced_count = 0
            for sprint in sprints:
                try:
                    # Filter to only supported fields
                    cloud_sprint = {
                        k: v for k, v in sprint.items()
                        if k in SUPPORTED_SPRINT_FIELDS
                    }
                    cloud_sprint['project_id'] = project_id
                    cloud_sprint['machine_id'] = machine_id

                    # Upsert (insert or update)
                    result = client.table('sprints').upsert(cloud_sprint).execute()
                    if result.data:
                        synced_count += 1

                except Exception as e:
                    print(f"   ⚠️  Failed to sync sprint {sprint.get('id', 'unknown')}: {e}")

            print(f"   ✅ Synced {synced_count}/{len(sprints)} sprints to cloud")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Sprints sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_journal(self, file_path: Path, change_type: str, project_manager, from_database: bool = False):
        """Sync journal.json to Supabase with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            # Read journal.json
            with open(file_path, 'r') as f:
                data = json.load(f)

            journal_entries = data.get('journal', data.get('sessions', []))
            if not journal_entries:
                print(f"   ℹ️  No journal entries to sync")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            # Get project ID
            project_id, project_error = get_or_create_project_id(project_manager.project_path)
            if project_error:
                print(f"   ⚠️  Project ID error: {project_error}")
                return

            machine_id = get_machine_id()

            # Database schema: only these fields are supported
            SUPPORTED_JOURNAL_FIELDS = {
                'id', 'session_type', 'tasks_worked', 'key_achievements', 'discoveries',
                'duration_minutes', 'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            # Sync all journal entries to Supabase (upsert strategy)
            synced_count = 0
            for entry in journal_entries:
                try:
                    # Filter to only supported fields with type conversion
                    cloud_entry = {}
                    for k, v in entry.items():
                        if k in SUPPORTED_JOURNAL_FIELDS:
                            # Convert duration_minutes to integer
                            if k == 'duration_minutes':
                                cloud_entry[k] = int(float(v)) if v is not None else None
                            else:
                                cloud_entry[k] = v

                    cloud_entry['project_id'] = project_id
                    cloud_entry['machine_id'] = machine_id

                    # Upsert (insert or update)
                    result = client.table('journal_sessions').upsert(cloud_entry).execute()
                    if result.data:
                        synced_count += 1

                except Exception as e:
                    print(f"   ⚠️  Failed to sync journal entry {entry.get('id', 'unknown')}: {e}")

            print(f"   ✅ Synced {synced_count}/{len(journal_entries)} journal entries to cloud")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Journal sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_documents(self, file_path: Path, change_type: str, project_manager, from_database: bool = False):
        """
        Sync documents.json to Supabase documents + document_sections tables with loop prevention.

        Note: This is different from _sync_doc_markdown_file which handles /docs/**/*.md files.
        - documents.json → documents + document_sections tables (structured documents with sections)
        - docs/**/*.md → documentation table (simple markdown files)
        """
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            print(f"🔄 Data file {change_type}: documents.json")

            # Read documents.json
            with open(file_path, 'r') as f:
                data = json.load(f)

            documents = data.get('documents', [])
            if not documents:
                print(f"   ℹ️  No documents to sync")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            # Get project ID
            project_id, project_error = get_or_create_project_id(project_manager.project_path)
            if project_error:
                print(f"   ⚠️  Project ID error: {project_error}")
                return

            machine_id = get_machine_id()

            # Database schema: only these fields are supported
            SUPPORTED_DOCUMENT_FIELDS = {
                'id', 'document_title', 'document_type', 'description', 'status', 'priority',
                'document_path', 'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            # Sync all documents to Supabase (upsert strategy)
            synced_count = 0
            for doc in documents:
                try:
                    # Extract sections separately
                    sections = doc.pop('sections', [])

                    # Filter to only supported fields
                    cloud_doc = {
                        k: v for k, v in doc.items()
                        if k in SUPPORTED_DOCUMENT_FIELDS
                    }

                    # Generate document_path from calculated_path or derive from title
                    if not cloud_doc.get('document_path'):
                        if doc.get('calculated_path'):
                            cloud_doc['document_path'] = doc['calculated_path'] + '.md'
                        else:
                            doc_type = doc.get('document_type', 'general')
                            doc_title = doc.get('document_title', 'untitled')
                            cloud_doc['document_path'] = f"{doc_type}/{doc_title}.md"

                    cloud_doc['project_id'] = project_id
                    cloud_doc['machine_id'] = machine_id

                    # Upsert document
                    result = client.table('documents').upsert(cloud_doc).execute()
                    if result.data:
                        doc_id = doc['id']

                        # Sync sections if any
                        if sections:
                            # Delete existing sections first
                            client.table('document_sections').delete().eq('document_id', doc_id).execute()

                            # Insert new sections
                            for i, section in enumerate(sections):
                                section_record = {
                                    'id': str(uuid.uuid4()),
                                    'document_id': doc_id,
                                    'section_type': section.get('section_type', 'content'),
                                    'section_title': section.get('section_title', ''),
                                    'content': section.get('content', ''),
                                    'content_format': section.get('content_format', 'markdown'),
                                    'sort_order': section.get('sort_order', i),
                                    'created_at': 'now()',
                                    'updated_at': 'now()'
                                }
                                client.table('document_sections').insert(section_record).execute()

                        synced_count += 1

                    # Restore sections to doc
                    doc['sections'] = sections

                except Exception as e:
                    print(f"   ⚠️  Failed to sync document {doc.get('id', 'unknown')}: {e}")

            print(f"   ✅ Synced {synced_count}/{len(documents)} documents to cloud")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Documents sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    async def _sync_specifications(self, file_path: Path, change_type: str, project_manager, from_database: bool = False):
        """Sync specifications.json to Supabase specifications table with loop prevention"""
        if self._should_skip_sync(file_path, from_database=from_database):
            return

        sync_key = str(file_path)
        self._sync_in_progress.add(sync_key)

        try:
            import json
            from tools.document_tools import get_supabase_client, get_or_create_project_id
            from core.machine_id import get_machine_id

            # Read specifications.json
            with open(file_path, 'r') as f:
                data = json.load(f)

            specifications = data.get('specifications', data.get('requirement', data.get('entities', [])))
            if not specifications:
                print(f"   ℹ️  No specifications to sync")
                return

            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  Supabase client error: {error}")
                return

            # Get project ID
            project_id, project_error = get_or_create_project_id(project_manager.project_path)
            if project_error:
                print(f"   ⚠️  Project ID error: {project_error}")
                return

            machine_id = get_machine_id()

            # Supported fields for specifications table
            SUPPORTED_SPEC_FIELDS = {
                'id', 'display_id', 'specification_name', 'specification_type',
                'description', 'parent_id', 'parent_display_id', 'approved',
                'implemented', 'validated', 'level_depth', 'sort_order',
                'specification_path', 'version',
                'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            # Sync all specifications to Supabase (upsert strategy)
            synced_count = 0
            for spec in specifications:
                try:
                    # Map old entity schema if needed
                    cloud_spec = {}
                    for k, v in spec.items():
                        if k == 'entity_name':
                            cloud_spec['specification_name'] = v
                        elif k == 'entity_type':
                            cloud_spec['specification_type'] = v
                        elif k == 'entity_path' and v:
                            cloud_spec['specification_path'] = v
                        elif k == 'specification_path' and not v:
                            continue
                        elif k in SUPPORTED_SPEC_FIELDS:
                            cloud_spec[k] = v

                    # Set default specification_path if missing
                    if not cloud_spec.get('specification_path'):
                        cloud_spec['specification_path'] = cloud_spec.get('display_id') or spec.get('id') or 'unknown'

                    cloud_spec['project_id'] = project_id
                    cloud_spec['machine_id'] = machine_id

                    # Upsert (insert or update)
                    result = client.table('specifications').upsert(cloud_spec).execute()
                    if result.data:
                        synced_count += 1

                except Exception as e:
                    print(f"   ⚠️  Failed to sync specification {spec.get('id', 'unknown')}: {e}")

            print(f"   ✅ Synced {synced_count}/{len(specifications)} specifications to cloud")

            self._last_sync_hashes[sync_key] = self._calculate_file_hash(file_path)

        except Exception as e:
            print(f"   ❌ Specifications sync failed: {e}")
        finally:
            self._sync_in_progress.discard(sync_key)

    def _find_project_for_file(self, file_path: Path) -> Optional[Any]:
        """Find which project a file belongs to"""
        for project_id, project_info in self.projects.items():
            project_path = project_info['project_path']
            if project_path in file_path.parents:
                return project_info['project_manager']
        return None

    # ============================================================================
    # Initial Sync: Bidirectional entity-level sync on registration
    # ============================================================================

    async def _initial_sync_project(self, project_id: str, project_path: Path, project_manager):
        """
        Perform initial bidirectional sync for all project data files.

        Compares local files vs database at entity level (task by task, etc.)
        and syncs based on timestamps.
        """
        print("\n" + "="*60)
        print("🔄 INITIAL SYNC: Comparing local ↔ database")
        print("="*60)

        data_dir = project_path / '.claude-tasks' / 'data'

        # Sync each entity type at entity level
        # Note: documents.json removed - using /docs/*.md files only
        sync_tasks = [
            ('tasks.json', self._initial_sync_tasks_entities),
            ('sprints.json', self._initial_sync_sprints_entities),
            ('journal.json', self._initial_sync_journal_entities),
            ('specifications.json', self._initial_sync_specifications_entities),
        ]

        for filename, sync_method in sync_tasks:
            file_path = data_dir / filename
            if file_path.exists():
                try:
                    await sync_method(file_path, project_manager)
                except Exception as e:
                    print(f"   ⚠️  {filename}: {e}")

        print("="*60 + "\n")

    async def _initial_sync_tasks_entities(self, file_path: Path, project_manager):
        """Initial sync for tasks - entity by entity with timestamp comparison"""
        import json
        from datetime import datetime
        from tools.document_tools import get_supabase_client, get_or_create_project_id
        from core.machine_id import get_machine_id

        try:
            # Load local tasks
            with open(file_path, 'r') as f:
                data = json.load(f)

            local_tasks = data if isinstance(data, list) else data.get('tasks', data.get('task', []))

            if not local_tasks:
                print(f"   ℹ️  tasks.json: No local tasks")
                return

            # Get database tasks
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  tasks.json: Database error: {error}")
                return

            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return

            db_result = client.table('tasks').select('*').eq('project_id', project_id).execute()
            db_tasks = db_result.data if db_result.data else []

            # Create maps by ID
            local_map = {t['id']: t for t in local_tasks if 'id' in t}
            db_map = {t['id']: t for t in db_tasks if 'id' in t}

            all_ids = set(local_map.keys()) | set(db_map.keys())

            machine_id = get_machine_id()
            synced_to_db = 0
            synced_to_local = 0
            skipped = 0

            SUPPORTED_FIELDS = {
                'id', 'title', 'description', 'status', 'priority', 'notes',
                'dependencies', 'completed_at', 'created_at', 'updated_at',
                'project_id', 'machine_id'
            }

            for task_id in all_ids:
                local_task = local_map.get(task_id)
                db_task = db_map.get(task_id)

                if not db_task:
                    # Only in local → sync to database
                    cloud_task = {k: v for k, v in local_task.items() if k in SUPPORTED_FIELDS}
                    cloud_task['project_id'] = project_id
                    cloud_task['machine_id'] = machine_id
                    client.table('tasks').upsert(cloud_task).execute()
                    synced_to_db += 1

                elif not local_task:
                    # Only in DB → sync to local
                    clean_task = {k: v for k, v in db_task.items() if k not in ['project_id', 'machine_id']}
                    local_tasks.append(clean_task)
                    synced_to_local += 1

                else:
                    # Both exist → compare timestamps
                    local_ts = local_task.get('updated_at', local_task.get('created_at', ''))
                    db_ts = db_task.get('updated_at', db_task.get('created_at', ''))

                    if local_ts > db_ts:
                        # Local is newer → sync to DB
                        cloud_task = {k: v for k, v in local_task.items() if k in SUPPORTED_FIELDS}
                        cloud_task['project_id'] = project_id
                        cloud_task['machine_id'] = machine_id
                        client.table('tasks').upsert(cloud_task).execute()
                        synced_to_db += 1
                    elif db_ts > local_ts:
                        # DB is newer → sync to local
                        clean_task = {k: v for k, v in db_task.items() if k not in ['project_id', 'machine_id']}
                        # Update in local_tasks list
                        for i, t in enumerate(local_tasks):
                            if t.get('id') == task_id:
                                local_tasks[i] = clean_task
                                break
                        synced_to_local += 1
                    else:
                        # Same timestamp → skip
                        skipped += 1

            # Save local changes if any
            if synced_to_local > 0:
                if 'task' in data:
                    data['task'] = local_tasks
                else:
                    data['tasks'] = local_tasks
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

            print(f"   ✅ tasks.json: {synced_to_db} →DB, {synced_to_local} ←DB, {skipped} synced")

        except Exception as e:
            print(f"   ❌ tasks.json initial sync failed: {e}")

    async def _initial_sync_sprints_entities(self, file_path: Path, project_manager):
        """Initial sync for sprints - entity by entity with timestamp comparison"""
        import json
        from tools.document_tools import get_supabase_client, get_or_create_project_id
        from core.machine_id import get_machine_id

        try:
            # Load local sprints
            with open(file_path, 'r') as f:
                data = json.load(f)

            local_sprints = data.get('sprints', [])
            if not local_sprints:
                print(f"   ℹ️  sprints.json: No local sprints")
                return

            # Get database sprints
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  sprints.json: Database error: {error}")
                return

            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return

            db_result = client.table('sprints').select('*').eq('project_id', project_id).execute()
            db_sprints = db_result.data if db_result.data else []

            # Create maps by ID
            local_map = {s['id']: s for s in local_sprints if 'id' in s}
            db_map = {s['id']: s for s in db_sprints if 'id' in s}

            all_ids = set(local_map.keys()) | set(db_map.keys())

            machine_id = get_machine_id()
            synced_to_db = 0
            synced_to_local = 0
            skipped = 0

            # Filter to database-supported fields only (based on actual schema)
            SUPPORTED_FIELDS = {
                'id', 'title', 'description', 'status',
                'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            for sprint_id in all_ids:
                local_sprint = local_map.get(sprint_id)
                db_sprint = db_map.get(sprint_id)

                if not db_sprint:
                    # Only in local → sync to database
                    cloud_sprint = {k: v for k, v in local_sprint.items() if k in SUPPORTED_FIELDS}
                    cloud_sprint['project_id'] = project_id
                    cloud_sprint['machine_id'] = machine_id
                    client.table('sprints').upsert(cloud_sprint).execute()
                    synced_to_db += 1

                elif not local_sprint:
                    # Only in DB → sync to local
                    clean_sprint = {k: v for k, v in db_sprint.items() if k not in ['project_id', 'machine_id']}
                    local_sprints.append(clean_sprint)
                    synced_to_local += 1

                else:
                    # Both exist → compare timestamps
                    local_ts = local_sprint.get('updated_at', local_sprint.get('created_at', ''))
                    db_ts = db_sprint.get('updated_at', db_sprint.get('created_at', ''))

                    if local_ts > db_ts:
                        cloud_sprint = {k: v for k, v in local_sprint.items() if k in SUPPORTED_FIELDS}
                        cloud_sprint['project_id'] = project_id
                        cloud_sprint['machine_id'] = machine_id
                        client.table('sprints').upsert(cloud_sprint).execute()
                        synced_to_db += 1
                    elif db_ts > local_ts:
                        clean_sprint = {k: v for k, v in db_sprint.items() if k not in ['project_id', 'machine_id']}
                        for i, s in enumerate(local_sprints):
                            if s.get('id') == sprint_id:
                                local_sprints[i] = clean_sprint
                                break
                        synced_to_local += 1
                    else:
                        skipped += 1

            # Save local changes if any
            if synced_to_local > 0:
                data['sprints'] = local_sprints
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

            print(f"   ✅ sprints.json: {synced_to_db} →DB, {synced_to_local} ←DB, {skipped} synced")

        except Exception as e:
            print(f"   ❌ sprints.json initial sync failed: {e}")

    async def _initial_sync_journal_entities(self, file_path: Path, project_manager):
        """Initial sync for journal - entity by entity with timestamp comparison"""
        import json
        from tools.document_tools import get_supabase_client, get_or_create_project_id
        from core.machine_id import get_machine_id

        try:
            # Load local journal
            with open(file_path, 'r') as f:
                data = json.load(f)

            local_sessions = data.get('journal', data.get('sessions', []))
            if not local_sessions:
                print(f"   ℹ️  journal.json: No local sessions")
                return

            # Get database journal sessions
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  journal.json: Database error: {error}")
                return

            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return

            # Note: table is journal_sessions not journal
            db_result = client.table('journal_sessions').select('*').eq('project_id', project_id).execute()
            db_sessions = db_result.data if db_result.data else []

            # Create maps by ID
            local_map = {s['id']: s for s in local_sessions if 'id' in s}
            db_map = {s['id']: s for s in db_sessions if 'id' in s}

            all_ids = set(local_map.keys()) | set(db_map.keys())

            machine_id = get_machine_id()
            synced_to_db = 0
            synced_to_local = 0
            skipped = 0

            SUPPORTED_FIELDS = {
                'id', 'session_type', 'tasks_worked', 'key_achievements', 'discoveries',
                'duration_minutes', 'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            for session_id in all_ids:
                try:
                    local_session = local_map.get(session_id)
                    db_session = db_map.get(session_id)

                    if not db_session:
                        cloud_session = {}
                        for k, v in local_session.items():
                            if k in SUPPORTED_FIELDS:
                                # Convert duration_minutes to integer
                                if k == 'duration_minutes':
                                    cloud_session[k] = int(float(v)) if v is not None else None
                                else:
                                    cloud_session[k] = v

                        cloud_session['project_id'] = project_id
                        cloud_session['machine_id'] = machine_id
                        client.table('journal_sessions').upsert(cloud_session).execute()
                        synced_to_db += 1

                    elif not local_session:
                        clean_session = {k: v for k, v in db_session.items() if k not in ['project_id', 'machine_id']}
                        local_sessions.append(clean_session)
                        synced_to_local += 1

                    else:
                        local_ts = local_session.get('updated_at', local_session.get('created_at', ''))
                        db_ts = db_session.get('updated_at', db_session.get('created_at', ''))

                        if local_ts > db_ts:
                            cloud_session = {}
                            for k, v in local_session.items():
                                if k in SUPPORTED_FIELDS:
                                    # Convert duration_minutes to integer
                                    if k == 'duration_minutes':
                                        cloud_session[k] = int(float(v)) if v is not None else None
                                    else:
                                        cloud_session[k] = v

                            cloud_session['project_id'] = project_id
                            cloud_session['machine_id'] = machine_id
                            client.table('journal_sessions').upsert(cloud_session).execute()
                            synced_to_db += 1
                        elif db_ts > local_ts:
                            clean_session = {k: v for k, v in db_session.items() if k not in ['project_id', 'machine_id']}
                            for i, s in enumerate(local_sessions):
                                if s.get('id') == session_id:
                                    local_sessions[i] = clean_session
                                    break
                            synced_to_local += 1
                        else:
                            skipped += 1

                except Exception as e:
                    print(f"      ⚠️  Skipped session {session_id}: {str(e)[:80]}")
                    continue

            if synced_to_local > 0:
                # Save to same key we read from
                if 'journal' in data:
                    data['journal'] = local_sessions
                else:
                    data['sessions'] = local_sessions
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

            print(f"   ✅ journal.json: {synced_to_db} →DB, {synced_to_local} ←DB, {skipped} synced")

        except Exception as e:
            print(f"   ❌ journal.json initial sync failed: {e}")

    async def _initial_sync_documents_entities(self, file_path: Path, project_manager):
        """Initial sync for documents - entity by entity with timestamp comparison"""
        import json
        from tools.document_tools import get_supabase_client, get_or_create_project_id
        from core.machine_id import get_machine_id

        try:
            # Load local documents
            with open(file_path, 'r') as f:
                data = json.load(f)

            local_docs = data.get('documents', [])
            if not local_docs:
                print(f"   ℹ️  documents.json: No local documents")
                return

            # Get database documents
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  documents.json: Database error: {error}")
                return

            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return

            db_result = client.table('documents').select('*').eq('project_id', project_id).execute()
            db_docs = db_result.data if db_result.data else []

            # Create maps by ID
            local_map = {d['id']: d for d in local_docs if 'id' in d}
            db_map = {d['id']: d for d in db_docs if 'id' in d}

            all_ids = set(local_map.keys()) | set(db_map.keys())

            machine_id = get_machine_id()
            synced_to_db = 0
            synced_to_local = 0
            skipped = 0

            SUPPORTED_FIELDS = {
                'id', 'document_title', 'document_type', 'description', 'status', 'priority',
                'document_path', 'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            for doc_id in all_ids:
                try:
                    local_doc = local_map.get(doc_id)
                    db_doc = db_map.get(doc_id)

                    if not db_doc:
                        cloud_doc = {k: v for k, v in local_doc.items() if k in SUPPORTED_FIELDS}

                        # Validate UUID - skip non-UUID test documents
                        import uuid
                        try:
                            uuid.UUID(doc_id)
                        except ValueError:
                            print(f"      ℹ️  Skipping non-UUID document: {doc_id}")
                            continue

                        # Generate document_path from calculated_path or derive from title
                        if not cloud_doc.get('document_path'):
                            if local_doc.get('calculated_path'):
                                cloud_doc['document_path'] = local_doc['calculated_path'] + '.md'
                            else:
                                doc_type = local_doc.get('document_type', 'general')
                                doc_title = local_doc.get('document_title', 'untitled')
                                # Create path like "guides/Document Title.md"
                                cloud_doc['document_path'] = f"{doc_type}/{doc_title}.md"

                        cloud_doc['project_id'] = project_id
                        cloud_doc['machine_id'] = machine_id
                        client.table('documents').upsert(cloud_doc).execute()
                        synced_to_db += 1

                    elif not local_doc:
                        clean_doc = {k: v for k, v in db_doc.items() if k not in ['project_id', 'machine_id']}
                        local_docs.append(clean_doc)
                        synced_to_local += 1

                    else:
                        local_ts = local_doc.get('updated_at', local_doc.get('created_at', ''))
                        db_ts = db_doc.get('updated_at', db_doc.get('created_at', ''))

                        if local_ts > db_ts:
                            cloud_doc = {k: v for k, v in local_doc.items() if k in SUPPORTED_FIELDS}

                            # Generate document_path from calculated_path or derive from title
                            if not cloud_doc.get('document_path'):
                                if local_doc.get('calculated_path'):
                                    cloud_doc['document_path'] = local_doc['calculated_path'] + '.md'
                                else:
                                    doc_type = local_doc.get('document_type', 'general')
                                    doc_title = local_doc.get('document_title', 'untitled')
                                    cloud_doc['document_path'] = f"{doc_type}/{doc_title}.md"

                            cloud_doc['project_id'] = project_id
                            cloud_doc['machine_id'] = machine_id
                            client.table('documents').upsert(cloud_doc).execute()
                            synced_to_db += 1
                        elif db_ts > local_ts:
                            clean_doc = {k: v for k, v in db_doc.items() if k not in ['project_id', 'machine_id']}
                            for i, d in enumerate(local_docs):
                                if d.get('id') == doc_id:
                                    local_docs[i] = clean_doc
                                    break
                            synced_to_local += 1
                        else:
                            skipped += 1

                except Exception as e:
                    print(f"      ⚠️  Skipped document {doc_id}: {str(e)[:80]}")
                    continue

            if synced_to_local > 0:
                data['documents'] = local_docs
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

            print(f"   ✅ documents.json: {synced_to_db} →DB, {synced_to_local} ←DB, {skipped} synced")

        except Exception as e:
            print(f"   ❌ documents.json initial sync failed: {e}")

    async def _initial_sync_specifications_entities(self, file_path: Path, project_manager):
        """Initial sync for specifications - entity by entity with timestamp comparison"""
        import json
        from tools.document_tools import get_supabase_client, get_or_create_project_id
        from core.machine_id import get_machine_id

        try:
            # Load local specifications
            with open(file_path, 'r') as f:
                data = json.load(f)

            local_specs = data.get('specifications', data.get('requirement', data.get('entities', [])))
            if not local_specs:
                print(f"   ℹ️  specifications.json: No local specifications")
                return

            # Get database specifications
            client, error = get_supabase_client()
            if error:
                print(f"   ⚠️  specifications.json: Database error: {error}")
                return

            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return

            db_result = client.table('specifications').select('*').eq('project_id', project_id).execute()
            db_specs = db_result.data if db_result.data else []

            # Create maps by ID
            local_map = {s.get('id'): s for s in local_specs if s.get('id')}
            db_map = {s['id']: s for s in db_specs if 'id' in s}

            all_ids = set(local_map.keys()) | set(db_map.keys())

            machine_id = get_machine_id()
            synced_to_db = 0
            synced_to_local = 0
            skipped = 0

            # Match actual database columns (specifications table schema)
            SUPPORTED_FIELDS = {
                'id', 'display_id', 'specification_name', 'specification_type',
                'description', 'parent_id', 'parent_display_id', 'approved',
                'implemented', 'validated', 'level_depth', 'sort_order',
                'specification_path', 'version',
                'created_at', 'updated_at', 'project_id', 'machine_id'
            }

            for spec_id in all_ids:
                try:
                    local_spec = local_map.get(spec_id)
                    db_spec = db_map.get(spec_id)

                    if not db_spec:
                        # Map old entity schema to new specification schema if needed
                        cloud_spec = {}
                        for k, v in local_spec.items():
                            # Map entity_name → specification_name
                            if k == 'entity_name':
                                cloud_spec['specification_name'] = v
                            # Map entity_type → specification_type
                            elif k == 'entity_type':
                                cloud_spec['specification_type'] = v
                            # Map entity_path → specification_path (skip if null, use default later)
                            elif k == 'entity_path' and v:
                                cloud_spec['specification_path'] = v
                            # Skip specification_path if it's explicitly null
                            elif k == 'specification_path' and not v:
                                continue
                            # Keep supported fields as-is
                            elif k in SUPPORTED_FIELDS:
                                cloud_spec[k] = v

                        # Always set specification_path (required field) - use display_id or id as fallback
                        if not cloud_spec.get('specification_path'):
                            cloud_spec['specification_path'] = cloud_spec.get('display_id') or spec_id or 'unknown'

                        cloud_spec['project_id'] = project_id
                        cloud_spec['machine_id'] = machine_id
                        client.table('specifications').upsert(cloud_spec).execute()
                        synced_to_db += 1

                    elif not local_spec:
                        clean_spec = {k: v for k, v in db_spec.items() if k not in ['project_id', 'machine_id']}
                        local_specs.append(clean_spec)
                        synced_to_local += 1

                    else:
                        local_ts = local_spec.get('updated_at', local_spec.get('created_at', ''))
                        db_ts = db_spec.get('updated_at', db_spec.get('created_at', ''))

                        if local_ts > db_ts:
                            # Map old entity schema to new specification schema if needed
                            cloud_spec = {}
                            for k, v in local_spec.items():
                                if k == 'entity_name':
                                    cloud_spec['specification_name'] = v
                                elif k == 'entity_type':
                                    cloud_spec['specification_type'] = v
                                elif k == 'entity_path' and v:
                                    cloud_spec['specification_path'] = v
                                elif k == 'specification_path' and not v:
                                    continue
                                elif k in SUPPORTED_FIELDS:
                                    cloud_spec[k] = v

                            # Always set specification_path (required field)
                            if not cloud_spec.get('specification_path'):
                                cloud_spec['specification_path'] = cloud_spec.get('display_id') or spec_id or 'unknown'

                            cloud_spec['project_id'] = project_id
                            cloud_spec['machine_id'] = machine_id
                            client.table('specifications').upsert(cloud_spec).execute()
                            synced_to_db += 1
                        elif db_ts > local_ts:
                            clean_spec = {k: v for k, v in db_spec.items() if k not in ['project_id', 'machine_id']}
                            for i, s in enumerate(local_specs):
                                if s.get('id') == spec_id:
                                    local_specs[i] = clean_spec
                                    break
                            synced_to_local += 1
                        else:
                            skipped += 1

                except Exception as e:
                    print(f"      ⚠️  Skipped spec {spec_id}: {str(e)[:80]}")
                    continue

            if synced_to_local > 0:
                data['specifications'] = local_specs
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

            print(f"   ✅ specifications.json: {synced_to_db} →DB, {synced_to_local} ←DB, {skipped} synced")

        except Exception as e:
            print(f"   ❌ specifications.json initial sync failed: {e}")

    # ============================================================================
    # Bidirectional Sync: Database → File
    # ============================================================================

    async def start_database_subscriptions(self):
        """
        Start Supabase realtime subscriptions for all entity tables.
        Listens for INSERT/UPDATE/DELETE events and syncs to local files.
        """
        try:
            from tools.document_tools import get_supabase_client

            client, error = get_supabase_client()
            if error:
                print(f"⚠️ Cannot start database subscriptions: {error}")
                return False

            # Tables to monitor for changes
            tables = [
                'tasks', 'sprints', 'journal_sessions', 'requirements',
                'documents', 'templates', 'commands', 'agents',
                'documentation', 'mcp_configs'
            ]

            print("\n" + "="*60)
            print("🔄 STARTING DATABASE SUBSCRIPTIONS")
            print("="*60)

            for table in tables:
                try:
                    # Create channel for this table
                    channel = client.channel(f'db-changes-{table}')

                    # Subscribe to all changes on this table
                    channel.on_postgres_changes(
                        event='*',  # INSERT, UPDATE, DELETE
                        schema='public',
                        table=table,
                        callback=lambda payload, t=table: asyncio.create_task(
                            self._handle_database_change(t, payload)
                        )
                    ).subscribe()

                    self.db_subscriptions.append(channel)
                    print(f"   ✅ Subscribed to {table} table changes")

                except Exception as e:
                    print(f"   ⚠️ Failed to subscribe to {table}: {e}")

            self.db_listening = True
            print(f"\n✅ Database subscriptions active for {len(self.db_subscriptions)} tables")
            print("="*60 + "\n")

            return True

        except Exception as e:
            print(f"❌ Failed to start database subscriptions: {e}")
            return False

    async def _handle_database_change(self, table: str, payload: Dict[str, Any]):
        """
        Handle database change event and sync to appropriate local file.

        Args:
            table: Table name that changed
            payload: Change event payload with old/new records
        """
        try:
            event_type = payload.get('eventType')  # INSERT, UPDATE, DELETE
            record = payload.get('new') or payload.get('old')

            if not record:
                return

            print(f"📥 Database change detected: {table} ({event_type})")

            # Route to appropriate sync function based on table
            if table == 'tasks':
                await self._sync_db_to_file_tasks(record, event_type)
            elif table == 'sprints':
                await self._sync_db_to_file_sprints(record, event_type)
            elif table == 'journal_sessions':
                await self._sync_db_to_file_journal(record, event_type)
            elif table == 'requirements':
                await self._sync_db_to_file_requirements(record, event_type)
            elif table == 'documents':
                await self._sync_db_to_file_documents(record, event_type)
            elif table == 'templates':
                await self._sync_db_to_file_templates(record, event_type)
            elif table == 'commands':
                await self._sync_db_to_file_commands(record, event_type)
            elif table == 'agents':
                await self._sync_db_to_file_agents(record, event_type)
            elif table == 'documentation':
                await self._sync_db_to_file_documentation(record, event_type)
            elif table == 'mcp_configs':
                await self._sync_db_to_file_mcp_configs(record, event_type)

        except Exception as e:
            print(f"❌ Error handling database change for {table}: {e}")

    async def stop_database_subscriptions(self):
        """Stop all database subscriptions"""
        if self.db_subscriptions:
            print("🛑 Stopping database subscriptions...")
            for channel in self.db_subscriptions:
                try:
                    channel.unsubscribe()
                except Exception as e:
                    print(f"⚠️ Error unsubscribing channel: {e}")

            self.db_subscriptions.clear()
            self.db_listening = False
            print("✅ Database subscriptions stopped")

    # Database → File sync functions (one per entity type)
    # These functions write database changes back to local files

    async def _sync_db_to_file_tasks(self, record: Dict[str, Any], event_type: str):
        """Sync database task change to local tasks.json"""
        try:
            project_id = record.get('project_id')
            if not project_id:
                return  # Skip global tasks for now

            # Find project manager for this project_id
            project_manager = self._find_project_by_id(project_id)
            if not project_manager:
                print(f"   ⚠️ No project found for project_id {project_id}")
                return

            # Get tasks file
            tasks_file = project_manager.project_path / '.claude-tasks' / 'data' / 'tasks.json'

            # Check if we should skip this sync (loop prevention)
            if self._should_skip_sync(tasks_file, from_database=True):
                return

            sync_key = str(tasks_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                # Read current file
                with open(tasks_file, 'r') as f:
                    data = json.load(f)

                tasks = data.get('tasks', data.get('task', []))

                # Handle DELETE event
                if event_type == 'DELETE':
                    tasks = [t for t in tasks if t.get('id') != record.get('id')]
                else:
                    # Handle INSERT/UPDATE
                    task_id = record.get('id')
                    found = False

                    # Update existing task
                    for i, task in enumerate(tasks):
                        if task.get('id') == task_id:
                            # Remove database-only fields
                            clean_record = {k: v for k, v in record.items()
                                          if k not in ['project_id', 'machine_id']}
                            tasks[i] = clean_record
                            found = True
                            break

                    # Insert new task if not found
                    if not found:
                        clean_record = {k: v for k, v in record.items()
                                      if k not in ['project_id', 'machine_id']}
                        tasks.append(clean_record)

                # Write back to file
                if 'task' in data:
                    data['task'] = tasks
                else:
                    data['tasks'] = tasks

                with open(tasks_file, 'w') as f:
                    json.dump(data, f, indent=2)

                # Update hash to prevent file monitor from syncing back
                self._last_sync_hashes[sync_key] = self._calculate_file_hash(tasks_file)

                print(f"   ✅ Synced task {record.get('id')[:8]}... to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync task to file: {e}")

    def _find_project_by_id(self, project_id: str) -> Optional[Any]:
        """Find project manager by project ID"""
        for pid, project_info in self.projects.items():
            # Check if this project matches the project_id
            # This is a simplified check - you may need to enhance this
            if str(project_info['project_path']) == project_id or pid == project_id:
                return project_info['project_manager']
        return None

    async def _sync_db_to_file_sprints(self, record: Dict[str, Any], event_type: str):
        """Sync database sprint change to local sprints.json"""
        try:
            project_id = record.get('project_id')
            if not project_id:
                return  # Skip global sprints

            project_manager = self._find_project_by_id(project_id)
            if not project_manager:
                print(f"   ⚠️ No project found for project_id {project_id}")
                return

            sprints_file = project_manager.project_path / '.claude-tasks' / 'data' / 'sprints.json'

            if self._should_skip_sync(sprints_file, from_database=True):
                return

            sync_key = str(sprints_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                with open(sprints_file, 'r') as f:
                    data = json.load(f)

                sprints = data.get('sprints', [])

                if event_type == 'DELETE':
                    sprints = [s for s in sprints if s.get('id') != record.get('id')]
                else:
                    sprint_id = record.get('id')
                    found = False

                    for i, sprint in enumerate(sprints):
                        if sprint.get('id') == sprint_id:
                            clean_record = {k: v for k, v in record.items()
                                          if k not in ['project_id', 'machine_id']}
                            sprints[i] = clean_record
                            found = True
                            break

                    if not found:
                        clean_record = {k: v for k, v in record.items()
                                      if k not in ['project_id', 'machine_id']}
                        sprints.append(clean_record)

                data['sprints'] = sprints

                with open(sprints_file, 'w') as f:
                    json.dump(data, f, indent=2)

                self._last_sync_hashes[sync_key] = self._calculate_file_hash(sprints_file)

                print(f"   ✅ Synced sprint {record.get('id')[:8]}... to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync sprint to file: {e}")

    async def _sync_db_to_file_journal(self, record: Dict[str, Any], event_type: str):
        """Sync database journal change to local journal.json"""
        try:
            project_id = record.get('project_id')
            if not project_id:
                return  # Skip global journal entries

            project_manager = self._find_project_by_id(project_id)
            if not project_manager:
                print(f"   ⚠️ No project found for project_id {project_id}")
                return

            journal_file = project_manager.project_path / '.claude-tasks' / 'data' / 'journal.json'

            if self._should_skip_sync(journal_file, from_database=True):
                return

            sync_key = str(journal_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                with open(journal_file, 'r') as f:
                    data = json.load(f)

                sessions = data.get('sessions', [])

                if event_type == 'DELETE':
                    sessions = [s for s in sessions if s.get('id') != record.get('id')]
                else:
                    session_id = record.get('id')
                    found = False

                    for i, session in enumerate(sessions):
                        if session.get('id') == session_id:
                            clean_record = {k: v for k, v in record.items()
                                          if k not in ['project_id', 'machine_id']}
                            sessions[i] = clean_record
                            found = True
                            break

                    if not found:
                        clean_record = {k: v for k, v in record.items()
                                      if k not in ['project_id', 'machine_id']}
                        sessions.append(clean_record)

                data['sessions'] = sessions

                with open(journal_file, 'w') as f:
                    json.dump(data, f, indent=2)

                self._last_sync_hashes[sync_key] = self._calculate_file_hash(journal_file)

                print(f"   ✅ Synced journal entry {record.get('id')[:8]}... to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync journal to file: {e}")

    async def _sync_db_to_file_requirements(self, record: Dict[str, Any], event_type: str):
        """Sync database requirement change to local requirements.json"""
        try:
            project_id = record.get('project_id')
            if not project_id:
                return  # Skip global requirements

            project_manager = self._find_project_by_id(project_id)
            if not project_manager:
                print(f"   ⚠️ No project found for project_id {project_id}")
                return

            requirements_file = project_manager.project_path / '.claude-tasks' / 'data' / 'requirements.json'

            if self._should_skip_sync(requirements_file, from_database=True):
                return

            sync_key = str(requirements_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                with open(requirements_file, 'r') as f:
                    data = json.load(f)

                requirements = data.get('requirements', [])

                if event_type == 'DELETE':
                    requirements = [r for r in requirements if r.get('id') != record.get('id')]
                else:
                    req_id = record.get('id')
                    found = False

                    for i, req in enumerate(requirements):
                        if req.get('id') == req_id:
                            clean_record = {k: v for k, v in record.items()
                                          if k not in ['project_id', 'machine_id']}
                            requirements[i] = clean_record
                            found = True
                            break

                    if not found:
                        clean_record = {k: v for k, v in record.items()
                                      if k not in ['project_id', 'machine_id']}
                        requirements.append(clean_record)

                data['requirements'] = requirements

                with open(requirements_file, 'w') as f:
                    json.dump(data, f, indent=2)

                self._last_sync_hashes[sync_key] = self._calculate_file_hash(requirements_file)

                print(f"   ✅ Synced requirement {record.get('id')[:8]}... to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync requirement to file: {e}")

    async def _sync_db_to_file_documents(self, record: Dict[str, Any], event_type: str):
        """Sync database document change to local documents.json"""
        try:
            from tools.document_tools import get_supabase_client

            project_id = record.get('project_id')
            if not project_id:
                return  # Skip global documents

            project_manager = self._find_project_by_id(project_id)
            if not project_manager:
                print(f"   ⚠️ No project found for project_id {project_id}")
                return

            documents_file = project_manager.project_path / '.claude-tasks' / 'data' / 'documents.json'

            if self._should_skip_sync(documents_file, from_database=True):
                return

            sync_key = str(documents_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                with open(documents_file, 'r') as f:
                    data = json.load(f)

                documents = data.get('documents', [])

                if event_type == 'DELETE':
                    documents = [d for d in documents if d.get('id') != record.get('id')]
                else:
                    doc_id = record.get('id')
                    found = False

                    # Fetch sections for this document from database
                    sections = []
                    client, error = get_supabase_client()
                    if not error and client:
                        try:
                            result = client.table('document_sections')\
                                .select('*')\
                                .eq('document_id', doc_id)\
                                .order('sort_order')\
                                .execute()

                            if result.data:
                                # Clean sections: remove document_id and database-only fields
                                sections = [
                                    {k: v for k, v in s.items()
                                     if k not in ['document_id', 'id', 'created_at', 'updated_at']}
                                    for s in result.data
                                ]
                        except Exception as e:
                            print(f"   ⚠️ Failed to fetch sections: {e}")

                    # Clean record and add sections
                    clean_record = {k: v for k, v in record.items()
                                  if k not in ['project_id', 'machine_id']}
                    clean_record['sections'] = sections

                    for i, doc in enumerate(documents):
                        if doc.get('id') == doc_id:
                            documents[i] = clean_record
                            found = True
                            break

                    if not found:
                        documents.append(clean_record)

                data['documents'] = documents

                with open(documents_file, 'w') as f:
                    json.dump(data, f, indent=2)

                self._last_sync_hashes[sync_key] = self._calculate_file_hash(documents_file)

                print(f"   ✅ Synced document {record.get('id')[:8]}... to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync document to file: {e}")

    async def _sync_db_to_file_templates(self, record: Dict[str, Any], event_type: str):
        """Sync database template change to local template files"""
        try:
            # Determine scope and file location
            is_global = record.get('is_global', record.get('scope') == 'global')
            template_type = record.get('template_type', 'task_template')

            # Determine file name and path
            if 'sprint' in template_type:
                filename = 'sprint_templates.json'
            else:
                filename = 'task_templates.json'

            if is_global:
                template_file = self.claude_home / '.claude-tasks' / 'templates' / filename
                project_manager = None
            else:
                project_id = record.get('project_id')
                if not project_id:
                    return

                project_manager = self._find_project_by_id(project_id)
                if not project_manager:
                    print(f"   ⚠️ No project found for project_id {project_id}")
                    return

                template_file = project_manager.project_path / '.claude-tasks' / 'templates' / filename

            if self._should_skip_sync(template_file, from_database=True):
                return

            sync_key = str(template_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                # Read current file (templates are stored as dict, not array)
                if template_file.exists():
                    with open(template_file, 'r') as f:
                        templates = json.load(f)
                else:
                    templates = {}

                # Extract template data and name
                template_data = record.get('data', {})
                template_name = template_data.get('metadata', {}).get('template_id', f"template_{record.get('id')[:8]}")

                if event_type == 'DELETE':
                    templates.pop(template_name, None)
                else:
                    # Clean template data: remove database-only fields from root
                    clean_data = {k: v for k, v in template_data.items()}
                    templates[template_name] = clean_data

                with open(template_file, 'w') as f:
                    json.dump(templates, f, indent=2)

                self._last_sync_hashes[sync_key] = self._calculate_file_hash(template_file)

                print(f"   ✅ Synced template {template_name} to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync template to file: {e}")

    async def _sync_db_to_file_commands(self, record: Dict[str, Any], event_type: str):
        """Sync database command change to local command .md files"""
        try:
            is_global = record.get('is_global', record.get('scope') == 'global')
            file_path = record.get('file_path', f"{record.get('command_name', 'command')}.md")

            if is_global:
                command_file = self.claude_home / 'commands' / file_path
            else:
                project_id = record.get('project_id')
                if not project_id:
                    return

                project_manager = self._find_project_by_id(project_id)
                if not project_manager:
                    print(f"   ⚠️ No project found for project_id {project_id}")
                    return

                command_file = project_manager.project_path / '.claude' / 'commands' / file_path

            if self._should_skip_sync(command_file, from_database=True):
                return

            sync_key = str(command_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                if event_type == 'DELETE':
                    if command_file.exists():
                        command_file.unlink()
                        print(f"   ✅ Deleted command file {file_path}")
                else:
                    # Create parent directory if needed
                    command_file.parent.mkdir(parents=True, exist_ok=True)

                    # Write content to file
                    content = record.get('content', '')
                    with open(command_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self._last_sync_hashes[sync_key] = self._calculate_file_hash(command_file)

                    print(f"   ✅ Synced command {file_path} to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync command to file: {e}")

    async def _sync_db_to_file_agents(self, record: Dict[str, Any], event_type: str):
        """Sync database agent change to local agent .md files"""
        try:
            is_global = record.get('is_global', record.get('scope') == 'global')
            file_path = record.get('file_path', f"{record.get('agent_name', 'agent')}.md")

            if is_global:
                agent_file = self.claude_home / 'agents' / file_path
            else:
                project_id = record.get('project_id')
                if not project_id:
                    return

                project_manager = self._find_project_by_id(project_id)
                if not project_manager:
                    print(f"   ⚠️ No project found for project_id {project_id}")
                    return

                agent_file = project_manager.project_path / '.claude' / 'agents' / file_path

            if self._should_skip_sync(agent_file, from_database=True):
                return

            sync_key = str(agent_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                if event_type == 'DELETE':
                    if agent_file.exists():
                        agent_file.unlink()
                        print(f"   ✅ Deleted agent file {file_path}")
                else:
                    # Create parent directory if needed
                    agent_file.parent.mkdir(parents=True, exist_ok=True)

                    # Write content to file (includes YAML frontmatter)
                    content = record.get('content', '')
                    with open(agent_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self._last_sync_hashes[sync_key] = self._calculate_file_hash(agent_file)

                    print(f"   ✅ Synced agent {file_path} to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync agent to file: {e}")

    async def _sync_db_to_file_documentation(self, record: Dict[str, Any], event_type: str):
        """Sync database documentation change to local doc .md files"""
        try:
            is_global = record.get('is_global', record.get('scope') == 'global')
            file_path = record.get('file_path', 'document.md')

            if is_global:
                doc_file = self.claude_home / 'docs' / file_path
            else:
                project_id = record.get('project_id')
                if not project_id:
                    return

                project_manager = self._find_project_by_id(project_id)
                if not project_manager:
                    print(f"   ⚠️ No project found for project_id {project_id}")
                    return

                doc_file = project_manager.project_path / 'docs' / file_path

            if self._should_skip_sync(doc_file, from_database=True):
                return

            sync_key = str(doc_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                if event_type == 'DELETE':
                    if doc_file.exists():
                        doc_file.unlink()
                        print(f"   ✅ Deleted documentation file {file_path}")
                else:
                    # Create parent directory if needed
                    doc_file.parent.mkdir(parents=True, exist_ok=True)

                    # Write content to file
                    content = record.get('content', '')
                    with open(doc_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self._last_sync_hashes[sync_key] = self._calculate_file_hash(doc_file)

                    print(f"   ✅ Synced documentation {file_path} to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync documentation to file: {e}")

    async def _sync_db_to_file_mcp_configs(self, record: Dict[str, Any], event_type: str):
        """Sync database MCP config change to local .claude-mcp-config.json"""
        try:
            # MCP configs are always global
            mcp_config_file = self.claude_home / '.claude-mcp-config.json'

            if self._should_skip_sync(mcp_config_file, from_database=True):
                return

            sync_key = str(mcp_config_file)
            self._db_sync_in_progress.add(sync_key)

            try:
                if event_type == 'DELETE':
                    if mcp_config_file.exists():
                        mcp_config_file.unlink()
                        print(f"   ✅ Deleted MCP config file")
                else:
                    # Write config_data to file
                    config_data = record.get('config_data', {})
                    with open(mcp_config_file, 'w') as f:
                        json.dump(config_data, f, indent=2)

                    self._last_sync_hashes[sync_key] = self._calculate_file_hash(mcp_config_file)

                    print(f"   ✅ Synced MCP config to file")

            finally:
                self._db_sync_in_progress.discard(sync_key)

        except Exception as e:
            print(f"   ❌ Failed to sync MCP config to file: {e}")

    async def stop_monitoring(self):
        """Stop unified file monitoring and database subscriptions"""
        # Stop database subscriptions first
        await self.stop_database_subscriptions()

        # Stop file monitoring
        if self.observer and self.monitoring:
            print("🛑 Stopping unified file monitoring...")
            self.observer.stop()
            self.observer.join(timeout=5)
            self.monitoring = False
            print("✅ Unified file monitoring stopped")

    def is_monitoring(self) -> bool:
        """Check if currently monitoring"""
        return self.monitoring and self.observer and self.observer.is_alive()


# Global singleton instance
_unified_monitor: Optional[UnifiedFileMonitor] = None


async def get_unified_monitor() -> UnifiedFileMonitor:
    """Get or create the global unified file monitor"""
    global _unified_monitor

    if _unified_monitor is None:
        _unified_monitor = UnifiedFileMonitor()

    return _unified_monitor


async def start_unified_monitoring() -> Optional[UnifiedFileMonitor]:
    """Start the unified file monitoring system"""
    monitor = await get_unified_monitor()

    if await monitor.start_monitoring():
        return monitor
    else:
        print("❌ Failed to start unified monitoring")
        return None
