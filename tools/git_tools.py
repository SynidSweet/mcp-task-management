"""Git operations and repository health checks - Simplified"""
import os
import subprocess
from typing import Dict, Any
from core.project_manager import ProjectManager
from utils.helpers import handle_error
from utils.validation_wrapper import require_git_tools


def register_git_tools(mcp, project_manager: ProjectManager, tool_filter=None):
    """Register git tools with simple pattern"""
    
    def run_git_command(command: list, cwd: str = None) -> Dict[str, Any]:
        """Helper function to run git commands"""
        try:
            if cwd is None:
                cwd = str(project_manager.project_path)
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out"
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }

    @require_git_tools()
    @mcp.tool()
    async def session_commit_start(
        task_id: str, 
        message: str = None, 
        force_clean: bool = False,
        include_context: bool = False
    ) -> Dict[str, Any]:
        """Start git session for task work - creates session branch and initial commit"""
        try:
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            session_branch = f"session/{task_id}-{timestamp}"
            
            # Check if we're in a git repo
            git_check = run_git_command(["git", "rev-parse", "--git-dir"])
            if git_check["returncode"] != 0:
                return {
                    "status": "error",
                    "error": "Not a git repository",
                    "details": git_check["stderr"]
                }
            
            # Get current branch for context
            current_branch_result = run_git_command(["git", "branch", "--show-current"])
            current_branch = current_branch_result["stdout"] if current_branch_result["returncode"] == 0 else "unknown"
            
            # Check working directory status
            if not force_clean:
                status_result = run_git_command(["git", "status", "--porcelain"])
                if status_result["returncode"] == 0 and status_result["stdout"]:
                    return {
                        "status": "error",
                        "error": "Working directory not clean",
                        "details": "Use force_clean=True to proceed with uncommitted changes",
                        "uncommitted_changes": status_result["stdout"].split('\n')
                    }
            
            # Create session branch
            branch_result = run_git_command(["git", "checkout", "-b", session_branch])
            if branch_result["returncode"] != 0:
                return {
                    "status": "error",
                    "error": "Failed to create session branch",
                    "details": branch_result["stderr"]
                }
            
            # Create initial session commit
            session_message = message or f"SESSION_START: {task_id} - Starting work session"
            if include_context:
                session_message += f"\n\nStarted from: {current_branch}\nTimestamp: {timestamp}"
            
            # Add any staged changes or create empty commit
            add_result = run_git_command(["git", "add", "."])
            commit_result = run_git_command(["git", "commit", "-m", session_message, "--allow-empty"])
            
            if commit_result["returncode"] != 0:
                return {
                    "status": "error", 
                    "error": "Failed to create session commit",
                    "details": commit_result["stderr"]
                }
            
            return {
                "status": "success",
                "session_started": {
                    "task_id": task_id,
                    "session_branch": session_branch,
                    "timestamp": timestamp,
                    "previous_branch": current_branch,
                    "commit_message": session_message,
                    "commit_hash": run_git_command(["git", "rev-parse", "HEAD"])["stdout"][:8]
                }
            }
            
        except Exception as e:
            return handle_error(e, "session_commit_start")

    @require_git_tools()
    @mcp.tool()
    async def session_list_history(
        limit: int = 20,
        task_filter: str = "",
        file_detail_level: str = "summary",
        include_context: bool = False
    ) -> Dict[str, Any]:
        """List git session history with intelligent file summarization"""
        try:
            
            # Validate parameters
            if file_detail_level not in ["none", "summary", "full"]:
                return {
                    "status": "error",
                    "error": "Invalid file_detail_level",
                    "details": "Must be 'none', 'summary', or 'full'"
                }
            
            # Check if we're in a git repo
            git_check = run_git_command(["git", "rev-parse", "--git-dir"])
            if git_check["returncode"] != 0:
                return {
                    "status": "error",
                    "error": "Not a git repository"
                }
            
            # Build git log command
            git_cmd = ["git", "log", "--oneline", f"-{limit}"]
            if task_filter:
                git_cmd.extend(["--grep", f"SESSION_START: {task_filter}"])
            
            # Get session history
            log_result = run_git_command(git_cmd)
            if log_result["returncode"] != 0:
                return {
                    "status": "error",
                    "error": "Failed to get git history",
                    "details": log_result["stderr"]
                }
            
            sessions = []
            if log_result["stdout"]:
                for line in log_result["stdout"].split('\n')[:limit]:
                    if not line:
                        continue
                        
                    parts = line.split(' ', 1)
                    commit_hash = parts[0]
                    commit_message = parts[1] if len(parts) > 1 else ""
                    
                    # Extract task ID if it's a session commit
                    task_id = None
                    if "SESSION_START:" in commit_message:
                        try:
                            task_part = commit_message.split("SESSION_START:")[1].split()[0]
                            task_id = task_part.strip()
                        except IndexError:
                            pass
                    
                    session_info = {
                        "commit_hash": commit_hash,
                        "message": commit_message,
                        "task_id": task_id,
                        "is_session": task_id is not None
                    }
                    
                    # Add file information based on detail level
                    if file_detail_level != "none":
                        files_result = run_git_command([
                            "git", "show", "--name-status", "--format=", commit_hash
                        ])
                        
                        if files_result["returncode"] == 0 and files_result["stdout"]:
                            files = []
                            file_lines = [line for line in files_result["stdout"].split('\n') if line.strip()]
                            
                            if file_detail_level == "summary":
                                # Intelligent directory grouping (limit to 10 files)
                                if len(file_lines) > 10:
                                    # Group by directory
                                    dirs = {}
                                    shown_files = file_lines[:10]
                                    for file_line in shown_files:
                                        if len(file_line.split('\t')) >= 2:
                                            status, filepath = file_line.split('\t', 1)
                                            dirname = '/'.join(filepath.split('/')[:-1]) if '/' in filepath else '.'
                                            if dirname not in dirs:
                                                dirs[dirname] = []
                                            dirs[dirname].append({"status": status, "file": filepath})
                                    
                                    session_info["files"] = dirs
                                    session_info["total_files"] = len(file_lines)
                                    session_info["truncated"] = len(file_lines) > 10
                                else:
                                    for file_line in file_lines:
                                        if len(file_line.split('\t')) >= 2:
                                            status, filepath = file_line.split('\t', 1)
                                            files.append({"status": status, "file": filepath})
                                    session_info["files"] = files
                            
                            elif file_detail_level == "full":
                                for file_line in file_lines:
                                    if len(file_line.split('\t')) >= 2:
                                        status, filepath = file_line.split('\t', 1)
                                        files.append({"status": status, "file": filepath})
                                session_info["files"] = files
                    
                    # Add context information
                    if include_context:
                        # Get commit timestamp and author
                        info_result = run_git_command([
                            "git", "show", "--format=%ci|%an", "--no-patch", commit_hash
                        ])
                        if info_result["returncode"] == 0 and info_result["stdout"]:
                            info_parts = info_result["stdout"].strip().split('|')
                            if len(info_parts) >= 2:
                                session_info["timestamp"] = info_parts[0]
                                session_info["author"] = info_parts[1]
                    
                    sessions.append(session_info)
            
            return {
                "status": "success",
                "session_history": {
                    "sessions": sessions,
                    "total_shown": len(sessions),
                    "limit": limit,
                    "task_filter": task_filter,
                    "file_detail_level": file_detail_level
                }
            }
            
        except Exception as e:
            return handle_error(e, "session_list_history")
