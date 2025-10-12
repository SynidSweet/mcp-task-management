#!/usr/bin/env python3
"""
HTTP Wrapper for MCP Server - Centralized Architecture
Allows multiple projects to connect to one persistent MCP server
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
import uvicorn

from server import MCPServer

app = FastAPI(title="Production MCP Server")

# Enable CORS for web frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store project-specific MCP instances
project_servers: Dict[str, MCPServer] = {}

async def get_project_server(project_path: str) -> MCPServer:
    """Get or create MCP server for specific project"""
    if project_path not in project_servers:
        print(f"🚀 Creating MCP server for project: {project_path}")
        server = MCPServer(project_dir=Path(project_path))
        project_servers[project_path] = server

        # Initialize unified file monitoring for automatic sync
        print(f"   Initializing unified file monitoring...")
        await server._initialize_unified_monitoring()

    return project_servers[project_path]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": "PRODUCTION",
        "active_projects": len(project_servers),
        "projects": list(project_servers.keys())
    }

@app.get("/projects/{project_path:path}/tools")
async def list_project_tools(project_path: str):
    """List available tools for a specific project"""
    try:
        server = await get_project_server(project_path)
        
        # Get tools using FastMCP's list_tools method (async)
        try:
            mcp_tools = await server.mcp.list_tools()
            tools = []
            
            for tool in mcp_tools:
                tools.append({
                    "name": getattr(tool, 'name', str(tool)),
                    "description": getattr(tool, 'description', ''),
                    "parameters": getattr(tool, 'inputSchema', getattr(tool, 'parameters', {}))
                })
                
        except Exception as tool_error:
            # Fallback debugging  
            tools = [{
                "debug": f"list_tools failed: {tool_error}",
                "available_methods": [method for method in dir(server.mcp) if not method.startswith('_')],
                "server_type": type(server.mcp).__name__
            }]
        
        return {
            "status": "success",
            "project": project_path,
            "tools": tools,
            "count": len(tools),
            "debug": {
                "server_type": type(server.mcp).__name__,
                "has_tools": hasattr(server.mcp, '_tools'),
                "has_registry": hasattr(server.mcp, 'tool_registry')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_path:path}/tools/{tool_name}")
async def call_project_tool(project_path: str, tool_name: str, params: dict = None):
    """Execute a tool for a specific project"""
    try:
        server = await get_project_server(project_path)
        
        # Execute tool using FastMCP's tool manager
        if hasattr(server.mcp, '_tool_manager'):
            result = await server.mcp._tool_manager.call_tool(tool_name, params or {})
        elif hasattr(server.mcp, 'call_tool'):
            result = await server.mcp.call_tool(tool_name, params or {})
        else:
            # Direct tool execution fallback
            tools = await server.mcp.list_tools()
            tool_func = None
            for tool in tools:
                if getattr(tool, 'name', '') == tool_name:
                    tool_func = tool
                    break
            
            if not tool_func:
                raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
            
            # Execute the tool function directly
            result = await tool_func(params or {})
        
        return {
            "status": "success",
            "project": project_path,
            "tool": tool_name,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_path:path}/mcp")
async def mcp_protocol_endpoint(project_path: str, request_data: dict):
    """MCP protocol endpoint for AI SDK integration"""
    try:
        server = await get_project_server(project_path)
        
        # Handle MCP protocol requests
        if request_data.get("method") == "initialize":
            # MCP initialization handshake
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "claude-tasks-prod",
                        "version": "1.0.0"
                    }
                }
            }
        elif request_data.get("method") == "tools/list":
            tools = await server.mcp.list_tools()
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": getattr(tool, 'name', str(tool)),
                            "description": getattr(tool, 'description', ''),
                            "inputSchema": getattr(tool, 'inputSchema', getattr(tool, 'parameters', {}))
                        }
                        for tool in tools
                    ]
                }
            }
        elif request_data.get("method") == "tools/call":
            tool_name = request_data.get("params", {}).get("name")
            arguments = request_data.get("params", {}).get("arguments", {})
            
            result = await server.mcp._tool_manager.call_tool(tool_name, arguments) if hasattr(server.mcp, '_tool_manager') else await server.mcp.call_tool(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0", 
                "id": request_data.get("id"),
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported method: {request_data.get('method')}")
            
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "error": {"code": -1, "message": str(e)}
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Centralized MCP HTTP Server")
    parser.add_argument("--port", type=int, default=8081, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    print("🌐 Starting Centralized MCP Server")
    print(f"   - HTTP API: http://{args.host}:{args.port}")
    print(f"   - Health: http://{args.host}:{args.port}/health") 
    print(f"   - Project tools: http://{args.host}:{args.port}/projects/{{path}}/tools")
    print(f"   - MCP protocol: http://{args.host}:{args.port}/projects/{{path}}/mcp")
    
    uvicorn.run(app, host=args.host, port=args.port)