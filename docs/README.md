# MCP Server Dev - Documentation Index

Welcome to the MCP Server Dev documentation! This simplified version provides 35 MCP tools for task management with bidirectional cloud synchronization.

## 📚 Quick Navigation

### 🎯 Getting Started
- **[Root README](../README.md)** - Quick start and setup instructions
- **[Agent Orientation](./agent-orientation/README.md)** - How AI agents should use this system

### 🏗️ Architecture
- **[Architecture Overview](./architecture/README.md)** - High-level system design
- **[Simplified Architecture](./architecture/simplified-architecture.md)** - Why function-based approach
- **[Tool Registration](./architecture/tool-registration.md)** - How tools are registered
- **[File Monitor](./architecture/file-monitor.md)** - Bidirectional sync system

### 🛠️ Tools Reference
- **[Tools Overview](./tools/README.md)** - All 35 tools documented
- **[System Tools](./tools/system-tools.md)** - Project setup and health (3 tools)
- **[Task Tools](./tools/task-tools.md)** - Task management (8 tools)
- **[Sprint Tools](./tools/sprint-tools.md)** - Sprint operations (5 tools)
- **[Journal Tools](./tools/journal-tools.md)** - Session tracking (3 tools)
- **[Git Tools](./tools/git-tools.md)** - Git validation (4 tools)
- **[Specification Tools](./tools/specification-tools.md)** - Requirements (10 tools)
- **[Template Tools](./tools/template-tools.md)** - Template operations (2 tools)
- **[Document Tools](./tools/document-tools.md)** - Document management (6 tools)
- **[Tools Summary](./tools/TOOLS_SUMMARY.md)** - Complete tools list

### 💻 Development
- **[Development Guide](./development/README.md)** - How to develop for this system
- **[Adding Tools](./development/adding-tools.md)** - Step-by-step tool creation

### 🤖 Agent Guides
- **[Agent README](./agent-orientation/README.md)** - Complete agent orientation
- **[Workflow Patterns](./agent-orientation/workflow.md)** - Common agent workflows
- **[Best Practices](./agent-orientation/best-practices.md)** - Development guidelines

### 🧪 Testing
- **[Testing Guide](./testing/README.md)** - Complete testing infrastructure

### 📜 History
- **[History Index](./history/README.md)** - Archived implementation summaries
- **[Consolidations](./history/consolidations.md)** - Consolidation milestones
- **[Implementations](./history/implementations.md)** - Implementation history

## 🔍 Documentation Structure

```
docs/
├── README.md                      # This file - documentation index
├── architecture/                  # System design and architecture
│   ├── README.md                  # Architecture overview
│   ├── simplified-architecture.md # Function-based approach
│   ├── tool-registration.md       # Tool registration patterns
│   └── file-monitor.md            # Bidirectional sync system
├── development/                   # Developer guides
│   ├── README.md                  # Development overview
│   └── adding-tools.md            # Creating new tools
├── tools/                         # All 35 MCP tools documented
│   ├── README.md                  # Tools overview
│   ├── system-tools.md            # 3 system tools
│   ├── task-tools.md              # 8 task tools
│   ├── sprint-tools.md            # 5 sprint tools
│   ├── journal-tools.md           # 3 journal tools
│   ├── git-tools.md               # 4 git tools
│   ├── specification-tools.md     # 10 specification tools
│   ├── template-tools.md          # 2 template tools
│   ├── document-tools.md          # 6 document tools
│   └── TOOLS_SUMMARY.md           # Complete tools list
├── agent-orientation/             # AI agent guides
│   ├── README.md                  # Agent orientation
│   ├── workflow.md                # Agent workflow patterns
│   └── best-practices.md          # Development best practices
├── testing/                       # Testing documentation
│   └── README.md                  # Testing guide
└── history/                       # Archived documentation
    ├── README.md                  # History index
    ├── consolidations.md          # Consolidation milestones
    ├── implementations.md         # Implementation summaries
    └── originals/                 # Original archived files
```

## 🎯 Common Use Cases

### For New Users
1. Start with [Root README](../README.md) for quick setup
2. Read [Agent Orientation](./agent-orientation/README.md) for usage patterns
3. Browse [Tools Overview](./tools/README.md) to see what's available

### For Developers
1. Review [Architecture Overview](./architecture/README.md) to understand the system
2. Follow [Development Guide](./development/README.md) for setup
3. Use [Adding Tools](./development/adding-tools.md) when creating new features

### For AI Agents
1. Start with [Agent README](./agent-orientation/README.md) for orientation
2. Follow [Workflow Patterns](./agent-orientation/workflow.md) for common tasks
3. Reference [Best Practices](./agent-orientation/best-practices.md) for quality work

## 📊 System Statistics

- **Total Tools**: 35 across 8 categories
- **Code Size**: ~2,700 lines (core server + tools)
- **File Monitor**: ~1,958 lines (bidirectional sync)
- **Test Coverage**: 100% (35/35 tools passing)
- **Architecture**: Function-based, no complex abstractions
- **Storage**: Direct JSON operations with automatic cloud sync

## 🔗 External References

- **Database Schema**: See `/docs/database/SCHEMA_REFERENCE.md` in parent project
- **Bidirectional Sync**: `../BIDIRECTIONAL_SYNC_IMPLEMENTATION.md` - Complete sync guide
- **Main Project**: Located at `/home/dev/.claude/task-sprint-system/`

## 📝 Documentation Notes

This documentation is organized by **concern** rather than by file structure:
- **Architecture** docs explain the "why" and "how"
- **Tools** docs are reference material
- **Agent** docs are practical guides
- **History** docs are for context only

All documentation is written for both human developers and AI agents working with this system.

## 🆘 Need Help?

- **Setup Issues**: Check [Root README](../README.md) setup section
- **Tool Usage**: See specific tool category in [tools/](./tools/)
- **Agent Workflows**: Review [Agent Orientation](./agent-orientation/)
- **Architecture Questions**: Read [Architecture](./architecture/) docs
- **Development Help**: Follow [Development Guide](./development/)

## 📅 Last Updated

Documentation structure last updated: 2025-10-07

---

*This is the MCP Server **Dev** version - a simplified architecture with function-based tools and direct JSON operations. For the production version, see the parent `mcp-server/` directory.*
