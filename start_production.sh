#!/bin/bash

# Production startup script for Centralized MCP Server
# Runs on port 80 to be accessible via api.petter.ai

echo "🚀 Starting Production Centralized MCP Server"
echo "   Domain: api.petter.ai"
echo "   Architecture: Multi-project HTTP MCP with isolation"

# Kill any existing instances
echo "🔄 Stopping existing instances..."
pkill -f "http_wrapper.py" 2>/dev/null || true

# Start on port 80 for domain access
echo "🌐 Starting server on port 80..."
sudo ./venv/bin/python http_wrapper.py --port 80 --host 0.0.0.0

echo "✅ Production MCP Server started"
echo "   - Health: http://api.petter.ai/health"
echo "   - Tools: http://api.petter.ai/projects/{path}/tools" 
echo "   - MCP: http://api.petter.ai/projects/{path}/mcp"