"""Journal and session management operations - Simplified"""
from typing import Dict, Any
from core.project_manager import ProjectManager
from utils.helpers import (
    handle_error,
    load_json_data,
    save_json_data,
    create_session_id,
    get_timestamp
)
from utils.validation_wrapper import require_project_basics


def register_journal_tools(mcp, project_manager: ProjectManager, tool_filter=None):
    """Register journal tools with simple pattern"""
    
    @require_project_basics()
    @mcp.tool()
    async def journal_create_session(
        session_type: str,
        duration_minutes: float,
        tasks_worked: str,
        discoveries: str = "",
        key_achievements: str = "",
        sprint_progress_impact: str = ""
    ) -> Dict[str, Any]:
        """Create journal session - simplified"""
        try:
            
            journal_file = project_manager.get_data_file('journal')
            data = load_json_data(journal_file)
            
            # Create session entry
            session = {
                "id": create_session_id(),
                "session_type": session_type,
                "duration_minutes": duration_minutes,
                "tasks_worked": tasks_worked,
                "discoveries": discoveries,
                "key_achievements": key_achievements,
                "sprint_progress_impact": sprint_progress_impact,
                "created_at": get_timestamp()
            }
            
            # Ensure journal list exists
            if "journal" not in data:
                data["journal"] = []
            
            data["journal"].append(session)
            save_json_data(journal_file, data)
            
            return {
                "status": "success",
                "session": session,
                "message": f"Journal session {session['id']} created"
            }
            
        except Exception as e:
            return handle_error(e, "journal_create_session")
    
    @require_project_basics()
    @mcp.tool()
    async def journal_get_recent(limit: str = "5") -> Dict[str, Any]:
        """Get recent work sessions"""
        try:
            journal_file = project_manager.get_data_file('journal')
            data = load_json_data(journal_file)

            sessions = data.get("journal", [])

            # Sort by created_at (most recent first)
            sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)

            # Apply limit
            try:
                limit_num = int(limit)
                sessions = sessions[:limit_num]
            except ValueError:
                pass

            return {
                "status": "success",
                "recent_sessions": sessions,
                "total_sessions": len(data.get("journal", []))
            }

        except Exception as e:
            return handle_error(e, "journal_get_recent")

    @require_project_basics()
    @mcp.tool()
    async def journal_search(
        query: str,
        session_type: str = ""
    ) -> Dict[str, Any]:
        """Search journal entries for specific work or patterns"""
        try:
            journal_file = project_manager.get_data_file('journal')
            data = load_json_data(journal_file)

            sessions = data.get("journal", [])

            # Filter by session_type if specified
            if session_type:
                sessions = [s for s in sessions if s.get("session_type") == session_type]

            # Search in text fields
            query_lower = query.lower()
            matching_sessions = []

            for session in sessions:
                searchable_text = " ".join([
                    session.get("tasks_worked", ""),
                    session.get("discoveries", ""),
                    session.get("key_achievements", ""),
                    session.get("sprint_progress_impact", "")
                ]).lower()

                if query_lower in searchable_text:
                    matching_sessions.append(session)

            # Sort by created_at (most recent first)
            matching_sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)

            return {
                "status": "success",
                "matching_sessions": matching_sessions,
                "query": query,
                "total_matches": len(matching_sessions)
            }

        except Exception as e:
            return handle_error(e, "journal_search")
