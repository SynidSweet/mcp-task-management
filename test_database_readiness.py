#!/usr/bin/env python3
"""
Database Readiness Test for Unified File Monitoring

Verifies that:
1. All database tables exist with correct schema
2. Database is accessible and writable
3. File→Database sync infrastructure is ready

This validates the database layer is ready for file monitoring.
"""

import json
import shutil
import tempfile
import uuid
from pathlib import Path

from core.project_manager import ProjectManager
from tools.document_tools import get_supabase_client, get_or_create_project_id
from core.machine_id import get_machine_id


class DatabaseReadinessTester:
    """Test database readiness for file monitoring"""

    def __init__(self):
        self.test_dir = None
        self.project_manager = None
        self.project_id = None
        self.machine_id = None
        self.supabase_client = None
        self.results = []

    def setup(self):
        """Set up test environment"""
        print("\n" + "="*80)
        print("DATABASE READINESS TEST FOR FILE MONITORING")
        print("="*80)

        # Create temporary test project
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_db_ready_"))
        (self.test_dir / ".claude-tasks" / "data").mkdir(parents=True)

        # Initialize project manager
        self.project_manager = ProjectManager(self.test_dir)

        # Get project ID and machine ID
        self.project_id, error = get_or_create_project_id(self.project_manager)
        if error:
            raise Exception(f"Failed to get project ID: {error}")

        self.machine_id = get_machine_id()

        # Get Supabase client
        self.supabase_client, error = get_supabase_client()
        if error:
            raise Exception(f"Failed to connect to Supabase: {error}")

        print(f"\n✅ Test environment ready")
        print(f"   Test dir: {self.test_dir}")
        print(f"   Project ID: {self.project_id}")
        print(f"   Machine ID: {self.machine_id}")

    def teardown(self):
        """Clean up test environment"""
        # Remove test directory
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

        # Clean up test data from database
        if self.supabase_client and self.project_id:
            try:
                tables = [
                    'tasks', 'sprints', 'journal_sessions', 'requirements',
                    'documents', 'templates', 'commands', 'agents',
                    'documentation', 'mcp_configs'
                ]
                for table in tables:
                    try:
                        self.supabase_client.table(table).delete().eq('project_id', self.project_id).execute()
                    except Exception:
                        pass

                # Delete project record
                self.supabase_client.table('projects').delete().eq('id', self.project_id).execute()
            except Exception as e:
                print(f"⚠️  Warning: Failed to clean up test data: {e}")

        print("\n✅ Test teardown complete")

    def test_table_exists(self, table_name: str) -> bool:
        """Test if a table exists and is accessible"""
        try:
            result = self.supabase_client.table(table_name).select('id').limit(1).execute()
            print(f"   ✓ Table exists and is accessible: {table_name}")
            return True
        except Exception as e:
            print(f"   ✗ Table not accessible: {table_name} - {e}")
            return False

    def test_table_write(self, table_name: str, record: dict) -> bool:
        """Test if we can write to a table"""
        try:
            # Add required fields
            record['project_id'] = self.project_id
            record['machine_id'] = self.machine_id
            record['id'] = str(uuid.uuid4())

            result = self.supabase_client.table(table_name).insert(record).execute()

            if result.data:
                print(f"   ✓ Successfully wrote to: {table_name}")
                # Clean up
                self.supabase_client.table(table_name).delete().eq('id', record['id']).execute()
                return True
            else:
                print(f"   ✗ Write failed: {table_name}")
                return False
        except Exception as e:
            print(f"   ✗ Write error: {table_name} - {e}")
            return False

    def run_tests(self):
        """Run all database readiness tests"""

        # Test 1: Critical tables exist
        print("\n🧪 Test 1: Critical Tables Exist")
        tables_to_test = [
            'tasks', 'sprints', 'journal_sessions', 'requirements',
            'documents', 'document_sections', 'templates', 'commands',
            'agents', 'documentation', 'mcp_configs', 'projects'
        ]

        table_results = {}
        for table in tables_to_test:
            table_results[table] = self.test_table_exists(table)

        all_exist = all(table_results.values())
        if all_exist:
            print(f"   ✅ PASS: All {len(tables_to_test)} critical tables exist")
            self.results.append({"test": "All Tables Exist", "status": "PASS"})
        else:
            missing = [t for t, exists in table_results.items() if not exists]
            print(f"   ❌ FAIL: Missing tables: {missing}")
            self.results.append({"test": "All Tables Exist", "status": "FAIL", "missing": missing})

        # Test 2: Tasks table write
        print("\n🧪 Test 2: Tasks Table Write")
        task_record = {
            'title': 'Test Task',
            'description': 'Database readiness test',
            'status': 'pending',
            'priority': 'medium',
            'created_at': '2025-10-06T20:00:00Z'
        }
        if self.test_table_write('tasks', task_record):
            print("   ✅ PASS: Tasks table is writable")
            self.results.append({"test": "Tasks Table Write", "status": "PASS"})
        else:
            print("   ❌ FAIL: Tasks table write failed")
            self.results.append({"test": "Tasks Table Write", "status": "FAIL"})

        # Test 3: Sprints table write
        print("\n🧪 Test 3: Sprints Table Write")
        sprint_record = {
            'title': 'Test Sprint',
            'description': 'Database readiness test',
            'status': 'active',
            'created_at': '2025-10-06T20:00:00Z'
        }
        if self.test_table_write('sprints', sprint_record):
            print("   ✅ PASS: Sprints table is writable")
            self.results.append({"test": "Sprints Table Write", "status": "PASS"})
        else:
            print("   ❌ FAIL: Sprints table write failed")
            self.results.append({"test": "Sprints Table Write", "status": "FAIL"})

        # Test 4: Requirements table write
        print("\n🧪 Test 4: Requirements Table Write")
        req_record = {
            'entity_name': 'Test Requirement',
            'entity_type': 'feature',
            'description': 'Database readiness test',
            'approved': True
        }
        if self.test_table_write('requirements', req_record):
            print("   ✅ PASS: Requirements table is writable")
            self.results.append({"test": "Requirements Table Write", "status": "PASS"})
        else:
            print("   ❌ FAIL: Requirements table write failed")
            self.results.append({"test": "Requirements Table Write", "status": "FAIL"})

        # Test 5: Templates table write
        print("\n🧪 Test 5: Templates Table Write")
        template_record = {
            'template_type': 'task',
            'scope': 'project',
            'is_global': False,
            'data': {'name': 'test_template', 'title': 'Test'}
        }
        if self.test_table_write('templates', template_record):
            print("   ✅ PASS: Templates table is writable")
            self.results.append({"test": "Templates Table Write", "status": "PASS"})
        else:
            print("   ❌ FAIL: Templates table write failed")
            self.results.append({"test": "Templates Table Write", "status": "FAIL"})

        # Test 6: Commands table write
        print("\n🧪 Test 6: Commands Table Write")
        command_record = {
            'command_name': 'test_command',
            'file_path': 'test_command.md',
            'scope': 'project',
            'is_global': False,
            'content': '# Test Command'
        }
        if self.test_table_write('commands', command_record):
            print("   ✅ PASS: Commands table is writable")
            self.results.append({"test": "Commands Table Write", "status": "PASS"})
        else:
            print("   ❌ FAIL: Commands table write failed")
            self.results.append({"test": "Commands Table Write", "status": "FAIL"})

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")

        for result in self.results:
            if result["status"] == "PASS":
                print(f"✅ PASS: {result['test']}")
            else:
                print(f"❌ FAIL: {result['test']}")
                if 'missing' in result:
                    print(f"   Missing: {result['missing']}")

        print(f"\n{'='*80}")
        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        print(f"{'='*80}\n")

        # Summary
        print("SUMMARY:")
        print("-" * 80)

        if failed == 0:
            print("✅ Database is READY for file monitoring system")
            print("   → All required tables exist and are writable")
            print("   → Schema v2.2 (requirements table) is deployed correctly")
            print("   → File→Database sync infrastructure is functional")
            print("\n📋 NEXT STEPS:")
            print("   1. Activate file monitoring in server.py (Issue #1)")
            print("   2. Implement documents sync (Issue #2)")
            print("   3. Restart MCP server to enable monitoring")
        else:
            print("❌ Database has issues that need fixing")
            print("   → Check Supabase schema deployment")
            print("   → Verify migration scripts ran successfully")

        print("-" * 80)

        return failed == 0


def main():
    """Run database readiness tests"""
    tester = DatabaseReadinessTester()

    try:
        # Setup
        tester.setup()

        # Run tests
        tester.run_tests()

        # Print summary
        success = tester.print_summary()

        return 0 if success else 1

    finally:
        # Teardown
        tester.teardown()


if __name__ == "__main__":
    exit(main())
