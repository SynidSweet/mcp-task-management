#!/usr/bin/env python3
"""
Clean up test data from database, keeping only current project and global data.

IMPORTANT: This script will DELETE data. Review the dry-run output before executing.
"""

import sys
from pathlib import Path
from tools.document_tools import get_supabase_client, get_or_create_project_id
from core.project_manager import ProjectManager


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"{text}")
    print("="*80)


def get_current_project_info():
    """Get current project information"""
    project_path = Path.cwd()
    project_manager = ProjectManager(project_path)

    if not project_manager.is_initialized():
        print(f"❌ Project not initialized at {project_path}")
        return None, None

    project_id, error = get_or_create_project_id(project_path)
    if error:
        print(f"❌ Failed to get project ID: {error}")
        return None, None

    return project_id, project_path


def analyze_database(client, keep_project_id):
    """Analyze what data exists and what will be deleted"""

    print_header("DATABASE ANALYSIS")

    # Get all projects
    result = client.table('projects').select('id, project_path, project_name, name, path').execute()
    all_projects = result.data if result.data else []

    print(f"\n📊 Found {len(all_projects)} projects:")

    keep_projects = []
    delete_projects = []

    for project in all_projects:
        project_id = project['id']
        project_path = project.get('project_path') or project.get('path', 'Unknown')
        project_name = project.get('project_name') or project.get('name', 'Unknown')

        if project_id == keep_project_id:
            keep_projects.append(project)
            print(f"   ✅ KEEP: {project_name} ({project_path})")
        else:
            delete_projects.append(project)
            print(f"   ❌ DELETE: {project_name} ({project_path})")

    # Analyze data for each table
    tables = [
        'tasks',
        'sprints',
        'journal_sessions',
        'specifications',
        'templates',
        'commands',
        'agents',
        'documentation',
        'documents',
        'document_sections'
    ]

    print_header("DATA TO DELETE BY TABLE")

    total_to_delete = 0
    deletion_plan = {}

    for table in tables:
        try:
            # Count records to delete (those not in keep_project_id and not global)
            if table == 'document_sections':
                # document_sections references documents via document_id, not project_id directly
                # First get document IDs to delete
                docs_result = client.table('documents').select('id').neq('project_id', keep_project_id).execute()
                doc_ids_to_delete = [doc['id'] for doc in (docs_result.data or [])]

                if doc_ids_to_delete:
                    # Count sections belonging to documents to be deleted
                    result = client.table('document_sections').select('id', count='exact').in_('document_id', doc_ids_to_delete).execute()
                    count = result.count if hasattr(result, 'count') else len(result.data or [])
                else:
                    count = 0

            elif table in ['templates', 'commands', 'agents', 'documentation']:
                # These tables have is_global flag
                result = client.table(table).select('id', count='exact').neq('project_id', keep_project_id).eq('is_global', False).execute()
                count = result.count if hasattr(result, 'count') else len(result.data or [])
            else:
                # Other tables just filter by project_id
                result = client.table(table).select('id', count='exact').neq('project_id', keep_project_id).execute()
                count = result.count if hasattr(result, 'count') else len(result.data or [])

            if count > 0:
                deletion_plan[table] = count
                total_to_delete += count
                print(f"   ❌ {table}: {count} records")
            else:
                print(f"   ✅ {table}: 0 records to delete")

        except Exception as e:
            print(f"   ⚠️  {table}: Error - {e}")

    # Check global data
    print_header("GLOBAL DATA (WILL BE KEPT)")

    global_tables = ['templates', 'commands', 'agents', 'documentation']

    for table in global_tables:
        try:
            result = client.table(table).select('id', count='exact').eq('is_global', True).execute()
            count = result.count if hasattr(result, 'count') else len(result.data or [])
            print(f"   ✅ {table}: {count} global records")
        except Exception as e:
            print(f"   ⚠️  {table}: Error - {e}")

    print_header("SUMMARY")
    print(f"Projects to keep: {len(keep_projects)}")
    print(f"Projects to delete: {len(delete_projects)}")
    print(f"Total records to delete: {total_to_delete}")

    return delete_projects, deletion_plan


