"""
Audit script to check MCP dual storage synchronization.
Compares JSON files vs Supabase database to identify sync gaps.
"""

import json
from pathlib import Path
from supabase import create_client

# Supabase connection
url = "https://yxyfiatdrgelnvxopdsm.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

client = create_client(url, key)

# Project path
project_path = Path.cwd()
data_dir = project_path / '.claude-tasks' / 'data'

def check_table_data(table_name, project_id=None):
    """Check how many records are in a table"""
    try:
        query = client.table(table_name).select('*', count='exact')
        if project_id:
            query = query.eq('project_id', project_id)
        result = query.execute()
        return len(result.data), result.data
    except Exception as e:
        return 0, f"Error: {e}"

def load_json_file(filename):
    """Load a JSON file and count items"""
    file_path = data_dir / filename
    if not file_path.exists():
        return 0, "File not found"

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            # Handle different structures
            if 'tasks' in data:
                return len(data['tasks']), data['tasks']
            elif 'sprints' in data:
                return len(data['sprints']), data['sprints']
            elif 'sessions' in data:
                return len(data['sessions']), data['sessions']
            elif 'specifications' in data:
                return len(data['specifications']), data['specifications']
            else:
                return 0, "Unknown structure"
    except Exception as e:
        return 0, f"Error: {e}"

def get_project_id():
    """Get or find project ID"""
    try:
        result = client.table('projects').select('id, path, name').eq('path', str(project_path)).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]['id'], result.data[0]
        return None, None
    except Exception as e:
        return None, f"Error: {e}"

print("=" * 80)
print("MCP DUAL STORAGE SYNCHRONIZATION AUDIT")
print("=" * 80)

# Get project info
project_id, project_info = get_project_id()
print(f"\n📁 Project Path: {project_path}")
if project_id:
    print(f"✅ Project ID: {project_id}")
    print(f"   Name: {project_info.get('name')}")
else:
    print(f"❌ Project not found in database: {project_info}")

print("\n" + "=" * 80)
print("ENTITY SYNCHRONIZATION STATUS")
print("=" * 80)

# Check each entity type
entities = [
    ('tasks', 'tasks.json', 'tasks'),
    ('sprints', 'sprints.json', 'sprints'),
    ('journal_sessions', 'journal.json', 'journal_sessions'),
    ('specifications', 'specifications.json', 'specifications'),
]

for table_name, json_file, entity_type in entities:
    print(f"\n📊 {entity_type.upper()}")
    print("-" * 80)

    # JSON file count
    json_count, json_data = load_json_file(json_file)
    print(f"   JSON File ({json_file}): {json_count} records")

    # Database count
    db_count, db_data = check_table_data(table_name, project_id)
    print(f"   Database ({table_name}): {db_count} records")

    # Sync status
    if isinstance(db_data, str):
        print(f"   ❌ Database Error: {db_data}")
    elif json_count == db_count:
        print(f"   ✅ SYNCHRONIZED ({json_count} == {db_count})")
    else:
        print(f"   ⚠️  SYNC MISMATCH! JSON has {json_count}, DB has {db_count}")

        # Show sample of what's in each
        if json_count > 0 and isinstance(json_data, list):
            print(f"\n   Sample JSON IDs: {[item.get('id') for item in json_data[:3]]}")
        if db_count > 0 and isinstance(db_data, list):
            print(f"   Sample DB IDs: {[item.get('id') for item in db_data[:3]]}")

# Check global resources
print("\n" + "=" * 80)
print("GLOBAL RESOURCES")
print("=" * 80)

# Check template tables
print(f"\n📊 TEMPLATES")
print("-" * 80)
task_templates_count, _ = check_table_data('template_tasks')
sprint_templates_count, _ = check_table_data('template_sprints')
print(f"   Database (template_tasks): {task_templates_count} records")
print(f"   Database (template_sprints): {sprint_templates_count} records")

# Check documentation table
print(f"\n📊 DOCUMENTATION")
print("-" * 80)
docs_count, docs_data = check_table_data('documentation', project_id)
print(f"   Database (documentation): {docs_count} records")
if docs_count > 0 and isinstance(docs_data, list):
    print(f"   Sample paths: {[doc.get('file_path') for doc in docs_data[:3]]}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
