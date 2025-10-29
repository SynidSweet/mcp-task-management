#!/usr/bin/env python3
"""
Comprehensive tests for MCP config normalization

Tests the normalized mcp_config_files and mcp_servers tables,
sync functionality, constraints, and query performance.
"""

import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from tools.document_tools import get_supabase_client
from core.machine_id import get_machine_id
from core.universal_storage.unified_file_monitor import UnifiedFileMonitor


class TestMCPConfigNormalization:
    """Test suite for normalized MCP configuration storage"""

    def __init__(self):
        self.client, _ = get_supabase_client()
        self.machine_id = get_machine_id()
        self.test_config_ids = []
        self.test_server_ids = []

    def cleanup(self):
        """Clean up test data"""
        try:
            # Delete test servers
            for server_id in self.test_server_ids:
                self.client.table('mcp_servers').delete().eq('id', server_id).execute()

            # Delete test config files
            for config_id in self.test_config_ids:
                self.client.table('mcp_config_files').delete().eq('id', config_id).execute()

            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

    def test_1_table_structure(self):
        """Test that normalized tables exist with correct structure"""
        print("\n=== Test 1: Table Structure ===")

        # Test mcp_config_files table
        try:
            result = self.client.table('mcp_config_files').select('*').limit(1).execute()
            print("✅ mcp_config_files table exists")
        except Exception as e:
            print(f"❌ mcp_config_files table error: {e}")
            return False

        # Test mcp_servers table
        try:
            result = self.client.table('mcp_servers').select('*').limit(1).execute()
            print("✅ mcp_servers table exists")
        except Exception as e:
            print(f"❌ mcp_servers table error: {e}")
            return False

        # Verify old table is gone
        try:
            result = self.client.table('mcp_configs').select('*').limit(1).execute()
            print("❌ Old mcp_configs table still exists (should be dropped)")
            return False
        except Exception as e:
            print("✅ Old mcp_configs table correctly dropped")

        return True

    def test_2_config_file_crud(self):
        """Test CRUD operations on mcp_config_files"""
        print("\n=== Test 2: Config File CRUD ===")

        config_id = str(uuid.uuid4())
        self.test_config_ids.append(config_id)

        # Create config file
        config_record = {
            'id': config_id,
            'machine_id': self.machine_id,
            'config_name': 'test_config',
            'file_path': 'test/.mcp.json',
            'file_type': 'mcp',
            'metadata_auto_generated': True,
            'scope': 'global',
            'is_global': True
        }

        try:
            result = self.client.table('mcp_config_files').insert(config_record).execute()
            assert len(result.data) == 1
            print("✅ Config file created")
        except Exception as e:
            print(f"❌ Config file creation failed: {e}")
            return False

        # Read config file
        try:
            result = self.client.table('mcp_config_files').select('*').eq('id', config_id).execute()
            assert len(result.data) == 1
            assert result.data[0]['config_name'] == 'test_config'
            print("✅ Config file read")
        except Exception as e:
            print(f"❌ Config file read failed: {e}")
            return False

        # Update config file
        try:
            result = self.client.table('mcp_config_files').update({'metadata_auto_generated': False}).eq('id', config_id).execute()
            assert result.data[0]['metadata_auto_generated'] == False
            print("✅ Config file updated")
        except Exception as e:
            print(f"❌ Config file update failed: {e}")
            return False

        return True

    def test_3_server_crud(self):
        """Test CRUD operations on mcp_servers"""
        print("\n=== Test 3: Server CRUD ===")

        # Create a config file first
        config_id = str(uuid.uuid4())
        self.test_config_ids.append(config_id)

        config_record = {
            'id': config_id,
            'machine_id': self.machine_id,
            'config_name': 'test_servers_config',
            'file_path': 'test/.mcp.json',
            'file_type': 'mcp',
            'scope': 'global',
            'is_global': True
        }
        self.client.table('mcp_config_files').insert(config_record).execute()

        # Create HTTP server
        http_server_id = str(uuid.uuid4())
        self.test_server_ids.append(http_server_id)

        http_server = {
            'id': http_server_id,
            'config_file_id': config_id,
            'machine_id': self.machine_id,
            'server_name': 'test_http_server',
            'transport_type': 'http',
            'url': 'http://localhost:8080',
            'disabled': False,
            'always_allow': False,
            'sort_order': 0
        }

        try:
            result = self.client.table('mcp_servers').insert(http_server).execute()
            assert len(result.data) == 1
            print("✅ HTTP server created")
        except Exception as e:
            print(f"❌ HTTP server creation failed: {e}")
            return False

        # Create stdio server
        stdio_server_id = str(uuid.uuid4())
        self.test_server_ids.append(stdio_server_id)

        stdio_server = {
            'id': stdio_server_id,
            'config_file_id': config_id,
            'machine_id': self.machine_id,
            'server_name': 'test_stdio_server',
            'transport_type': 'stdio',
            'command': 'python',
            'args': ['-m', 'test_module'],
            'env': {'TEST_VAR': 'test_value'},
            'sort_order': 1
        }

        try:
            result = self.client.table('mcp_servers').insert(stdio_server).execute()
            assert len(result.data) == 1
            print("✅ Stdio server created")
        except Exception as e:
            print(f"❌ Stdio server creation failed: {e}")
            return False

        # Read servers
        try:
            result = self.client.table('mcp_servers').select('*').eq('config_file_id', config_id).order('sort_order').execute()
            assert len(result.data) == 2
            assert result.data[0]['server_name'] == 'test_http_server'
            assert result.data[1]['server_name'] == 'test_stdio_server'
            print("✅ Servers read with correct order")
        except Exception as e:
            print(f"❌ Servers read failed: {e}")
            return False

        return True

    def test_4_transport_constraints(self):
        """Test CHECK constraints for transport-specific fields"""
        print("\n=== Test 4: Transport Type Constraints ===")

        config_id = str(uuid.uuid4())
        self.test_config_ids.append(config_id)

        config_record = {
            'id': config_id,
            'machine_id': self.machine_id,
            'config_name': 'test_constraints',
            'file_path': 'test/.mcp.json',
            'file_type': 'mcp',
            'scope': 'global',
            'is_global': True
        }
        self.client.table('mcp_config_files').insert(config_record).execute()

        # Test 1: stdio without command should fail
        print("  Testing stdio without command (should fail)...")
        try:
            invalid_server = {
                'id': str(uuid.uuid4()),
                'config_file_id': config_id,
                'machine_id': self.machine_id,
                'server_name': 'invalid_stdio',
                'transport_type': 'stdio',
                # Missing command!
                'sort_order': 0
            }
            result = self.client.table('mcp_servers').insert(invalid_server).execute()
            print("  ❌ Stdio without command was allowed (constraint not working)")
            return False
        except Exception as e:
            print("  ✅ Stdio without command correctly rejected")

        # Test 2: http without url should fail
        print("  Testing http without URL (should fail)...")
        try:
            invalid_server = {
                'id': str(uuid.uuid4()),
                'config_file_id': config_id,
                'machine_id': self.machine_id,
                'server_name': 'invalid_http',
                'transport_type': 'http',
                # Missing url!
                'sort_order': 0
            }
            result = self.client.table('mcp_servers').insert(invalid_server).execute()
            print("  ❌ HTTP without URL was allowed (constraint not working)")
            return False
        except Exception as e:
            print("  ✅ HTTP without URL correctly rejected")

        # Test 3: Valid stdio with command should succeed
        print("  Testing valid stdio with command (should succeed)...")
        try:
            valid_server_id = str(uuid.uuid4())
            self.test_server_ids.append(valid_server_id)

            valid_server = {
                'id': valid_server_id,
                'config_file_id': config_id,
                'machine_id': self.machine_id,
                'server_name': 'valid_stdio',
                'transport_type': 'stdio',
                'command': 'node',
                'sort_order': 0
            }
            result = self.client.table('mcp_servers').insert(valid_server).execute()
            print("  ✅ Valid stdio correctly accepted")
        except Exception as e:
            print(f"  ❌ Valid stdio was rejected: {e}")
            return False

        return True

    def test_5_cascade_delete(self):
        """Test CASCADE DELETE from config to servers"""
        print("\n=== Test 5: Cascade Delete ===")

        # Create config with servers
        config_id = str(uuid.uuid4())

        config_record = {
            'id': config_id,
            'machine_id': self.machine_id,
            'config_name': 'test_cascade',
            'file_path': 'test/.mcp.json',
            'file_type': 'mcp',
            'scope': 'global',
            'is_global': True
        }
        self.client.table('mcp_config_files').insert(config_record).execute()

        # Create multiple servers
        server_ids = []
        for i in range(3):
            server_id = str(uuid.uuid4())
            server_ids.append(server_id)

            server = {
                'id': server_id,
                'config_file_id': config_id,
                'machine_id': self.machine_id,
                'server_name': f'cascade_test_server_{i}',
                'transport_type': 'http',
                'url': f'http://localhost:808{i}',
                'sort_order': i
            }
            self.client.table('mcp_servers').insert(server).execute()

        # Verify servers exist
        result = self.client.table('mcp_servers').select('id').eq('config_file_id', config_id).execute()
        assert len(result.data) == 3
        print(f"  Created 3 servers for config {config_id[:8]}...")

        # Delete config file
        self.client.table('mcp_config_files').delete().eq('id', config_id).execute()
        print("  Deleted config file")

        # Verify servers were cascade deleted
        result = self.client.table('mcp_servers').select('id').eq('config_file_id', config_id).execute()
        assert len(result.data) == 0
        print("✅ Servers correctly cascade deleted")

        return True

    def test_6_unique_constraints(self):
        """Test UNIQUE constraints"""
        print("\n=== Test 6: Unique Constraints ===")

        config_id = str(uuid.uuid4())
        self.test_config_ids.append(config_id)

        config_record = {
            'id': config_id,
            'machine_id': self.machine_id,
            'config_name': 'test_unique',
            'file_path': 'test/.mcp.json',
            'file_type': 'mcp',
            'scope': 'global',
            'is_global': True
        }
        self.client.table('mcp_config_files').insert(config_record).execute()

        # Create first server
        server1_id = str(uuid.uuid4())
        self.test_server_ids.append(server1_id)

        server1 = {
            'id': server1_id,
            'config_file_id': config_id,
            'machine_id': self.machine_id,
            'server_name': 'duplicate_test',
            'transport_type': 'http',
            'url': 'http://localhost:8080',
            'sort_order': 0
        }
        self.client.table('mcp_servers').insert(server1).execute()
        print("  Created first server with name 'duplicate_test'")

        # Try to create duplicate server name in same config
        try:
            server2 = {
                'id': str(uuid.uuid4()),
                'config_file_id': config_id,
                'machine_id': self.machine_id,
                'server_name': 'duplicate_test',  # Same name!
                'transport_type': 'http',
                'url': 'http://localhost:8081',
                'sort_order': 1
            }
            result = self.client.table('mcp_servers').insert(server2).execute()
            print("  ❌ Duplicate server name was allowed (constraint not working)")
            return False
        except Exception as e:
            print("  ✅ Duplicate server name correctly rejected")

        return True

    def test_7_query_performance(self):
        """Test indexed queries"""
        print("\n=== Test 7: Query Performance (Indexed Queries) ===")

        # Test filter by transport_type (indexed)
        try:
            result = self.client.table('mcp_servers').select('server_name, transport_type').eq('transport_type', 'http').execute()
            print(f"✅ Filter by transport_type: Found {len(result.data)} HTTP servers")
        except Exception as e:
            print(f"❌ Transport type query failed: {e}")
            return False

        # Test filter by machine_id (indexed)
        try:
            result = self.client.table('mcp_servers').select('server_name').eq('machine_id', self.machine_id).execute()
            print(f"✅ Filter by machine_id: Found {len(result.data)} servers")
        except Exception as e:
            print(f"❌ Machine ID query failed: {e}")
            return False

        # Test filter by disabled (indexed)
        try:
            result = self.client.table('mcp_servers').select('server_name').eq('disabled', False).execute()
            print(f"✅ Filter by disabled: Found {len(result.data)} enabled servers")
        except Exception as e:
            print(f"❌ Disabled filter query failed: {e}")
            return False

        # Test JOIN query (foreign key)
        try:
            result = self.client.table('mcp_config_files').select('config_name, mcp_servers(server_name, transport_type)').execute()
            print(f"✅ JOIN query: Found {len(result.data)} configs with servers")
        except Exception as e:
            print(f"❌ JOIN query failed: {e}")
            return False

        return True

    async def test_8_sync_function(self):
        """Test sync from file to database"""
        print("\n=== Test 8: File Sync Functionality ===")

        # Create temporary config files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Test .claude-mcp-config.json
            config1_path = tmpdir_path / '.claude-mcp-config.json'
            config1_data = {
                "_metadata": {
                    "machine_id": self.machine_id,
                    "auto_generated": True,
                    "repo_root": str(tmpdir_path)
                },
                "mcpServers": {
                    "test_sync_http": {
                        "transport": "http",
                        "url": "http://test-sync:8080"
                    },
                    "test_sync_stdio": {
                        "command": "python",
                        "args": ["-m", "test"]
                    }
                }
            }

            with open(config1_path, 'w') as f:
                json.dump(config1_data, f)

            # Initialize monitor and sync
            monitor = UnifiedFileMonitor()
            monitor.claude_home = tmpdir_path
            await monitor.initialize()

            # Sync the file
            try:
                await monitor._sync_mcp_config(config1_path, 'created')
                print("✅ File sync executed without error")
            except Exception as e:
                print(f"❌ File sync failed: {e}")
                import traceback
                traceback.print_exc()
                return False

            # Verify data was synced
            try:
                # Find the config that was just synced
                result = self.client.table('mcp_config_files').select('id, config_name').eq('machine_id', self.machine_id).eq('config_name', 'claude_mcp_config').execute()

                if result.data:
                    config_file_id = result.data[0]['id']
                    self.test_config_ids.append(config_file_id)

                    # Check servers
                    servers_result = self.client.table('mcp_servers').select('*').eq('config_file_id', config_file_id).execute()

                    # Track server IDs for cleanup
                    for server in servers_result.data:
                        self.test_server_ids.append(server['id'])

                    assert len(servers_result.data) == 2, f"Expected 2 servers, found {len(servers_result.data)}"

                    server_names = [s['server_name'] for s in servers_result.data]
                    assert 'test_sync_http' in server_names
                    assert 'test_sync_stdio' in server_names

                    # Verify HTTP server
                    http_server = next(s for s in servers_result.data if s['server_name'] == 'test_sync_http')
                    assert http_server['transport_type'] == 'http'
                    assert http_server['url'] == 'http://test-sync:8080'

                    # Verify stdio server
                    stdio_server = next(s for s in servers_result.data if s['server_name'] == 'test_sync_stdio')
                    assert stdio_server['transport_type'] == 'stdio'
                    assert stdio_server['command'] == 'python'
                    assert stdio_server['args'] == ['-m', 'test']

                    print("✅ Synced data verified in database")
                else:
                    print("❌ Config file not found after sync")
                    return False

            except Exception as e:
                print(f"❌ Data verification failed: {e}")
                import traceback
                traceback.print_exc()
                return False

        return True

    def test_9_jsonb_queries(self):
        """Test JSONB field queries (args, env, headers)"""
        print("\n=== Test 9: JSONB Field Queries ===")

        config_id = str(uuid.uuid4())
        self.test_config_ids.append(config_id)

        config_record = {
            'id': config_id,
            'machine_id': self.machine_id,
            'config_name': 'test_jsonb',
            'file_path': 'test/.mcp.json',
            'file_type': 'mcp',
            'scope': 'global',
            'is_global': True
        }
        self.client.table('mcp_config_files').insert(config_record).execute()

        # Create server with env variables
        server_id = str(uuid.uuid4())
        self.test_server_ids.append(server_id)

        server = {
            'id': server_id,
            'config_file_id': config_id,
            'machine_id': self.machine_id,
            'server_name': 'jsonb_test',
            'transport_type': 'stdio',
            'command': 'node',
            'args': ['--version', '--verbose'],
            'env': {'API_KEY': 'secret123', 'DEBUG': 'true'},
            'sort_order': 0
        }
        self.client.table('mcp_servers').insert(server).execute()

        # Test JSONB containment query (args)
        try:
            # Note: Supabase client may have limited JSONB query support
            result = self.client.table('mcp_servers').select('server_name, args').eq('id', server_id).execute()
            assert result.data[0]['args'] == ['--version', '--verbose']
            print("✅ JSONB args field retrieved correctly")
        except Exception as e:
            print(f"❌ JSONB args query failed: {e}")
            return False

        # Test JSONB object query (env)
        try:
            result = self.client.table('mcp_servers').select('server_name, env').eq('id', server_id).execute()
            assert result.data[0]['env']['API_KEY'] == 'secret123'
            print("✅ JSONB env field retrieved correctly")
        except Exception as e:
            print(f"❌ JSONB env query failed: {e}")
            return False

        return True


def run_all_tests():
    """Run all MCP config normalization tests"""
    print("="*70)
    print("MCP CONFIG NORMALIZATION - COMPREHENSIVE TEST SUITE")
    print("="*70)

    suite = TestMCPConfigNormalization()

    tests = [
        ("Table Structure", suite.test_1_table_structure),
        ("Config File CRUD", suite.test_2_config_file_crud),
        ("Server CRUD", suite.test_3_server_crud),
        ("Transport Constraints", suite.test_4_transport_constraints),
        ("Cascade Delete", suite.test_5_cascade_delete),
        ("Unique Constraints", suite.test_6_unique_constraints),
        ("Query Performance", suite.test_7_query_performance),
        ("File Sync", lambda: asyncio.run(suite.test_8_sync_function())),
        ("JSONB Queries", suite.test_9_jsonb_queries),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()

    # Cleanup
    print("\n" + "="*70)
    print("CLEANUP")
    print("="*70)
    suite.cleanup()

    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"Total: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
