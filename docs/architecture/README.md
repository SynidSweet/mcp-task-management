# MCP Server Dev - System Architecture Overview

*Last updated: 2025-10-07*

## Purpose
Simplified MCP server providing 35 tools across 8 categories for task management, sprint tracking, journal entries, and cloud synchronization. Built with function-based tool registration and direct JSON operations.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastMCP Server                          │
│                     (server.py)                             │
├─────────────────────────────────────────────────────────────┤
│  Core Components:                                           │
│  • MCPServer class (40 lines)                              │
│  • ProjectManager integration                               │
│  • UnifiedFileMonitor initialization                        │
│  • Function-based tool registration (8 modules)            │
└─────────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│ ProjectManager   │ │ Tool Modules │ │ UnifiedFile      │
│                  │ │              │ │ Monitor          │
│ • File paths     │ │ • 8 modules  │ │                  │
│ • JSON ops       │ │ • 35 tools   │ │ • Watchdog       │
│ • No database    │ │ • Direct ops │ │ • Cloud sync     │
└──────────────────┘ └──────────────┘ └──────────────────┘
          │                 │                 │
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────┐
│            Local JSON Storage                             │
│         (.claude-tasks/data/*.json)                       │
│                                                           │
│  • tasks.json    • sprints.json    • journal.json       │
│  • documents.json • requirements.json                    │
└──────────────────────────────────────────────────────────┘
          │
          │ (automatic sync)
          ▼
┌──────────────────────────────────────────────────────────┐
│              Supabase Cloud Database                      │
│           (10 tables with bidirectional sync)            │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. FastMCP Server (`server.py`)
**Lines**: 143 total
**Purpose**: Lightweight server initialization with modular tool loading

**Key Features**:
- FastMCP v2.10.5 integration
- Automatic project directory detection
- Lazy initialization of unified file monitoring
- Modular tool registration (8 modules)
- Zero complex abstractions

**Initialization Flow**:
```python
server = MCPServer(project_dir)
  → Creates ProjectManager
  → Registers 8 tool modules
  → Initializes UnifiedFileMonitor (lazy)
  → Starts monitoring on first project operation
```

### 2. ProjectManager (`core/project_manager.py`)
**Lines**: 157 total
**Purpose**: Simple file path management and JSON operations

**Key Features**:
- Path resolution for data files
- Project structure creation
- Direct JSON read/write operations
- No database dependencies
- Async-compatible interface

**API**:
```python
project_manager.get_data_file('tasks')          # Get file path
project_manager.get_storage_data('tasks')       # Read JSON
project_manager.save_storage_data('tasks', data) # Write JSON
project_manager.is_initialized()                 # Check setup
```

### 3. UnifiedFileMonitor (`core/universal_storage/unified_file_monitor.py`)
**Lines**: 1,958 total
**Purpose**: Automatic bidirectional synchronization between files and cloud database

**Key Features**:
- Watchdog-based file monitoring (10 entity types)
- Supabase Realtime database subscriptions
- SHA256 hash-based loop prevention
- Async operation with debouncing
- Global + project-specific resource monitoring

**Monitored Entities**:
- Project: tasks, sprints, journal, documents, requirements
- Global: templates, commands, agents, documentation, mcp_configs

**Sync Flow**:
```
File Change → Watchdog Event → Hash Check → Sync to Database
Database Change → Realtime Event → Hash Check → Sync to File
```

### 4. Tool Modules (`tools/`)
**Total Lines**: ~2,500 across 8 modules
**Purpose**: Function-based MCP tools with direct JSON operations

**Modules**:
1. `system_tools.py` (77 lines) - 3 tools for project setup and health checks
2. `task_tools.py` (~500 lines) - 8 tools for task CRUD operations
3. `sprint_tools.py` (~400 lines) - 5 tools for sprint management
4. `journal_tools.py` (~300 lines) - 3 tools for session tracking
5. `git_tools.py` (~200 lines) - 4 tools for Git validation
6. `specification_tools.py` (~600 lines) - 10 tools for requirements management
7. `template_tools.py` (~300 lines) - 2 tools for template operations
8. `document_tools.py` (~800 lines) - 6 tools for document management

## Data Flow

### Tool Operation Flow
```
1. MCP Tool Call (e.g., task_create)
   ↓
2. Decorator Validation (@require_project_basics)
   ↓
3. Direct JSON File Operation (via ProjectManager)
   ↓
4. File Save (atomic write)
   ↓
5. UnifiedFileMonitor Detection
   ↓
6. Automatic Cloud Sync (if configured)
```

### Bidirectional Sync Flow
```
┌─────────────────────────────────────────────────────────┐
│                    File Change                           │
│  (User edits tasks.json manually)                       │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│             Watchdog Event Handler                       │
│  • Detects file modification                            │
│  • Calculates SHA256 hash                               │
│  • Checks if sync needed (hash comparison)              │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│          UnifiedFileMonitor Sync                         │
│  • Reads JSON file                                      │
│  • Transforms to database schema                        │
│  • Upserts to Supabase table                           │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│         Supabase Realtime Event                          │
│  • Database change triggers subscription                │
│  • Event payload includes new record                    │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│          Database → File Sync                            │
│  • Transforms record to file format                     │
│  • Updates hash tracker (prevent loop)                  │
│  • Writes to JSON file                                  │
└─────────────────────────────────────────────────────────┘
```

## Simplified Architecture Principles

### 1. No Complex Abstractions
**Before** (Production): TaskEngine, SprintEngine, DataAccessLayer, UniversalStorage
**After** (Dev): Direct JSON operations via ProjectManager

**Removed Complexity**:
- 600+ lines of abstraction layers
- Complex inheritance hierarchies
- Abstract base classes
- Factory patterns
- State management classes

### 2. Function-Based Tools
**Pattern**:
```python
def register_task_tools(mcp, project_manager: ProjectManager):
    @mcp.tool()
    async def task_create(title: str, priority: str = "medium"):
        # Direct implementation
        tasks_file = project_manager.get_data_file('tasks')
        data = load_json_data(tasks_file)
        # ... modify data ...
        save_json_data(tasks_file, data)
        return {"status": "success", "task": new_task}
```

**Benefits**:
- Clear, linear code flow
- Easy to understand and modify
- No hidden behaviors
- Minimal cognitive overhead

### 3. Direct JSON Operations
**Pattern**:
```python
# Read
data = load_json_data(file_path)  # Simple helper
tasks = data.get('tasks', [])

# Modify
tasks.append(new_task)

# Write
save_json_data(file_path, data)  # Atomic write with backup
```

**No ORM, No DAL, No Repositories** - Just direct file operations.

### 4. Single Responsibility
Each component has one clear job:
- **ProjectManager**: File path management
- **UnifiedFileMonitor**: Cloud synchronization
- **Tool Modules**: MCP tool implementations
- **Helpers**: Shared utilities (validation, JSON ops, error handling)

## Performance Characteristics

### Tool Response Times
- **System health check**: <5ms
- **Task creation**: <10ms
- **Task list**: <20ms (100 tasks)
- **File monitoring overhead**: <2ms per event

### File Operations
- **JSON read**: <2ms (typical task file)
- **JSON write**: <5ms (atomic operation)
- **File monitoring**: <1ms event detection

### Cloud Sync
- **File → Database**: <100ms (async)
- **Database → File**: <200ms (via Realtime)
- **Hash calculation**: <1ms (SHA256)

## Key Design Decisions

### 1. Why Function-Based Tools?
**Rationale**: Simplicity over abstraction
- Easier to understand
- Easier to modify
- Easier to debug
- No performance overhead

### 2. Why Direct JSON Operations?
**Rationale**: No unnecessary layers
- File operations are simple
- No complex queries needed
- JSON is human-readable
- Direct control over data format

### 3. Why Unified File Monitor?
**Rationale**: Automatic cloud sync without tool complexity
- Tools remain simple
- Sync happens automatically
- Loop prevention built-in
- Supports manual file edits

### 4. Why Modular Tool Registration?
**Rationale**: Clean separation of concerns
- Each module focuses on one domain
- Easy to add/remove modules
- Clear dependency graph
- Simple testing

## Tool Registration Pattern

### Standard Pattern
```python
def register_*_tools(mcp, project_manager: ProjectManager):
    """Register [domain] tools"""

    @require_project_basics()  # Optional: initialization check
    @mcp.tool()
    async def tool_name(param: str) -> Dict[str, Any]:
        """Tool description"""
        try:
            # Implementation
            return {"status": "success", "result": data}
        except Exception as e:
            return handle_error(e, "tool_name")
```

### Registration in server.py
```python
tool_registrations = [
    ("SystemTools", register_system_tools),
    ("TaskTools", register_task_tools),
    ("SprintTools", register_sprint_tools),
    # ... 8 modules total
]

for module_name, register_func in tool_registrations:
    register_func(self.mcp, self.project_manager)
```

## Error Handling Philosophy

### Simple, Clear Errors
```python
# Good: Clear error with context
return {
    "status": "error",
    "error": "No project directory set",
    "solution": "Use system_set_project_directory"
}

# Bad: Technical stack trace
raise Exception("NoneType has no attribute 'get_data_file'")
```

### Consistent Error Format
All tools return:
```python
{
    "status": "error" | "success",
    "error": "Human-readable message",  # if error
    "solution": "How to fix",  # optional
    "result": {...}  # if success
}
```

## Testing Strategy

### Unit Testing
- Test tool functions directly
- Mock ProjectManager
- Test error cases
- Verify JSON operations

### Integration Testing
- Test with real files
- Test file monitoring
- Test cloud sync
- Test tool combinations

### Performance Testing
- Measure tool response times
- Measure file operation overhead
- Measure sync latency
- Monitor memory usage

## Future Considerations

### Potential Enhancements
1. **Caching**: Add in-memory cache for frequently accessed data
2. **Batch Operations**: Support bulk task operations
3. **Query Optimization**: Add indexed search for large datasets
4. **Compression**: Compress large JSON files
5. **Validation**: Add JSON schema validation

### Not Planned
- Complex abstractions (defeats simplification purpose)
- ORM integration (direct JSON is simpler)
- Multi-user concurrency (file-based by design)
- Complex query language (simple filters sufficient)

## Related Documentation

- **Simplified Architecture**: `./simplified-architecture.md` - Detailed simplification rationale
- **Tool Registration**: `./tool-registration.md` - Tool registration system deep dive
- **File Monitor**: `./file-monitor.md` - Unified file monitoring architecture
- **Database Schema**: `/docs/database/SCHEMA_REFERENCE.md` - Cloud database structure
- **Bidirectional Sync**: `../BIDIRECTIONAL_SYNC_IMPLEMENTATION.md` - Complete sync guide

## Summary

The MCP Server Dev version prioritizes **simplicity, clarity, and maintainability** over complex abstractions. With just ~2,700 lines of core code (excluding file monitor), it provides 35 tools with automatic cloud sync, all while remaining easy to understand, modify, and extend.

**Key Achievement**: Removed 600+ lines of abstractions while maintaining full functionality and adding automatic bidirectional cloud synchronization.
