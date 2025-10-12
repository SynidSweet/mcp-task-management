#!/bin/bash

# Development MCP Server Startup Script
# Isolated development environment on port 8082

echo "🛠️ Starting DEVELOPMENT MCP Server"
echo "   Environment: DEVELOPMENT"
echo "   Port: 8082"
echo "   Data: Isolated development data"

# Kill any existing dev instances
pkill -f "mcp-server-dev.*http_wrapper.py" 2>/dev/null || true

# Start development server (portable path)
cd ~/.claude/task-sprint-system/mcp-server-dev
./venv/bin/python http_wrapper.py --port 8082

echo "✅ Development MCP Server started"
echo "   - Health: http://localhost:8082/health"
echo "   - Tools: http://localhost:8082/projects/{path}/tools"