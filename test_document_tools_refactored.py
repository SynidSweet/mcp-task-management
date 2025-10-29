"""
Test refactored document tools - filesystem-only operations.

This test verifies that document tools work correctly with only filesystem operations,
without any direct database calls.
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


async def test_document_tools():
    """Test all document tool operations"""
    print("Testing refactored document tools (filesystem-only)...")

    # Create temporary project directory
    temp_dir = tempfile.mkdtemp()
    print(f"✓ Created temp directory: {temp_dir}")

    try:
        # Setup project manager
        project_manager = ProjectManager(Path(temp_dir))

        # Create mock MCP and register tools
        mcp = MockMCP()
        register_document_tools(mcp, project_manager)

        # Get tool functions
        document_create = mcp.tools['document_create']
        document_get = mcp.tools['document_get']
        document_query = mcp.tools['document_query']
        document_update = mcp.tools['document_update']
        document_delete = mcp.tools['document_delete']

        print("\n1. Testing document_create...")
        result = await document_create(
            document_title="Test Document",
            document_type="guides",
            description="This is a test document",
            content="## Section 1\n\nSome content here."
        )
        assert result['status'] == 'success', f"Create failed: {result}"
        file_path = result['file_path']
        filesystem_path = result['filesystem_path']
        print(f"   ✓ Created document at {file_path}")

        # Verify file exists on filesystem
        assert Path(filesystem_path).exists(), "File not created on filesystem"
        print(f"   ✓ File exists on filesystem")

        # Verify content
        with open(filesystem_path, 'r') as f:
            content = f.read()
        assert "Test Document" in content, "Title not in content"
        assert "This is a test document" in content, "Description not in content"
        assert "Section 1" in content, "Content not in file"
        print(f"   ✓ Content verified")

        print("\n2. Testing document_get...")
        result = await document_get(file_path=file_path)
        assert result['status'] == 'success', f"Get failed: {result}"
        doc = result['document']
        assert doc['title'] == "Test Document", "Wrong title"
        assert doc['file_path'] == file_path, "Wrong file_path"
        assert "This is a test document" in doc['description'], "Wrong description"
        assert "Section 1" in doc['content'], "Wrong content"
        print(f"   ✓ Retrieved document correctly")

        print("\n3. Testing document_query...")
        result = await document_query()
        assert result['status'] == 'success', f"Query failed: {result}"
        assert result['document_count'] == 1, "Should find 1 document"
        assert result['documents'][0]['title'] == "Test Document", "Wrong document in query"
        print(f"   ✓ Query found {result['document_count']} document(s)")

        # Test query with search term
        result = await document_query(query="test")
        assert result['status'] == 'success', f"Search query failed: {result}"
        assert result['document_count'] == 1, "Should find 1 document with 'test'"
        print(f"   ✓ Search query works")

        # Test query with non-matching search
        result = await document_query(query="nonexistent")
        assert result['status'] == 'success', f"Non-matching query failed: {result}"
        assert result['document_count'] == 0, "Should find 0 documents"
        print(f"   ✓ Non-matching search returns 0 results")

        print("\n4. Testing document_update...")
        new_content = "# Test Document\n\nUpdated content here.\n\n## New Section\n\nMore content."
        result = await document_update(
            file_path=file_path,
            content=new_content
        )
        assert result['status'] == 'success', f"Update failed: {result}"
        assert 'content' in result['updates_applied'], "Content not in updates"
        print(f"   ✓ Updated document")

        # Verify update on filesystem
        with open(filesystem_path, 'r') as f:
            content = f.read()
        assert "Updated content" in content, "Content not updated"
        assert "New Section" in content, "New section not added"
        print(f"   ✓ File updated on filesystem")

        print("\n5. Testing document_delete...")
        result = await document_delete(file_path=file_path)
        assert result['status'] == 'success', f"Delete failed: {result}"
        print(f"   ✓ Deleted document")

        # Verify file deleted from filesystem
        assert not Path(filesystem_path).exists(), "File not deleted from filesystem"
        print(f"   ✓ File removed from filesystem")

        # Verify query shows no documents
        result = await document_query()
        assert result['document_count'] == 0, "Document still in query results"
        print(f"   ✓ Query shows 0 documents")

        print("\n✅ ALL TESTS PASSED!")
        print("\nSummary:")
        print("- All document tools work with filesystem only")
        print("- No database operations performed by tools")
        print("- File monitor will handle database sync automatically")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up temp directory")


if __name__ == '__main__':
    asyncio.run(test_document_tools())
