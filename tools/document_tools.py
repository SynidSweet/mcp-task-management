"""
MCP tools for document management - filesystem-only operations.

All tools work exclusively with markdown files in /docs/ folder.
UnifiedFileMonitor handles automatic sync to documentation table.

Architecture:
- Tools: Read/write markdown files in /docs/{type}/{name}.md
- File Monitor: Syncs changes to/from documentation table in Supabase
- No direct database operations in tools (follows task/sprint pattern)
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

    NOTE: This helper is used by UnifiedFileMonitor for database sync.
    MCP tools do NOT use this - they work with filesystem only.
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


def get_or_create_project_id(project_manager):
    """Get or create project ID using file-based project identification.

    NOTE: This helper is used by UnifiedFileMonitor for database sync.
    MCP tools do NOT use this - they work with filesystem only.

    NEW: Uses .claude-tasks/data/project_id file for cross-machine identification.
    Same repo on different machines = same project_id (from file).

    Args:
        project_manager: ProjectManager instance (not just path)

    Returns:
        Tuple of (project_id: str, error: str|None)
    """
    client, error = get_supabase_client()
    if error:
        return None, f"Supabase client error: {error}"

    try:
        # 1. Get project_id from file (or generate new one)
        project_id = project_manager.get_or_generate_project_id()

        # 2. Get machine_id for this computer
        try:
            machine_id = get_machine_id()
        except Exception as e:
            return None, f"Machine ID error: {e}"

        # 3. Check if this machine already registered for this project
        result = client.table('projects').select('*')\
            .eq('id', project_id)\
            .eq('machine_id', machine_id)\
            .execute()

        if result.data and len(result.data) > 0:
            # Machine already registered, check if path changed
            existing = result.data[0]
            current_path = str(project_manager.project_path)

            if existing['path'] != current_path:
                # Path changed on this machine, update it
                client.table('projects').update({
                    'path': current_path,
                    'updated_at': 'NOW()'
                }).eq('id', project_id).eq('machine_id', machine_id).execute()

            return project_id, None

        # 4. This machine not yet registered for this project, create entry
        project_name = os.path.basename(str(project_manager.project_path))
        new_record = {
            'id': project_id,  # From project_id file
            'machine_id': machine_id,
            'path': str(project_manager.project_path),
            'name': project_name
        }

        result = client.table('projects').insert(new_record).execute()

        if result.data and len(result.data) > 0:
            return project_id, None
        else:
            return None, "Failed to create project record"

    except Exception as e:
        return None, f"Project error: {str(e)}"


def register_document_tools(mcp, project_manager, server=None, tool_filter=None):
    """Register document management tools with existing MCP infrastructure."""

    @mcp.tool()
    async def document_create(
        document_title: str,
        document_type: str,
        description: str = "",
        content: str = ""
    ) -> Dict[str, Any]:
        """Create new document - writes markdown file to /docs/ filesystem.

        Args:
            document_title: Title of the document
            document_type: Type/category (becomes subfolder: guides, architecture, etc.)
            description: Short description
            content: Markdown content for the document

        Creates:
            - Markdown file at /docs/{document_type}/{document_title}.md
            - File monitor automatically syncs to documentation table
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Create file path (e.g., "guides/My Document.md")
            file_path = f"{document_type}/{document_title}.md"

            # Create full markdown content
            full_content = f"# {document_title}\n\n"
            if description:
                full_content += f"{description}\n\n"
            if content:
                full_content += content

            # Write to filesystem - file monitor handles database sync
            docs_dir = project_manager.project_path / 'docs' / document_type
            docs_dir.mkdir(parents=True, exist_ok=True)

            doc_file = docs_dir / f"{document_title}.md"
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(full_content)

            return {
                "status": "success",
                "file_path": file_path,
                "filesystem_path": str(doc_file),
                "message": f"Document created at {file_path} (will auto-sync to database)"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_update(
        file_path: str,
        content: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """Update existing document - modifies markdown file in /docs/ filesystem.

        Args:
            file_path: Path to document (e.g., "guides/My Document.md")
            content: New markdown content (replaces entire file)
            description: New description (updates second paragraph after title)

        Updates:
            - Markdown file at /docs/{file_path}
            - File monitor automatically syncs to documentation table
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Check if file exists
            doc_file = project_manager.project_path / 'docs' / file_path
            if not doc_file.exists():
                return {"status": "error", "error": f"Document not found: {file_path}"}

            updates_applied = []

            # If full content provided, replace entire file
            if content is not None:
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                updates_applied.append('content')

            # If only description provided, update the description paragraph
            elif description is not None:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

                # Parse and update description (second paragraph after title)
                lines = existing_content.split('\n')
                new_lines = []
                found_title = False
                description_updated = False

                for i, line in enumerate(lines):
                    if line.startswith('# ') and not found_title:
                        # Found title, add it and description after
                        new_lines.append(line)
                        new_lines.append('')
                        new_lines.append(description)
                        found_title = True
                        description_updated = True
                        # Skip old description (next non-empty line)
                        continue
                    elif found_title and not description_updated:
                        # Skip old description paragraph
                        if line.strip() == '':
                            continue
                        description_updated = True

                    if description_updated or not found_title:
                        new_lines.append(line)

                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                updates_applied.append('description')

            return {
                "status": "success",
                "file_path": file_path,
                "filesystem_path": str(doc_file),
                "updates_applied": updates_applied,
                "message": f"Document updated: {file_path} (will auto-sync to database)"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_query(
        query: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Query documents - searches markdown files in /docs/ folder.

        Args:
            query: Optional text search in title/content
            limit: Maximum results (default: 50)

        Returns list of documents found in /docs/ folder.
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            import glob
            from pathlib import Path

            docs_dir = project_manager.project_path / 'docs'
            if not docs_dir.exists():
                return {
                    "status": "success",
                    "document_count": 0,
                    "documents": []
                }

            # Find all markdown files
            md_files = list(docs_dir.glob('**/*.md'))

            documents = []
            for md_file in md_files:
                try:
                    # Read file content
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract title from first # header
                    title = md_file.stem
                    for line in content.split('\n'):
                        if line.startswith('# '):
                            title = line[2:].strip()
                            break

                    # Extract description (first non-header paragraph)
                    description = ""
                    for line in content.split('\n'):
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#') and len(stripped) > 10:
                            description = stripped[:200]
                            break

                    # Get relative path from docs/
                    relative_path = md_file.relative_to(docs_dir)
                    file_path = str(relative_path).replace('\\', '/')

                    # Apply query filter if provided
                    if query:
                        query_lower = query.lower()
                        if not (query_lower in title.lower() or
                                query_lower in description.lower() or
                                query_lower in content.lower()):
                            continue

                    # Get file stats
                    stats = md_file.stat()

                    documents.append({
                        "title": title,
                        "file_path": file_path,
                        "description": description,
                        "filesystem_path": str(md_file),
                        "created_at": datetime.fromtimestamp(stats.st_ctime, timezone.utc).isoformat(),
                        "updated_at": datetime.fromtimestamp(stats.st_mtime, timezone.utc).isoformat()
                    })

                except Exception as e:
                    # Skip files that can't be read
                    continue

            # Sort by updated_at (most recent first)
            documents.sort(key=lambda d: d['updated_at'], reverse=True)

            # Apply limit
            documents = documents[:limit]

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
        """Get document - reads markdown file from /docs/ folder.

        Args:
            file_path: Path to document (e.g., "guides/My Document.md")

        Returns document with full content from filesystem.
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Read document from filesystem
            doc_file = project_manager.project_path / 'docs' / file_path
            if not doc_file.exists():
                return {"status": "error", "error": f"Document not found: {file_path}"}

            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract title from first # header
            title = doc_file.stem
            for line in content.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    break

            # Extract description (first non-header paragraph)
            description = ""
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and len(stripped) > 10:
                    description = stripped[:200]
                    break

            # Get file stats
            stats = doc_file.stat()

            return {
                "status": "success",
                "document": {
                    "title": title,
                    "file_path": file_path,
                    "description": description,
                    "content": content,
                    "filesystem_path": str(doc_file),
                    "created_at": datetime.fromtimestamp(stats.st_ctime, timezone.utc).isoformat(),
                    "updated_at": datetime.fromtimestamp(stats.st_mtime, timezone.utc).isoformat()
                }
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


    @mcp.tool()
    async def document_delete(
        file_path: str
    ) -> Dict[str, Any]:
        """Delete document - removes markdown file from /docs/ filesystem.

        Args:
            file_path: Path to document (e.g., "guides/My Document.md")

        Removes:
            - Markdown file at /docs/{file_path}
            - File monitor automatically removes from documentation table
        """
        if not project_manager.is_initialized():
            return {"status": "error", "error": "No project directory set"}

        try:
            # Delete from filesystem - file monitor handles database removal
            doc_file = project_manager.project_path / 'docs' / file_path
            if not doc_file.exists():
                return {"status": "error", "error": f"Document not found: {file_path}"}

            doc_file.unlink()

            return {
                "status": "success",
                "file_path": file_path,
                "message": f"Document deleted: {file_path} (will auto-remove from database)"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


