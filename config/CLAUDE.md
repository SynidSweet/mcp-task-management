# MCP Server Configuration Guide

*Last updated: 2025-08-08 | Configuration for Claude Code integration*

## 🎯 Configuration Purpose
Configuration files for integrating the MCP Task Management Server with Claude Desktop and other MCP clients.

## 🔧 Key Configuration Files

### **claude_code_config.json.example** - Claude Code Integration Example
- **Purpose**: Example configuration for MCP server integration (not directly used by Claude Code)
- **Key Sections**:
  - `mcpServers`: MCP server definitions for Claude Desktop
  - Server configuration with command path and arguments
  - Environment variable handling for server startup
- **Integration**: Enables native `mcp__claude-tasks__*` tool access in Claude Code

### **mcp_config.json** - General MCP Configuration
- **Purpose**: General MCP server configuration settings
- **Key Sections**:
  - Server metadata and versioning
  - Tool registration configuration
  - Performance and logging settings
- **Usage**: Used by MCP server startup scripts and validation tools

## 🚀 Common Configuration Tasks

### Claude Code Integration
```bash
# Claude Code handles MCP server configuration internally
# No manual configuration file needed - servers are started automatically

# IMPORTANT: Due to Claude Code bug #1254, manual initialization required:
# Use mcp__claude-tasks__system_set_project_directory at session start
```

### Environment Configuration
```bash
# Set environment variables for MCP server
export PYTHONPATH=/path/to/mcp-server
export CLAUDE_TASKS_CONFIG=/path/to/config.yaml

# Test MCP server startup
python /path/to/mcp-server/server.py
```

### Configuration Validation
```bash
# Validate MCP server configuration
python test_claude_desktop_config.py

# Test tool registration
python test_registration.py
```

## 🎯 AI Assistant Context

### Configuration Patterns
- **Server Definition**: Each MCP server requires command path, arguments, and environment setup
- **Tool Prefix**: All tools use `mcp__claude-tasks__` prefix for Claude Code integration
- **Environment Isolation**: Server runs in isolated Python environment with specific PYTHONPATH

### Environment Handling
- **PYTHONPATH**: Points to MCP server module directory for imports
- **CLAUDE_TASKS_CONFIG**: Optional configuration file path for server settings
- **Virtual Environment**: Server runs in dedicated venv for dependency isolation

### Common Configuration Updates
- **Adding new tools**: No configuration changes needed (automatic registration)
- **Environment variables**: Update in claude_desktop_config.json server definition
- **Performance tuning**: Modify server startup arguments or environment settings
- **Path changes**: Update command paths when server location changes

### Troubleshooting
- **Tool not found**: Ensure Claude Code restarted after adding new tools
- **Server startup errors**: Check PYTHONPATH and virtual environment setup
- **Permission issues**: Verify server script executable permissions
- **Configuration validation**: Use test scripts to verify configuration correctness