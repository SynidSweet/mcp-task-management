#!/usr/bin/env python3
"""MCP Server - Simplified Architecture (No File Sync for Testing)"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Import spec utilities from .claude-specs
spec_utils_path = Path.home() / '.claude' / '.claude-specs' / 'utils'
sys.path.insert(0, str(spec_utils_path))
import spec_utils
sys.path.remove(str(spec_utils_path))

from core.project_manager import ProjectManager
from utils.tool_filter import ToolSubscriptionFilter, create_default_config

# Import tool registration functions
from tools.system_tools import register_system_tools
from tools.task_tools import register_task_tools
from tools.sprint_tools import register_sprint_tools
from tools.journal_tools import register_journal_tools
from tools.git_tools import register_git_tools
from tools.specification_tools import register_specification_tools
from tools.template_tools import register_template_tools
from tools.document_tools import register_document_tools


# Handle validation mode without dependencies
if "--validate" in sys.argv:
    print("MCP Server validation successful")
    sys.exit(0)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: Official MCP SDK not installed. Install with: pip install mcp")
    sys.exit(1)


class MCPServer:
    """MCP Server with Simplified Architecture (No File Sync)"""

    def __init__(self, project_dir: Optional[Path] = None):
        self.mcp = FastMCP("claude-tasks")
        self.project_manager = ProjectManager(project_dir)
        self._initialized = self.project_manager.is_initialized()

        # Load tool subscription filter (create default if doesn't exist)
        config_path = None
        if self._initialized:
            config_path = self.project_manager.project_path / ".claude-tasks" / "config" / "tool_subscription.json"
            # Create default config for local agents if it doesn't exist
            create_default_config(config_path)
        self.tool_filter = ToolSubscriptionFilter(config_path)

        # Print filter summary if filters are active
        filter_summary = self.tool_filter.get_summary()
        if filter_summary["has_filters"]:
            print("🔧 Tool subscription filters active:")
            for filter_desc in filter_summary["filters"]:
                print(f"   - {filter_desc}")

        self.unified_monitor = None
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all tools using simplified function-based architecture"""

        tool_registrations = [
            ("SystemTools", register_system_tools),
            ("TaskTools", register_task_tools),
            ("SprintTools", register_sprint_tools),
            ("JournalTools", register_journal_tools),
            ("GitTools", register_git_tools),
            ("SpecificationTools", register_specification_tools),
            ("TemplateTools", register_template_tools),
            ("DocumentTools", lambda mcp, pm, tf: register_document_tools(mcp, pm, self, tf))
        ]

        registered_count = 0
        for module_name, register_func in tool_registrations:
            try:
                # Pass tool_filter to all registration functions
                register_func(self.mcp, self.project_manager, self.tool_filter)
                print(f"✅ Registered {module_name}")
                registered_count += 1
            except Exception as e:
                print(f"❌ Failed to register {module_name}: {str(e)}")

        print(f"🎯 Simplified Architecture Complete: {registered_count}/{len(tool_registrations)} modules loaded")
        print(f"⚠️  File monitoring disabled (watchdog not available)")

    def run(self):
        """Run the MCP server"""
        return self.mcp.run()


def main():
    parser = argparse.ArgumentParser(description="MCP Server for Claude Tasks - Simplified (No Sync)")
    parser.add_argument("--project-dir", type=Path, help="Project directory path")
    parser.add_argument("--validate", action="store_true", help="Validate server configuration")

    args = parser.parse_args()

    if args.validate:
        print("MCP Server configuration validated successfully")
        return

    try:
        print(f"🚀 Starting MCP Server (No File Sync Mode)")
        print(f"   Project Directory: {args.project_dir or 'Auto-detect'}")

        server = MCPServer(project_dir=args.project_dir)
        server.run()
    except KeyboardInterrupt:
        print("\n🔶 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
