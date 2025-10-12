"""
Centralized Machine ID Management

Single source of truth for machine ID across all MCP tools.
Uses .claude-machine-config.json file in MCP server directory.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def get_machine_id() -> str:
    """
    Get machine ID for this machine.
    
    Single source of truth - all tools should use this function.
    Reads from .claude-machine-config.json in MCP server directory.
    """
    config_file = get_machine_config_path()
    
    if not config_file.exists():
        raise ValueError(f"Machine ID not configured. Run: mcp__claude-tasks__requirements_set_machine_id to set up machine ID for this machine.")
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        machine_id = config.get('machine_id')
        if not machine_id:
            raise ValueError("machine_id not found in configuration file")
        
        return machine_id
        
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid machine configuration file: {e}")


def get_machine_config_path() -> Path:
    """Get the path to the machine configuration file."""
    # Find MCP server directory by locating this module's location
    # This works regardless of working directory and is portable
    current_file = Path(__file__).resolve()
    mcp_server_dir = current_file.parent.parent  # core/machine_id.py -> mcp-server/
    return mcp_server_dir / ".claude-machine-config.json"


def set_machine_id(machine_id: str) -> Dict[str, Any]:
    """
    Set machine ID by creating/updating configuration file.
    
    Args:
        machine_id: Descriptive machine identifier
        
    Returns:
        Dict with status and details
    """
    try:
        config_file = get_machine_config_path()
        
        config = {
            "machine_id": machine_id,
            "description": "Machine identifier for this MCP server instance",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "status": "success",
            "machine_id": machine_id,
            "config_file": str(config_file),
            "message": "Machine ID set successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def get_machine_info() -> Dict[str, Any]:
    """
    Get comprehensive machine information.
    
    Returns:
        Dict with machine_id, hostname, config_file path, etc.
    """
    try:
        machine_id = get_machine_id()
        config_file = get_machine_config_path()
        
        return {
            "machine_id": machine_id,
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
            "config_file": str(config_file),
            "source": "config_file"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "config_file": str(get_machine_config_path()),
            "source": "error"
        }


def validate_machine_id() -> Optional[str]:
    """
    Validate machine ID configuration exists and is valid.

    Returns:
        None if valid, error message if invalid
    """
    config_file = get_machine_config_path()

    if not config_file.exists():
        return "missing_config_file"

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        machine_id = config.get('machine_id')
        if not machine_id:
            return "missing_machine_id"

        # Check for auto-generated patterns
        if machine_id.startswith('machine_') or (machine_id.startswith('ip-') and len(machine_id.split('-')) > 4):
            return "auto_generated_id"

        return None

    except (json.JSONDecodeError, KeyError):
        return "corrupted_config"