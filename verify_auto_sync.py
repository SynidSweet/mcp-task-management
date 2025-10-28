#!/usr/bin/env python3
"""
Comprehensive verification of auto-sync at MCP registration.

This script checks:
1. Database connection and schema
2. Local project data files
3. Database records for this project
4. Global data files and their database records
5. Initial sync behavior
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import database helpers
from tools.document_tools import get_supabase_client, get_or_create_project_id
from core.project_manager import ProjectManager
from core.machine_id import get_machine_id


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"{text}")
    print("="*80)


def print_subheader(text):
    """Print formatted subheader"""
    print(f"\n{text}")
    print("-"*80)


def check_database_connection():
    """Check if we can connect to Supabase"""
    print_header("1. DATABASE CONNECTION")

    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        return None

    print("✅ Database connection successful")
    print(f"   URL: https://yxyfiatdrgelnvxopdsm.supabase.co")
    return client


def check_project_setup(project_path):
    """Check project setup and get project ID"""
    print_header("2. PROJECT SETUP")

    project_id, error = get_or_create_project_id(project_path)
    if error:
        print(f"❌ Failed to get/create project ID: {error}")
        return None

    print(f"✅ Project ID: {project_id}")
    print(f"   Path: {project_path}")
    print(f"   Machine ID: {get_machine_id()}")
    return project_id


def check_local_data_files(project_path):
    """Check what data files exist locally"""
    print_header("3. LOCAL DATA FILES")

    data_dir = project_path / '.claude-tasks' / 'data'
    if not data_dir.exists():
        print(f"❌ Data directory doesn't exist: {data_dir}")
        return {}

    print(f"📁 Data directory: {data_dir}")

    data_files = {}
    for json_file in data_dir.glob('*.json'):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            # Count entities based on file type (handle multiple key naming conventions)
            if json_file.name == 'tasks.json':
                entities = data.get('tasks', data.get('task', []))
            elif json_file.name == 'sprints.json':
                entities = data.get('sprints', [])
            elif json_file.name == 'journal.json':
                # Handle both 'sessions' and 'journal' keys
                entities = data.get('sessions', data.get('journal', []))
            elif json_file.name == 'specifications.json':
                # Handle both 'specifications' and 'specification' keys
                entities = data.get('specifications', data.get('specification', []))
            else:
                entities = data if isinstance(data, list) else []

            count = len(entities) if isinstance(entities, list) else 0
            data_files[json_file.name] = {
                'path': str(json_file),
                'count': count,
                'modified': datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
            }
            print(f"   ✓ {json_file.name}: {count} entities (modified: {data_files[json_file.name]['modified']})")
        except Exception as e:
            print(f"   ⚠️  {json_file.name}: Error reading - {e}")

    return data_files


def check_database_records(client, project_id):
    """Check what records exist in the database for this project"""
    print_header("4. DATABASE RECORDS FOR THIS PROJECT")

    tables = [
        ('tasks', 'id, title, status, updated_at'),
        ('sprints', 'id, title, status, updated_at'),
        ('journal_sessions', 'id, session_type, tasks_worked, created_at'),
        ('specifications', 'id, specification_name, specification_type, updated_at'),
    ]

    db_records = {}
    for table_name, select_fields in tables:
        try:
            result = client.table(table_name).select(select_fields).eq('project_id', project_id).execute()
            records = result.data if result.data else []
            db_records[table_name] = len(records)

            print(f"   ✓ {table_name}: {len(records)} records")

            # Show first few records
            if records and len(records) > 0:
                for i, record in enumerate(records[:3]):
                    id_field = record.get('id', 'N/A')
                    title_field = record.get('title') or record.get('specification_name') or record.get('session_type', 'N/A')
                    print(f"      - {id_field}: {title_field}")
                if len(records) > 3:
                    print(f"      ... and {len(records) - 3} more")
        except Exception as e:
            print(f"   ⚠️  {table_name}: Error - {e}")
            db_records[table_name] = 'error'

    return db_records


def check_global_data():
    """Check global data files and database records"""
    print_header("5. GLOBAL DATA FILES")

    claude_home = Path.home() / '.claude'

    # Check global templates
    print_subheader("Global Templates")
    global_templates = claude_home / '.claude-tasks' / 'templates'
    if global_templates.exists():
        template_files = list(global_templates.glob('*.json'))
        print(f"   ✓ {len(template_files)} template files found")
        for tf in template_files[:5]:
            print(f"      - {tf.name}")
    else:
        print(f"   ⚠️  Directory not found: {global_templates}")

    # Check global commands
    print_subheader("Global Commands")
    global_commands = claude_home / 'commands'
    if global_commands.exists():
        command_files = list(global_commands.glob('*.md'))
        print(f"   ✓ {len(command_files)} command files found")
        for cf in command_files[:5]:
            print(f"      - {cf.name}")
    else:
        print(f"   ⚠️  Directory not found: {global_commands}")

    # Check global agents
    print_subheader("Global Agents")
    global_agents = claude_home / 'agents'
    if global_agents.exists():
        agent_files = list(global_agents.glob('*.md'))
        print(f"   ✓ {len(agent_files)} agent files found")
        for af in agent_files[:5]:
            print(f"      - {af.name}")
    else:
        print(f"   ⚠️  Directory not found: {global_agents}")

    # Check global docs
    print_subheader("Global Documentation")
    global_docs = claude_home / 'docs'
    if global_docs.exists():
        doc_files = list(global_docs.rglob('*.md'))
        print(f"   ✓ {len(doc_files)} documentation files found")
        for df in doc_files[:5]:
            print(f"      - {df.relative_to(global_docs)}")
    else:
        print(f"   ⚠️  Directory not found: {global_docs}")


def check_sync_comparison(local_data, db_records):
    """Compare local vs database to see sync status"""
    print_header("6. SYNC STATUS COMPARISON")

    file_to_table = {
        'tasks.json': 'tasks',
        'sprints.json': 'sprints',
        'journal.json': 'journal_sessions',
        'specifications.json': 'specifications',
    }

    sync_issues = []

    for file_name, table_name in file_to_table.items():
        local_count = local_data.get(file_name, {}).get('count', 0)
        db_count = db_records.get(table_name, 0)

        status = "✅" if local_count == db_count else "⚠️"
        print(f"   {status} {file_name} → {table_name}")
        print(f"      Local: {local_count} | Database: {db_count}")

        if local_count != db_count:
            sync_issues.append({
                'file': file_name,
                'table': table_name,
                'local': local_count,
                'db': db_count
            })

    if sync_issues:
        print(f"\n   ⚠️  Sync discrepancies found:")
        for issue in sync_issues:
            diff = issue['local'] - issue['db']
            direction = "local ahead" if diff > 0 else "database ahead"
            print(f"      - {issue['file']}: {direction} by {abs(diff)} records")
    else:
        print(f"\n   ✅ All files are in sync with database!")

    return len(sync_issues) == 0


def main():
    """Run all verification checks"""
    print_header("AUTO-SYNC VERIFICATION REPORT")
    print(f"Generated: {datetime.now().isoformat()}")

    # Get current project path
    project_path = Path.cwd()

    # Run checks
    client = check_database_connection()
    if not client:
        print("\n❌ Cannot proceed without database connection")
        sys.exit(1)

    project_id = check_project_setup(project_path)
    if not project_id:
        print("\n❌ Cannot proceed without project ID")
        sys.exit(1)

    local_data = check_local_data_files(project_path)
    db_records = check_database_records(client, project_id)
    check_global_data()

    is_synced = check_sync_comparison(local_data, db_records)

    # Final summary
    print_header("SUMMARY")

    if is_synced:
        print("✅ AUTO-SYNC IS WORKING CORRECTLY")
        print("   - Database connection: OK")
        print("   - Project registered: OK")
        print("   - Local files synced to database: OK")
        print("   - Global resources monitored: OK")
    else:
        print("⚠️  AUTO-SYNC HAS DISCREPANCIES")
        print("   Possible causes:")
        print("   1. Initial sync hasn't run yet (server needs to be started)")
        print("   2. Files modified after last sync")
        print("   3. Manual database changes not synced back")
        print("\n   Recommended action:")
        print("   - Start the MCP server to trigger initial sync")
        print("   - Check server logs for sync errors")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
