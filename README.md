# MCP Server - Simplified Architecture

**Database Schema:** See `../SCHEMA.md` (canonical schema documentation shared with frontend)

A **simplified MCP (Model Context Protocol) server** providing 35 tools for task/sprint management. Built with a function-based architecture emphasizing directness over abstraction.

**Key Stats**: 35 tools across 8 categories | 100% test coverage | ~68% less code than production version

## Quick Commands

```bash
# Run the server
python server.py --project-dir "$(pwd)"

# Run all tests (expect 35/35 passing)
python test_all_mcp_tools_direct.py

# Run database readiness check
python test_database_readiness.py

# Verify auto-sync is working
python verify_auto_sync.py
```

## Documentation

- **Complete Documentation:** See `CLAUDE.md` in this directory
- **Database Schema:** See `../SCHEMA.md` (shared with frontend)
- **Architecture Overview:** See `../DATABASE_ARCHITECTURE.md`
- **Sync Verification:** See `SYNC_VERIFICATION_SUMMARY.md`

## What This Server Does

Provides MCP tools for:
- Task management (create, update, search, delete)
- Sprint planning (templates, tracking, updates)
- Journal/session tracking
- Specifications/requirements management
- Document management
- Template management
- Git session tools

All data syncs automatically between local JSON files and Supabase database.

## For Complete Information

See `CLAUDE.md` for:
- Architecture philosophy
- Tool development patterns
- Code structure
- Testing approach
- Common pitfalls
- Design trade-offs

---

**Last Updated:** 2025-10-12
