#!/usr/bin/env python3
"""
Manually trigger initial sync for auto-sync verification.

This script simulates what happens during MCP server startup:
1. Initialize UnifiedFileMonitor
2. Register global resources
3. Register project
4. Perform initial sync
"""

import asyncio
import sys
from pathlib import Path

from core.project_manager import ProjectManager
from core.universal_storage.unified_file_monitor import UnifiedFileMonitor


async def trigger_initial_sync(project_path: Path):
    """Trigger initial sync for the project"""
    print("="*80)
    print("MANUALLY TRIGGERING INITIAL SYNC")
    print("="*80)
    print(f"Project: {project_path}\n")

    try:
        # Initialize the monitor
        print("1️⃣  Initializing UnifiedFileMonitor...")
        monitor = UnifiedFileMonitor()
        await monitor.initialize()

        # Register global resources
        print("\n2️⃣  Registering global resources...")
        await monitor.register_global_resources()

        # Create project manager
        print(f"\n3️⃣  Creating ProjectManager for {project_path.name}...")
        project_manager = ProjectManager(project_path)

        if not project_manager.is_initialized():
            print(f"   ⚠️  Project not initialized at {project_path}")
            print(f"   Run: python server.py --project-dir \"{project_path}\"")
            return False

        # Register project (this triggers initial sync)
        print(f"\n4️⃣  Registering project (this triggers initial sync)...")
        project_id = str(project_path)
        await monitor.register_project(
            project_id=project_id,
            project_path=project_path,
            project_manager=project_manager
        )

        print("\n" + "="*80)
        print("✅ INITIAL SYNC TRIGGERED SUCCESSFULLY")
        print("="*80)
        print("\nNext steps:")
        print("   1. Run: python3 verify_auto_sync.py")
        print("   2. Check if sync discrepancies are resolved")
        print("   3. If issues persist, check database permissions")
        print()

        return True

    except Exception as e:
        print(f"\n❌ Error during initial sync: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point"""
    # Use current directory as project path
    project_path = Path.cwd()

    success = await trigger_initial_sync(project_path)

    if success:
        print("Run 'python3 verify_auto_sync.py' to verify sync status")
        sys.exit(0)
    else:
        print("Initial sync failed - check error messages above")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
