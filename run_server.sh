#!/bin/bash
# Run the MCP server for testing

echo "Starting MCP Server for Task & Sprint Management System..."
echo "=============================================="
echo "This server implements the Model Context Protocol (MCP)"
echo "for integration with Claude Desktop."
echo ""
echo "Registered tools:"
echo "- Task management: create, get, update, list, delete"
echo "- Sprint management: create, activate, current, list"
echo "- Backlog management: add, list, prioritize"
echo "- System operations: config, validate, backup"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=============================================="

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

python server.py --project-dir . --debug