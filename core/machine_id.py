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
    Get machine ID for this computer.

    IMPORTANT: machine_id identifies the physical computer, not individual
    projects. All projects on this computer share the same machine_id.

    Single source of truth - all tools should use this function.
    Reads from global config at ~/.claude/.claude-machine-config.json

    Returns:
        machine_id string (e.g., "ubuntu-bokio-dev")

    Raises:
        ValueError: If machine_id not configured or invalid
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
    """Get the path to the machine configuration file.

    IMPORTANT: Returns GLOBAL config location shared across ALL projects
    on this computer. machine_id identifies the physical machine, not
    individual projects.

    Returns:
        Path to ~/.claude/.claude-machine-config.json (global config)
    """
    return Path.home() / ".claude" / ".claude-machine-config.json"


def set_machine_id(machine_id: str) -> Dict[str, Any]:
    """
    Set machine ID by creating/updating global configuration file.

    IMPORTANT: This sets the machine_id for the ENTIRE COMPUTER, not just
    one project. All projects on this computer will share this machine_id.

    Args:
        machine_id: Descriptive machine identifier (e.g., "ubuntu-bokio-dev")

    Returns:
        Dict with status and details
    """
    try:
        config_file = get_machine_config_path()

        # Ensure ~/.claude directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "machine_id": machine_id,
            "description": "Machine identifier for this computer (shared across all projects)",
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