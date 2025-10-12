# MCP Task Management Server - Dev Version

**Simplified MCP server with 35 tools across 8 categories**

[![Tests](https://img.shields.io/badge/tests-35%2F35%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()
[![Architecture](https://img.shields.io/badge/architecture-simplified-blue)]()

## Quick Start

```bash
# Run the server
python3 server.py --project-dir "$(pwd)"

# Run tests
python3 test_all_mcp_tools_direct.py
```

## Features

- **35 MCP Tools** - Complete task/sprint management
- **Simplified Architecture** - Function-based, no abstractions
- **Bidirectional Sync** - Files ↔ Database automatic
- **100% Test Coverage** - All tools tested and passing

## Tools Overview

| Category | Tools | Description |
|----------|-------|-------------|
| **System** | 3 | Project setup, health check, context |
| **Task** | 6 | Create, update, search, manage tasks |
| **Sprint** | 5 | Sprint management and organization |
| **Journal** | 3 | Work session tracking |
| **Git** | 2 | Git session management |
| **Specification** | 5 | Requirements and specifications |
| **Template** | 6 | Task and sprint templates |
| **Document** | 5 | Documentation management |

## Architecture

**Simplified Design**:
- Function-based tool registration
- Direct JSON file operations  
- Unified file monitoring for sync
- 68% less code than production version

**Performance**:
- <10ms most operations
- <100ms database sync
- <1s full test suite

## Documentation

📖 **Complete documentation in `docs/`**:

- **[Documentation Index](docs/README.md)** - Start here
- **[Architecture](docs/architecture/)** - System design (4 files)
- **[Development](docs/development/)** - Developer guides (2 files)
- **[Tools Reference](docs/tools/)** - All 35 tools (10 files)
- **[Agent Orientation](docs/agent-orientation/)** - AI agent guides (3 files)
- **[Testing](docs/testing/)** - Test guide (1 file)

## For AI Agents

See **[CLAUDE.md](CLAUDE.md)** for quick reference and **[Agent Orientation](docs/agent-orientation/)** for complete workflow guides.

## Development

See **[Development Guide](docs/development/README.md)** for:
- Project structure
- Adding new tools
- Code patterns
- Testing approach

## Testing

```bash
python3 test_all_mcp_tools_direct.py
```

Expected: 35/35 tools passing (100% coverage)

See **[Testing Guide](docs/testing/README.md)** for details.

## Structure

```
mcp-server-dev/
├── README.md              # This file
├── CLAUDE.md              # Agent reference
├── server.py              # Main server
├── tools/                 # 8 tool modules
├── core/                  # Core functionality
├── utils/                 # Utilities
├── docs/                  # All documentation
├── test_*.py              # Test suite
└── supabase/              # Database
```

## License

See [LICENSE](LICENSE) for details.

---

**Status**: Production-ready ✅ | **Tests**: 35/35 passing ✅ | **Docs**: Complete ✅
