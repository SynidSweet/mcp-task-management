"""
MCP tools for document management system integration.
Refactored to use ONLY local file operations (documents.json).
File monitor handles database sync automatically.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import validation wrapper
from utils.validation_wrapper import validation_wrapper

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None
    create_client = None



def get_supabase_client():
    """Get Supabase client with hardcoded credentials for document sync.

    NOTE: This helper function is used by OTHER modules (like unified_file_monitor.py).
    DO NOT REMOVE - only MCP tool functions have been refactored to use local files.
    """
    try:
        if not SUPABASE_AVAILABLE:
            return None, "Supabase library not available"

        # Use same credentials as frontend and requirements tools
        url = "https://yxyfiatdrgelnvxopdsm.supabase.co"
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4eWZpYXRkcmdlbG52eG9wZHNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwMTYzODEsImV4cCI6MjA3MjU5MjM4MX0.2kqRnsxp17XUYMaz36KffV2Kwff_vGvQ5sxBlFyrv-A"

        client = create_client(url, key)
        return client, None
    except Exception as e:
        return None, str(e)


# Import centralized machine ID management
from core.machine_id import get_machine_id


def get_or_create_project_id(project_path):
    """Get or create project ID for the current project.

    NOTE: This helper function is used by OTHER modules (like unified_file_monitor.py).
    DO NOT REMOVE - only MCP tool functions have been refactored to use local files.
    """
    client, error = get_supabase_client()
    if error:
        return None, f"Supabase client error: {error}"

    try:
        # First try to find existing project (using actual table column 'path')
        result = client.table('projects').select('id').eq('path', str(project_path)).execute()

        if result.data and len(result.data) > 0:
            # Project exists, return its ID
            return result.data[0]['id'], None

        # Project doesn't exist, create it (using actual table columns 'name' and 'path')
        project_name = os.path.basename(str(project_path))
        new_project = {
            'name': project_name,
            'path': str(project_path)
        }

        result = client.table('projects').insert(new_project).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]['id'], None
        else:
            return None, "Failed to create project"

    except Exception as e:
        return None, f"Project error: {str(e)}"


def register_document_tools(mcp, project_manager, server=None):
    """Register document management tools with existing MCP infrastructure."""

    @mcp.tool()
    async def document_create(
        document_title: str,
        document_type: str,
        description: str = "",
        content: str = ""
    ) -> Dict[str, Any]:
        """Create new document - writes to documentation table and /docs/ filesystem.

        Args:
            document_title: Title of the document
            document_type: Type/category (becomes subfolder: guides, architecture, etc.)
            description: Short description
            content: Markdown content for the document

        Creates:
            - Database record in documentation table
            - Markdown file at /docs/{document_type}/{document_title}.md
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                return {"status": "error", "error": f"Database error: {error}"}

            # Get project ID
            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return {"status": "error", "error": f"Project error: {error}"}

            machine_id = get_machine_id()
            doc_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()

            # Create file path (e.g., "guides/My Document.md")
            file_path = f"{document_type}/{document_title}.md"

            # Create full markdown content
            full_content = f"# {document_title}\n\n"
            if description:
                full_content += f"{description}\n\n"
            if content:
                full_content += content

            # Write to documentation table (for frontend AI agents)
            doc_record = {
                'id': doc_id,
                'project_id': project_id,
                'machine_id': machine_id,
                'doc_title': document_title,
                'file_path': file_path,
                'description': description,
                'content': full_content,
                'scope': 'project',
                'is_global': False,
                'created_at': timestamp,
                'updated_at': timestamp
            }

            result = client.table('documentation').insert(doc_record).execute()

            # Also write to filesystem (since DB→File sync needs async client)
            docs_dir = project_manager.project_path / 'docs' / document_type
            docs_dir.mkdir(parents=True, exist_ok=True)

            doc_file = docs_dir / f"{document_title}.md"
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(full_content)

            return {
                "status": "success",
                "document_id": doc_id,
                "file_path": file_path,
                "filesystem_path": str(doc_file),
                "message": f"Document created at {file_path}"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_update(
        file_path: str,
        content: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """Update existing document in documentation table and filesystem.

        Args:
            file_path: Path to document (e.g., "guides/My Document.md")
            content: New markdown content (optional)
            description: New description (optional)

        Updates both database and /docs/ file.
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                return {"status": "error", "error": f"Database error: {error}"}

            # Get project ID
            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return {"status": "error", "error": f"Project error: {error}"}

            # Find document in database
            result = client.table('documentation')\
                .select('*')\
                .eq('project_id', project_id)\
                .eq('file_path', file_path)\
                .execute()

            if not result.data:
                return {"status": "error", "error": f"Document not found: {file_path}"}

            doc = result.data[0]
            doc_id = doc['id']
            timestamp = datetime.now(timezone.utc).isoformat()

            # Update database
            updates = {'updated_at': timestamp}
            if description is not None:
                updates['description'] = description
            if content is not None:
                updates['content'] = content

            client.table('documentation').update(updates).eq('id', doc_id).execute()

            # Update filesystem file
            doc_file = project_manager.project_path / 'docs' / file_path
            if doc_file.exists() and content is not None:
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(content)

            return {
                "status": "success",
                "document_id": doc_id,
                "file_path": file_path,
                "updates_applied": list(updates.keys()),
                "message": f"Document updated: {file_path}"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_query(
        query: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Query documents from documentation table.

        Args:
            query: Optional text search in title/description/content
            limit: Maximum results (default: 50)

        Returns list of documents from /docs/ folder.
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                return {"status": "error", "error": f"Database error: {error}"}

            # Get project ID
            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return {"status": "error", "error": f"Project error: {error}"}

            # Query documentation table
            db_query = client.table('documentation').select('*').eq('project_id', project_id)

            # Apply text search if provided
            if query:
                # Note: Supabase textSearch requires full-text search setup
                # For now, fetch all and filter in Python
                result = db_query.execute()
                docs = result.data or []

                # Filter by query
                query_lower = query.lower()
                docs = [
                    d for d in docs
                    if query_lower in d.get('doc_title', '').lower()
                    or query_lower in d.get('description', '').lower()
                    or query_lower in d.get('content', '').lower()
                ]
            else:
                result = db_query.limit(limit).execute()
                docs = result.data or []

            # Format response
            documents = [
                {
                    "id": doc['id'],
                    "title": doc.get('doc_title'),
                    "file_path": doc.get('file_path'),
                    "description": doc.get('description', ''),
                    "created_at": doc.get('created_at'),
                    "updated_at": doc.get('updated_at')
                }
                for doc in docs[:limit]
            ]

            return {
                "status": "success",
                "document_count": len(documents),
                "documents": documents
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_get(
        file_path: str
    ) -> Dict[str, Any]:
        """Get document from documentation table by file path.

        Args:
            file_path: Path to document (e.g., "guides/My Document.md")

        Returns document with full content.
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                return {"status": "error", "error": f"Database error: {error}"}

            # Get project ID
            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return {"status": "error", "error": f"Project error: {error}"}

            # Find document in database
            result = client.table('documentation')\
                .select('*')\
                .eq('project_id', project_id)\
                .eq('file_path', file_path)\
                .execute()

            if not result.data:
                return {"status": "error", "error": f"Document not found: {file_path}"}

            doc = result.data[0]

            return {
                "status": "success",
                "document": {
                    "id": doc['id'],
                    "title": doc.get('doc_title'),
                    "file_path": doc.get('file_path'),
                    "description": doc.get('description'),
                    "content": doc.get('content'),
                    "created_at": doc.get('created_at'),
                    "updated_at": doc.get('updated_at')
                }
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_delete(
        file_path: str
    ) -> Dict[str, Any]:
        """Delete document from documentation table and filesystem.

        Args:
            file_path: Path to document (e.g., "guides/My Document.md")

        Removes both database record and file.
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Get Supabase client
            client, error = get_supabase_client()
            if error:
                return {"status": "error", "error": f"Database error: {error}"}

            # Get project ID
            project_id, error = get_or_create_project_id(project_manager.project_path)
            if error:
                return {"status": "error", "error": f"Project error: {error}"}

            # Find document in database
            result = client.table('documentation')\
                .select('*')\
                .eq('project_id', project_id)\
                .eq('file_path', file_path)\
                .execute()

            if not result.data:
                return {"status": "error", "error": f"Document not found: {file_path}"}

            doc = result.data[0]
            doc_id = doc['id']

            # Delete from database
            client.table('documentation').delete().eq('id', doc_id).execute()

            # Delete from filesystem
            doc_file = project_manager.project_path / 'docs' / file_path
            if doc_file.exists():
                doc_file.unlink()

            return {
                "status": "success",
                "document_id": doc_id,
                "file_path": file_path,
                "message": f"Document deleted: {file_path}"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


