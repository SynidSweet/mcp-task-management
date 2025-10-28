"""Tool subscription filtering system"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from utils.tool_categories import get_tool_category, get_tools_by_category


# Default configuration for local agents (excludes online-only document tools)
DEFAULT_TOOL_SUBSCRIPTION = {
    "tool_subscription": {
        "include_tools": [],
        "exclude_tools": [],
        "include_categories": [],
        "exclude_categories": ["document"]  # Document tools are for online agents only
    }
}


def create_default_config(config_path: Path) -> bool:
    """Create default tool subscription config file.

    Args:
        config_path: Path where config file should be created

    Returns:
        True if file was created, False if it already existed or failed
    """
    if config_path.exists():
        return False

    try:
        # Create parent directories if they don't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create config with helpful comments
        config_content = {
            "_comment": "Tool Subscription Configuration - Controls which MCP tools are available",
            "_description": "Default config excludes 'document' category (online agents only). Local agents use filesystem for docs.",
            "_categories": [
                "system (3 tools) - Health checks, project setup",
                "task (7 tools) - Task CRUD operations",
                "sprint (8 tools) - Sprint management",
                "journal (3 tools) - Session tracking",
                "git (2 tools) - Git operations",
                "specification (5 tools) - Requirements management",
                "template (2 tools) - Template operations",
                "document (5 tools) - Documentation management [EXCLUDED BY DEFAULT]"
            ],
            "tool_subscription": DEFAULT_TOOL_SUBSCRIPTION["tool_subscription"]
        }

        # Write with nice formatting
        with open(config_path, 'w') as f:
            json.dump(config_content, f, indent=2)

        print(f"📝 Created default tool subscription config at {config_path}")
        print("   → Excluding 'document' category (online agents only)")
        print("   → Edit .claude-tasks/config/tool_subscription.json to customize")
        return True

    except Exception as e:
        print(f"⚠️  Failed to create default config: {e}")
        return False


class ToolSubscriptionFilter:
    """Filters tools based on subscription configuration.

    Configuration file format (.claude-tasks/config/tool_subscription.json):
    {
      "tool_subscription": {
        "include_tools": [],        # Whitelist specific tools (most restrictive)
        "exclude_tools": [],        # Blacklist specific tools
        "include_categories": [],   # Whitelist categories
        "exclude_categories": []    # Blacklist categories
      }
    }

    Precedence order:
    1. include_tools (most restrictive) - if set, ONLY these tools are allowed
    2. include_categories - if set, only tools from these categories
    3. exclude_categories - remove entire categories
    4. exclude_tools - remove specific tools
    5. Default - all tools allowed if no config
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize filter with optional config file.

        Args:
            config_path: Path to tool_subscription.json config file
        """
        self.config = self._load_config(config_path)
        self.include_tools: Set[str] = set(self.config.get("include_tools", []))
        self.exclude_tools: Set[str] = set(self.config.get("exclude_tools", []))
        self.include_categories: Set[str] = set(self.config.get("include_categories", []))
        self.exclude_categories: Set[str] = set(self.config.get("exclude_categories", []))

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load subscription config from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary (empty if file doesn't exist or has errors)
        """
        if not config_path or not config_path.exists():
            return {}  # No config = all tools available

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                # Extract only the tool_subscription section (ignore _comment, _description, etc.)
                return data.get("tool_subscription", {})
        except Exception as e:
            print(f"⚠️  Failed to load tool subscription config: {e}")
            return {}

    def should_register_tool(self, tool_name: str) -> bool:
        """Check if a tool should be registered based on filters.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool should be registered, False otherwise
        """
        # 1. Most restrictive: explicit include list
        if self.include_tools:
            return tool_name in self.include_tools

        # 2. Category-based filtering
        tool_category = get_tool_category(tool_name)

        # If include_categories is set, only allow those categories
        if self.include_categories:
            if tool_category not in self.include_categories:
                return False

        # Exclude specific categories
        if tool_category in self.exclude_categories:
            return False

        # 3. Explicit tool exclusion
        if tool_name in self.exclude_tools:
            return False

        # Default: allow the tool
        return True

    def get_summary(self) -> Dict:
        """Get summary of active filters.

        Returns:
            Dictionary with filter status and active filter descriptions
        """
        active_filters = []

        if self.include_tools:
            active_filters.append(f"Only tools: {sorted(self.include_tools)}")
        if self.exclude_tools:
            active_filters.append(f"Exclude tools: {sorted(self.exclude_tools)}")
        if self.include_categories:
            active_filters.append(f"Only categories: {sorted(self.include_categories)}")
        if self.exclude_categories:
            active_filters.append(f"Exclude categories: {sorted(self.exclude_categories)}")

        return {
            "has_filters": bool(active_filters),
            "filters": active_filters or ["No filters - all tools available"]
        }

    def get_allowed_tools(self, all_tools: List[str]) -> List[str]:
        """Get list of allowed tools from a given list.

        Args:
            all_tools: List of all available tool names

        Returns:
            Filtered list of allowed tool names
        """
        return [tool for tool in all_tools if self.should_register_tool(tool)]

    def get_filtered_count(self, total_count: int, allowed_count: int) -> str:
        """Get a formatted string showing filtering results.

        Args:
            total_count: Total number of available tools
            allowed_count: Number of tools allowed after filtering

        Returns:
            Formatted string like "25/35 tools enabled (71%)"
        """
        if total_count == 0:
            return "0 tools available"

        percentage = (allowed_count / total_count) * 100
        return f"{allowed_count}/{total_count} tools enabled ({percentage:.0f}%)"
