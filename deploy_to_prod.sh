#!/bin/bash
#
# Production Deployment Script
# Copies development version to production with proper structure
#

set -e

SOURCE_DIR="/home/dev/projects/mcp-management-system/dev/mcp-server"
TARGET_DIR="/home/dev/projects/mcp-management-system/prod/mcp-server"

echo "============================================================"
echo "MCP Server Production Deployment"
echo "============================================================"
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Create target directory structure
echo "📁 Creating production directory structure..."
mkdir -p "$TARGET_DIR"/{core/universal_storage,tools,utils,supabase/migrations,docs,schemas}

# Copy core application files
echo "📋 Copying core application files..."
cp "$SOURCE_DIR/server.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/server_no_sync.py" "$TARGET_DIR/"

# Copy core modules
echo "📋 Copying core modules..."
cp "$SOURCE_DIR/core/project_manager.py" "$TARGET_DIR/core/"
cp "$SOURCE_DIR/core/machine_id.py" "$TARGET_DIR/core/"
cp "$SOURCE_DIR/core/__init__.py" "$TARGET_DIR/core/" 2>/dev/null || touch "$TARGET_DIR/core/__init__.py"
cp "$SOURCE_DIR/core/universal_storage/unified_file_monitor.py" "$TARGET_DIR/core/universal_storage/"
cp "$SOURCE_DIR/core/universal_storage/__init__.py" "$TARGET_DIR/core/universal_storage/" 2>/dev/null || touch "$TARGET_DIR/core/universal_storage/__init__.py"

# Copy tools
echo "📋 Copying tools..."
cp "$SOURCE_DIR/tools/"*.py "$TARGET_DIR/tools/"

# Copy utilities
echo "📋 Copying utilities..."
cp "$SOURCE_DIR/utils/"*.py "$TARGET_DIR/utils/"

# Copy documentation
echo "📋 Copying documentation..."
cp "$SOURCE_DIR/README.md" "$TARGET_DIR/" 2>/dev/null || echo "  (README.md not found, skipping)"
cp "$SOURCE_DIR/CLAUDE.md" "$TARGET_DIR/"
cp "$SOURCE_DIR/SCHEMA.md" "$TARGET_DIR/" 2>/dev/null || echo "  (SCHEMA.md not found, skipping)"
cp "$SOURCE_DIR/PRODUCTION_READINESS_REPORT.md" "$TARGET_DIR/"
cp "$SOURCE_DIR/SYNC_AUDIT_REPORT.md" "$TARGET_DIR/"

# Copy docs directory
if [ -d "$SOURCE_DIR/docs" ]; then
    echo "📋 Copying docs directory..."
    cp -r "$SOURCE_DIR/docs" "$TARGET_DIR/"
fi

# Copy migration scripts
echo "📋 Copying database migrations..."
if [ -d "$SOURCE_DIR/supabase/migrations" ]; then
    cp "$SOURCE_DIR/supabase/migrations/"*.sql "$TARGET_DIR/supabase/migrations/" 2>/dev/null || echo "  (No migration files found)"
    cp "$SOURCE_DIR/supabase/migrations/README.md" "$TARGET_DIR/supabase/migrations/" 2>/dev/null || echo "  (No migration README found)"
fi

# Copy utility scripts (data integrity, etc.)
echo "📋 Copying utility scripts..."
cp "$SOURCE_DIR/check_data_integrity.py" "$TARGET_DIR/" 2>/dev/null || echo "  (check_data_integrity.py not found)"
cp "$SOURCE_DIR/audit_sync.py" "$TARGET_DIR/" 2>/dev/null || echo "  (audit_sync.py not found)"
cp "$SOURCE_DIR/run_migration.py" "$TARGET_DIR/" 2>/dev/null || echo "  (run_migration.py not found)"

# Copy test files for production verification
echo "📋 Copying test files..."
cp "$SOURCE_DIR/test_all_mcp_tools_direct.py" "$TARGET_DIR/" 2>/dev/null || echo "  (test_all_mcp_tools_direct.py not found)"
cp "$SOURCE_DIR/test_templates_integration.py" "$TARGET_DIR/" 2>/dev/null || echo "  (test_templates_integration.py not found)"
cp "$SOURCE_DIR/test_specification_validation.py" "$TARGET_DIR/" 2>/dev/null || echo "  (test_specification_validation.py not found)"
cp "$SOURCE_DIR/test_tool_subscription.py" "$TARGET_DIR/" 2>/dev/null || echo "  (test_tool_subscription.py not found)"

# Copy schemas for reference
if [ -d "$SOURCE_DIR/schemas" ]; then
    echo "📋 Copying schemas..."
    cp -r "$SOURCE_DIR/schemas/"* "$TARGET_DIR/schemas/" 2>/dev/null || echo "  (No schemas found)"
fi

# Create production-specific files
echo "📋 Creating production configuration..."

# Create .gitignore if it doesn't exist
cat > "$TARGET_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/

# Project specific
.claude-tasks/data/*
!.claude-tasks/data/.gitkeep
*.log
.DS_Store

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF

# Create requirements.txt
cat > "$TARGET_DIR/requirements.txt" << 'EOF'
# MCP Server Dependencies
mcp>=0.1.0
watchdog>=2.0.0
supabase>=1.0.0
EOF

# Create production deployment notes
cat > "$TARGET_DIR/DEPLOYMENT_NOTES.md" << 'EOF'
# Production Deployment Notes

**Deployed**: $(date)
**Source**: /home/dev/projects/mcp-management-system/dev/mcp-server
**Target**: /home/dev/projects/mcp-management-system/prod/mcp-server

## Post-Deployment Steps

1. **Install Dependencies**
   ```bash
   # Install Python dependencies
   sudo apt-get install python3-watchdog python3-supabase
   # OR use pip
   pip install -r requirements.txt
   ```

2. **Test Server Startup**
   ```bash
   # With file monitoring (requires watchdog)
   python3 server.py --project-dir "$(pwd)"

   # Without file monitoring (if watchdog not available)
   python3 server_no_sync.py --project-dir "$(pwd)"
   ```

3. **Run Verification Tests**
   ```bash
   python3 test_all_mcp_tools_direct.py
   python3 check_data_integrity.py
   python3 audit_sync.py
   ```

4. **Configure for Production**
   - Update database credentials in tools/document_tools.py (or use env vars)
   - Review tool subscription filters in .claude-tasks/config/tool_subscription.json
   - Set up monitoring/logging as needed

## Health Checks

```bash
# Quick health check
python3 server.py --validate

# Data integrity check
python3 check_data_integrity.py --verbose

# Sync status check
python3 audit_sync.py
```

## Rollback

If issues occur, the development version is still available at:
/home/dev/projects/mcp-management-system/dev/mcp-server
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Production server location: $TARGET_DIR"
echo ""
echo "Next steps:"
echo "1. cd $TARGET_DIR"
echo "2. Install dependencies: sudo apt-get install python3-watchdog"
echo "3. Test: python3 server.py --validate"
echo "4. Run: python3 server.py --project-dir \"\$(pwd)\""
echo ""
echo "See DEPLOYMENT_NOTES.md for detailed instructions"
echo "============================================================"
