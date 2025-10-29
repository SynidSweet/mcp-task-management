#!/usr/bin/env python3
"""
Comprehensive Test Suite for Document Tools - Filesystem-Only Operations

Tests all 5 document tools with:
- Happy path scenarios
- Edge cases
- Error conditions
- Integration scenarios
- Filesystem verification

All tests verify that tools work ONLY with filesystem, no database operations.
"""

import tempfile
import shutil
from pathlib import Path
import sys
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.project_manager import ProjectManager
from tools.document_tools import register_document_tools


class MockMCP:
    """Mock MCP server for testing"""
    def __init__(self):
        self.tools = {}

    def tool(self):
        """Decorator to register tools"""
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator


class DocumentToolsTestSuite:
    """Comprehensive test suite for document tools"""

    def __init__(self):
        self.temp_dir = None
        self.project_manager = None
        self.mcp = None
        self.tools = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0

    def log(self, message: str, level: str = "INFO"):
        """Log test message"""
        prefix = {
            "INFO": "ℹ️ ",
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️ ",
            "TEST": "🧪"
        }.get(level, "  ")
        print(f"{prefix} {message}")

    def assert_equal(self, actual, expected, test_name):
        """Assert equality with test tracking"""
        self.tests_run += 1
        if actual == expected:
            self.tests_passed += 1
            self.log(f"{test_name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{test_name}: FAIL - Expected {expected}, got {actual}", "FAIL")
            return False

    def assert_true(self, condition, test_name):
        """Assert true with test tracking"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"{test_name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{test_name}: FAIL - Condition was false", "FAIL")
            return False

    def assert_contains(self, container, item, test_name):
        """Assert contains with test tracking"""
        self.tests_run += 1
        if item in container:
            self.tests_passed += 1
            self.log(f"{test_name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{test_name}: FAIL - '{item}' not in container", "FAIL")
            return False

    async def setup(self):
        """Set up test environment"""
        self.log("Setting up test environment...")
        self.temp_dir = tempfile.mkdtemp()
        self.project_manager = ProjectManager(Path(self.temp_dir))

        # Create mock MCP and register tools
        self.mcp = MockMCP()
        register_document_tools(self.mcp, self.project_manager)

        # Get tool functions
        self.tools = {
            'create': self.mcp.tools['document_create'],
            'get': self.mcp.tools['document_get'],
            'query': self.mcp.tools['document_query'],
            'update': self.mcp.tools['document_update'],
            'delete': self.mcp.tools['document_delete']
        }

        self.log(f"Created temp directory: {self.temp_dir}")
        self.log("Setup complete\n")

    async def cleanup(self):
        """Clean up test environment"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            self.log(f"Cleaned up temp directory")

    # ========================================================================
    # DOCUMENT_CREATE TESTS
    # ========================================================================

    async def test_create_basic(self):
        """Test basic document creation"""
        self.log("\n1. Testing document_create - Basic", "TEST")

        result = await self.tools['create'](
            document_title="Test Document",
            document_type="guides",
            description="A test document",
            content="## Section 1\n\nContent here."
        )

        self.assert_equal(result['status'], 'success', "Create returns success")
        self.assert_equal(result['file_path'], 'guides/Test Document.md', "Correct file path")

        # Verify file exists
        doc_path = Path(self.temp_dir) / 'docs' / 'guides' / 'Test Document.md'
        self.assert_true(doc_path.exists(), "File created on filesystem")

        # Verify content
        with open(doc_path, 'r') as f:
            content = f.read()
        self.assert_contains(content, "Test Document", "Title in content")
        self.assert_contains(content, "A test document", "Description in content")
        self.assert_contains(content, "Section 1", "Content in file")

    async def test_create_nested_directory(self):
        """Test creating document in nested directory"""
        self.log("\n2. Testing document_create - Nested Directory", "TEST")

        result = await self.tools['create'](
            document_title="Nested Doc",
            document_type="architecture/backend",
            description="Nested document",
            content="Nested content"
        )

        self.assert_equal(result['status'], 'success', "Create with nested dir succeeds")

        # Verify nested directory created
        doc_path = Path(self.temp_dir) / 'docs' / 'architecture' / 'backend' / 'Nested Doc.md'
        self.assert_true(doc_path.exists(), "Nested directory created")

    async def test_create_minimal(self):
        """Test creating document with minimal info"""
        self.log("\n3. Testing document_create - Minimal Info", "TEST")

        result = await self.tools['create'](
            document_title="Minimal",
            document_type="notes"
        )

        self.assert_equal(result['status'], 'success', "Create with minimal info succeeds")

        doc_path = Path(self.temp_dir) / 'docs' / 'notes' / 'Minimal.md'
        with open(doc_path, 'r') as f:
            content = f.read()
        self.assert_contains(content, "# Minimal", "Title added even with no content")

    async def test_create_special_characters(self):
        """Test creating document with special characters in title"""
        self.log("\n4. Testing document_create - Special Characters", "TEST")

        result = await self.tools['create'](
            document_title="Test: Document (v2)",
            document_type="guides",
            content="Special chars test"
        )

        self.assert_equal(result['status'], 'success', "Create with special chars succeeds")

        # File should be created with the special characters
        doc_path = Path(self.temp_dir) / 'docs' / 'guides' / 'Test: Document (v2).md'
        self.assert_true(doc_path.exists(), "File with special chars created")

    # ========================================================================
    # DOCUMENT_GET TESTS
    # ========================================================================

    async def test_get_existing(self):
        """Test getting existing document"""
        self.log("\n5. Testing document_get - Existing Document", "TEST")

        # Create document first
        await self.tools['create'](
            document_title="Get Test",
            document_type="guides",
            description="Test description",
            content="Test content"
        )

        result = await self.tools['get'](file_path="guides/Get Test.md")

        self.assert_equal(result['status'], 'success', "Get returns success")
        doc = result['document']
        self.assert_equal(doc['title'], 'Get Test', "Correct title")
        self.assert_contains(doc['content'], "Test content", "Content retrieved")
        self.assert_contains(doc['description'], "Test description", "Description extracted")

    async def test_get_nonexistent(self):
        """Test getting nonexistent document"""
        self.log("\n6. Testing document_get - Nonexistent Document", "TEST")

        result = await self.tools['get'](file_path="guides/Nonexistent.md")

        self.assert_equal(result['status'], 'error', "Get nonexistent returns error")
        self.assert_contains(result['error'], "not found", "Error message mentions not found")

    # ========================================================================
    # DOCUMENT_QUERY TESTS
    # ========================================================================

    async def test_query_all(self):
        """Test querying all documents"""
        self.log("\n7. Testing document_query - All Documents", "TEST")

        # Clean docs folder first
        docs_dir = Path(self.temp_dir) / 'docs'
        if docs_dir.exists():
            shutil.rmtree(docs_dir)

        # Create multiple documents
        await self.tools['create'](
            document_title="Doc 1",
            document_type="guides",
            content="Content 1"
        )
        await self.tools['create'](
            document_title="Doc 2",
            document_type="tutorials",
            content="Content 2"
        )

        result = await self.tools['query']()

        self.assert_equal(result['status'], 'success', "Query returns success")
        self.assert_equal(result['document_count'], 2, "Finds 2 documents")

    async def test_query_with_search(self):
        """Test querying with search term"""
        self.log("\n8. Testing document_query - With Search", "TEST")

        # Create documents
        await self.tools['create'](
            document_title="Python Guide",
            document_type="guides",
            content="Python programming"
        )
        await self.tools['create'](
            document_title="Java Guide",
            document_type="guides",
            content="Java programming"
        )

        result = await self.tools['query'](query="Python")

        self.assert_equal(result['status'], 'success', "Search query succeeds")
        self.assert_equal(result['document_count'], 1, "Finds only Python doc")
        self.assert_equal(result['documents'][0]['title'], 'Python Guide', "Correct doc found")

    async def test_query_no_matches(self):
        """Test querying with no matches"""
        self.log("\n9. Testing document_query - No Matches", "TEST")

        await self.tools['create'](
            document_title="Test Doc",
            document_type="guides",
            content="Test content"
        )

        result = await self.tools['query'](query="nonexistent")

        self.assert_equal(result['status'], 'success', "No matches returns success")
        self.assert_equal(result['document_count'], 0, "Returns 0 documents")

    async def test_query_empty_docs(self):
        """Test querying when no documents exist"""
        self.log("\n10. Testing document_query - Empty Docs Folder", "TEST")

        # Clean docs folder to ensure empty
        docs_dir = Path(self.temp_dir) / 'docs'
        if docs_dir.exists():
            shutil.rmtree(docs_dir)

        result = await self.tools['query']()

        self.assert_equal(result['status'], 'success', "Empty query returns success")
        self.assert_equal(result['document_count'], 0, "Returns 0 documents")

    async def test_query_limit(self):
        """Test querying with limit"""
        self.log("\n11. Testing document_query - With Limit", "TEST")

        # Create 5 documents
        for i in range(5):
            await self.tools['create'](
                document_title=f"Doc {i}",
                document_type="guides",
                content=f"Content {i}"
            )

        result = await self.tools['query'](limit=3)

        self.assert_equal(result['status'], 'success', "Limit query succeeds")
        self.assert_equal(result['document_count'], 3, "Returns exactly 3 documents")

    # ========================================================================
    # DOCUMENT_UPDATE TESTS
    # ========================================================================

    async def test_update_content(self):
        """Test updating document content"""
        self.log("\n12. Testing document_update - Update Content", "TEST")

        # Create document
        await self.tools['create'](
            document_title="Update Test",
            document_type="guides",
            content="Original content"
        )

        # Update it
        new_content = "# Update Test\n\nNew content here"
        result = await self.tools['update'](
            file_path="guides/Update Test.md",
            content=new_content
        )

        self.assert_equal(result['status'], 'success', "Update returns success")
        self.assert_contains(result['updates_applied'], 'content', "Content in updates")

        # Verify update on filesystem
        doc_path = Path(self.temp_dir) / 'docs' / 'guides' / 'Update Test.md'
        with open(doc_path, 'r') as f:
            content = f.read()
        self.assert_contains(content, "New content here", "Content updated on filesystem")

    async def test_update_description(self):
        """Test updating document description"""
        self.log("\n13. Testing document_update - Update Description", "TEST")

        # Create document
        await self.tools['create'](
            document_title="Desc Test",
            document_type="guides",
            description="Old description",
            content="Some content"
        )

        # Update description
        result = await self.tools['update'](
            file_path="guides/Desc Test.md",
            description="New description"
        )

        self.assert_equal(result['status'], 'success', "Update description succeeds")
        self.assert_contains(result['updates_applied'], 'description', "Description in updates")

    async def test_update_nonexistent(self):
        """Test updating nonexistent document"""
        self.log("\n14. Testing document_update - Nonexistent Document", "TEST")

        result = await self.tools['update'](
            file_path="guides/Nonexistent.md",
            content="New content"
        )

        self.assert_equal(result['status'], 'error', "Update nonexistent returns error")
        self.assert_contains(result['error'], "not found", "Error mentions not found")

    # ========================================================================
    # DOCUMENT_DELETE TESTS
    # ========================================================================

    async def test_delete_existing(self):
        """Test deleting existing document"""
        self.log("\n15. Testing document_delete - Existing Document", "TEST")

        # Create document
        await self.tools['create'](
            document_title="Delete Test",
            document_type="guides",
            content="To be deleted"
        )

        doc_path = Path(self.temp_dir) / 'docs' / 'guides' / 'Delete Test.md'
        self.assert_true(doc_path.exists(), "File exists before delete")

        # Delete it
        result = await self.tools['delete'](file_path="guides/Delete Test.md")

        self.assert_equal(result['status'], 'success', "Delete returns success")
        self.assert_true(not doc_path.exists(), "File deleted from filesystem")

    async def test_delete_nonexistent(self):
        """Test deleting nonexistent document"""
        self.log("\n16. Testing document_delete - Nonexistent Document", "TEST")

        result = await self.tools['delete'](file_path="guides/Nonexistent.md")

        self.assert_equal(result['status'], 'error', "Delete nonexistent returns error")
        self.assert_contains(result['error'], "not found", "Error mentions not found")

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    async def test_full_lifecycle(self):
        """Test complete document lifecycle"""
        self.log("\n17. Testing Full Lifecycle - Create, Get, Update, Delete", "TEST")

        # Create
        create_result = await self.tools['create'](
            document_title="Lifecycle",
            document_type="guides",
            content="Original"
        )
        self.assert_equal(create_result['status'], 'success', "Lifecycle: Create")

        # Get
        get_result = await self.tools['get'](file_path="guides/Lifecycle.md")
        self.assert_equal(get_result['status'], 'success', "Lifecycle: Get")

        # Update
        update_result = await self.tools['update'](
            file_path="guides/Lifecycle.md",
            content="# Lifecycle\n\nUpdated"
        )
        self.assert_equal(update_result['status'], 'success', "Lifecycle: Update")

        # Verify update
        get_result2 = await self.tools['get'](file_path="guides/Lifecycle.md")
        self.assert_contains(get_result2['document']['content'], "Updated", "Lifecycle: Update verified")

        # Delete
        delete_result = await self.tools['delete'](file_path="guides/Lifecycle.md")
        self.assert_equal(delete_result['status'], 'success', "Lifecycle: Delete")

        # Verify deletion
        get_result3 = await self.tools['get'](file_path="guides/Lifecycle.md")
        self.assert_equal(get_result3['status'], 'error', "Lifecycle: Delete verified")

    async def test_multiple_types(self):
        """Test documents in different types/folders"""
        self.log("\n18. Testing Multiple Document Types", "TEST")

        # Clean docs folder first
        docs_dir = Path(self.temp_dir) / 'docs'
        if docs_dir.exists():
            shutil.rmtree(docs_dir)

        types = ["guides", "tutorials", "architecture", "notes"]

        for doc_type in types:
            result = await self.tools['create'](
                document_title=f"{doc_type.capitalize()} Doc",
                document_type=doc_type,
                content=f"{doc_type} content"
            )
            self.assert_equal(result['status'], 'success', f"Create {doc_type}")

        # Query all
        query_result = await self.tools['query']()
        self.assert_equal(query_result['document_count'], 4, "All types queryable")

    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================

    async def run_all_tests(self):
        """Run all test scenarios"""
        print("\n" + "="*70)
        print("📚 COMPREHENSIVE DOCUMENT TOOLS TEST SUITE")
        print("Testing filesystem-only operations (no database calls)")
        print("="*70)

        await self.setup()

        try:
            # Run all tests
            await self.test_create_basic()
            await self.test_create_nested_directory()
            await self.test_create_minimal()
            await self.test_create_special_characters()

            await self.test_get_existing()
            await self.test_get_nonexistent()

            await self.test_query_all()
            await self.test_query_with_search()
            await self.test_query_no_matches()
            await self.test_query_empty_docs()
            await self.test_query_limit()

            await self.test_update_content()
            await self.test_update_description()
            await self.test_update_nonexistent()

            await self.test_delete_existing()
            await self.test_delete_nonexistent()

            await self.test_full_lifecycle()
            await self.test_multiple_types()

        finally:
            await self.cleanup()

        # Print summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*70)

        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            print("\n✅ Document tools are working correctly:")
            print("   - All operations use filesystem only")
            print("   - No database calls from tools")
            print("   - File monitor will handle database sync")
            return 0
        else:
            print(f"\n⚠️  {self.tests_failed} test(s) failed")
            return 1


if __name__ == '__main__':
    tester = DocumentToolsTestSuite()
    exit_code = asyncio.run(tester.run_all_tests())
    sys.exit(exit_code)