def execute_cleanup(client, keep_project_id, delete_projects, deletion_plan):
    """Execute the actual cleanup"""

    print_header("EXECUTING CLEANUP")
    print("⚠️  This will permanently delete data!")

    # Delete data from tables (in dependency order)
    tables_to_clean = [
        'document_sections',  # Delete sections before documents
        'documents',
        'specifications',
        'journal_sessions',
        'sprints',
        'tasks',
        'documentation',
        'agents',
        'commands',
        'templates'
    ]

    deleted_counts = {}

    for table in tables_to_clean:
        if table not in deletion_plan or deletion_plan[table] == 0:
            continue

        try:
            print(f"\n🗑️  Deleting from {table}...")

            if table == 'document_sections':
                # document_sections references documents via document_id
                # Get document IDs to delete
                docs_result = client.table('documents').select('id').neq('project_id', keep_project_id).execute()
                doc_ids_to_delete = [doc['id'] for doc in (docs_result.data or [])]

                if doc_ids_to_delete:
                    result = client.table('document_sections').delete().in_('document_id', doc_ids_to_delete).execute()
                    count = len(result.data) if result.data else 0
                else:
                    count = 0

            elif table in ['templates', 'commands', 'agents', 'documentation']:
                # Delete non-global records not in keep_project_id
                result = client.table(table).delete().neq('project_id', keep_project_id).eq('is_global', False).execute()
                count = len(result.data) if result.data else 0
            else:
                # Delete records not in keep_project_id
                result = client.table(table).delete().neq('project_id', keep_project_id).execute()
                count = len(result.data) if result.data else 0

            deleted_counts[table] = count
            print(f"   ✅ Deleted {count} records from {table}")

        except Exception as e:
            print(f"   ❌ Error deleting from {table}: {e}")

    # Delete projects last
    if delete_projects:
        print(f"\n🗑️  Deleting {len(delete_projects)} projects...")
        for project in delete_projects:
            try:
                client.table('projects').delete().eq('id', project['id']).execute()
                project_name = project.get('project_name') or project.get('name', 'Unknown')
                print(f"   ✅ Deleted project: {project_name}")
            except Exception as e:
                print(f"   ❌ Error deleting project {project['id']}: {e}")

    print_header("CLEANUP COMPLETE")
    print(f"Total records deleted: {sum(deleted_counts.values())}")
    print(f"Projects deleted: {len(delete_projects)}")

    return deleted_counts


def main():
    """Main entry point"""

    # Parse arguments
    force = '--force' in sys.argv
    dry_run = not force

    if dry_run:
        print_header("DATABASE CLEANUP - DRY RUN")
        print("This is a dry run. No data will be deleted.")
        print("Run with --force to execute the cleanup.")
    else:
        print_header("DATABASE CLEANUP - LIVE MODE")
        print("⚠️  WARNING: This will permanently delete data!")

    # Get current project
    print("\n1️⃣  Identifying current project...")
    keep_project_id, project_path = get_current_project_info()

    if not keep_project_id:
        print("❌ Cannot proceed without project ID")
        sys.exit(1)

    print(f"✅ Current project ID: {keep_project_id}")
    print(f"   Path: {project_path}")

    # Connect to database
    print("\n2️⃣  Connecting to database...")
    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        sys.exit(1)

    print("✅ Database connection established")

    # Analyze database
    print("\n3️⃣  Analyzing database...")
    delete_projects, deletion_plan = analyze_database(client, keep_project_id)

    if not delete_projects and not deletion_plan:
        print("\n✅ Database is already clean! No test data to delete.")
        return

    # Execute cleanup if not dry run
    if not dry_run and force:
        print("\n4️⃣  Executing cleanup...")

        confirm = input("\n⚠️  Type 'DELETE' to confirm: ")
        if confirm != 'DELETE':
            print("❌ Cleanup cancelled")
            sys.exit(0)

        deleted_counts = execute_cleanup(client, keep_project_id, delete_projects, deletion_plan)
    else:
        print_header("DRY RUN COMPLETE")
        print("\nTo execute the cleanup, run:")
        print("   python3 cleanup_database.py --force")
        print("\nThis will:")
        print(f"   - Delete {len(delete_projects)} projects")
        print(f"   - Delete {sum(deletion_plan.values())} records from various tables")
        print("   - Keep current project and all global data")


if __name__ == '__main__':
    main()
