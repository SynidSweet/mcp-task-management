#!/usr/bin/env python3
"""
Database audit script - checks what data exists in Supabase
"""
import sys
from supabase import create_client

# Supabase connection
SUPABASE_URL = "https://yxyfiatdrgelnvxopdsm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

def main():
    try:
        print("=" * 80)
        print("DATABASE AUDIT REPORT")
        print("=" * 80)
        print()

        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Read machine_id
        try:
            with open('.claude-tasks/config/machine_id.txt', 'r') as f:
                machine_id = f.read().strip()
            print(f"✓ Local machine_id: {machine_id}")
        except FileNotFoundError:
            print("✗ No machine_id.txt found")
            machine_id = None

        print()
        print("-" * 80)
        print("CHECKING PROJECTS TABLE")
        print("-" * 80)

        # Check projects table
        result = client.table("projects").select("*").execute()
        if result.data:
            print(f"✓ Found {len(result.data)} project(s) in database:")
            for proj in result.data:
                print(f"  - Project ID: {proj.get('id')}")
                print(f"    Machine ID: {proj.get('machine_id')}")
                print(f"    Name: {proj.get('name')}")
                print(f"    Path: {proj.get('path')}")  # Fixed: use 'path' not 'project_path'
                print()
        else:
            print("✗ NO PROJECTS FOUND IN DATABASE")
            print()

        # If we have a machine_id, check for matching project
        if machine_id:
            print("-" * 80)
            print(f"CHECKING FOR PROJECT WITH MACHINE_ID: {machine_id}")
            print("-" * 80)
            result = client.table("projects").select("*").eq("machine_id", machine_id).execute()
            if result.data:
                project_id = result.data[0]['id']
                print(f"✓ Found matching project: {project_id}")
                print()

                # Check tasks for this project
                print("-" * 80)
                print(f"CHECKING TASKS FOR PROJECT: {project_id}")
                print("-" * 80)
                result = client.table("tasks").select("id, title, status, priority").eq("project_id", project_id).execute()
                if result.data:
                    print(f"✓ Found {len(result.data)} task(s):")
                    for task in result.data[:5]:  # Show first 5
                        print(f"  - {task.get('id')}: {task.get('title')} [{task.get('status')}]")
                    if len(result.data) > 5:
                        print(f"  ... and {len(result.data) - 5} more")
                else:
                    print("✗ NO TASKS FOUND for this project")
                print()

                # Check sprints
                print("-" * 80)
                print(f"CHECKING SPRINTS FOR PROJECT: {project_id}")
                print("-" * 80)
                result = client.table("sprints").select("id, title, status").eq("project_id", project_id).execute()
                if result.data:
                    print(f"✓ Found {len(result.data)} sprint(s):")
                    for sprint in result.data:
                        print(f"  - {sprint.get('id')}: {sprint.get('title')} [{sprint.get('status')}]")
                else:
                    print("✗ NO SPRINTS FOUND for this project")
                print()

                # Check journal sessions
                print("-" * 80)
                print(f"CHECKING JOURNAL SESSIONS FOR PROJECT: {project_id}")
                print("-" * 80)
                result = client.table("journal_sessions").select("id, session_type, duration_minutes").eq("project_id", project_id).execute()
                if result.data:
                    print(f"✓ Found {len(result.data)} journal session(s):")
                    for session in result.data[:5]:
                        print(f"  - {session.get('id')}: {session.get('session_type')} ({session.get('duration_minutes')} min)")
                    if len(result.data) > 5:
                        print(f"  ... and {len(result.data) - 5} more")
                else:
                    print("✗ NO JOURNAL SESSIONS FOUND for this project")
                print()

                # Check specifications
                print("-" * 80)
                print(f"CHECKING SPECIFICATIONS FOR PROJECT: {project_id}")
                print("-" * 80)
                result = client.table("specifications").select("id, display_id, specification_name").eq("project_id", project_id).execute()
                if result.data:
                    print(f"✓ Found {len(result.data)} specification(s):")
                    for spec in result.data[:5]:
                        print(f"  - {spec.get('display_id')}: {spec.get('specification_name')}")
                    if len(result.data) > 5:
                        print(f"  ... and {len(result.data) - 5} more")
                else:
                    print("✗ NO SPECIFICATIONS FOUND for this project")
                print()

                # Check documentation
                print("-" * 80)
                print(f"CHECKING DOCUMENTATION FOR PROJECT: {project_id}")
                print("-" * 80)
                result = client.table("documentation").select("id, document_title, document_type").eq("project_id", project_id).execute()
                if result.data:
                    print(f"✓ Found {len(result.data)} document(s):")
                    for doc in result.data[:5]:
                        print(f"  - {doc.get('document_type')}/{doc.get('document_title')}")
                    if len(result.data) > 5:
                        print(f"  ... and {len(result.data) - 5} more")
                else:
                    print("✗ NO DOCUMENTATION FOUND for this project")
                print()

            else:
                print(f"✗ NO PROJECT FOUND with machine_id: {machine_id}")
                print()

        # Check global resources (not project-specific)
        print("-" * 80)
        print("CHECKING GLOBAL RESOURCES (not project-specific)")
        print("-" * 80)

        # Template tasks
        result = client.table("template_tasks").select("template_id, template_name").limit(5).execute()
        print(f"Template tasks: {len(result.data) if result.data else 0} found")

        # Template sprints
        result = client.table("template_sprints").select("template_id, template_name").limit(5).execute()
        print(f"Template sprints: {len(result.data) if result.data else 0} found")

        print()
        print("=" * 80)
        print("AUDIT COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
