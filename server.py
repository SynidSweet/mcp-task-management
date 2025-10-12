#!/usr/bin/env python3
"""MCP Server - Simplified Architecture"""

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
    """MCP Server with Simplified Architecture"""

    def __init__(self, project_dir: Optional[Path] = None):
        self.mcp = FastMCP("claude-tasks")
        self.project_manager = ProjectManager(project_dir)
        self._initialized = self.project_manager.is_initialized()
        self.unified_monitor = None
        self._should_init_monitoring = self._initialized
        self._register_all_tools()
    
    async def _initialize_unified_monitoring(self):
        """Initialize unified file monitoring for all auto-sync."""
        try:
            from core.universal_storage.unified_file_monitor import UnifiedFileMonitor

            self.unified_monitor = UnifiedFileMonitor()
            await self.unified_monitor.initialize()
            await self.unified_monitor.register_global_resources()

            if self._initialized:
                project_id = str(self.project_manager.project_path)
                await self.unified_monitor.register_project(
                    project_id=project_id,
                    project_path=self.project_manager.project_path,
                    project_manager=self.project_manager
                )

            await self.unified_monitor.start_monitoring()
            print("✅ Unified file monitoring initialized and started")

        except Exception as e:
            print(f"⚠️ Unified monitoring initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.unified_monitor = None

    async def ensure_monitoring_initialized(self):
        """Lazy initialization of unified monitoring when first needed."""
        if self._should_init_monitoring and self.unified_monitor is None:
            await self._initialize_unified_monitoring()
            self._should_init_monitoring = False

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
            ("DocumentTools", lambda mcp, pm: register_document_tools(mcp, pm, self))
        ]

        registered_count = 0
        for module_name, register_func in tool_registrations:
            try:
                register_func(self.mcp, self.project_manager)
                print(f"✅ Registered {module_name}")
                registered_count += 1
            except Exception as e:
                print(f"❌ Failed to register {module_name}: {str(e)}")

        print(f"🎯 Simplified Architecture Complete: {registered_count}/{len(tool_registrations)} modules loaded")
    
    def run(self):
        """Run the MCP server"""
        @self.mcp.on_startup
        async def startup():
            if self._initialized:
                await self._initialize_unified_monitoring()

        return self.mcp.run()


def main():
    parser = argparse.ArgumentParser(description="MCP Server for Claude Tasks - Simplified")
    parser.add_argument("--project-dir", type=Path, help="Project directory path")
    parser.add_argument("--validate", action="store_true", help="Validate server configuration")
    
    args = parser.parse_args()
    
    if args.validate:
        print("MCP Server configuration validated successfully")
        return
    
    try:
        print(f"🚀 Starting MCP Server")
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