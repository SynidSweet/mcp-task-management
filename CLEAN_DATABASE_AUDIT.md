# Clean Database Audit - Corrected Analysis

**Date**: 2025-10-28
**Purpose**: Identify truly unused tables for removal

---

## Tables in Database (26 total)

### ✅ ACTIVELY USED (Keep) - 16 Tables

**Core Data** (synced from JSON files via UnifiedFileMonitor):
- `tasks` - 22 records - Core task management
- `sprints` - 5 records - Sprint management
- `journal_sessions` - 2 records - Session tracking

**Documentation**:
- `documentation` - 18 records - Synced from /docs/*.md files

**Specifications** (MCP tools exist):
- `specifications` - 16 records
- `specification_requirements` - 47 records
- `specification_constraints` - 27 records

**Specification Validation** (AI suggestions vs human approval):
- `specifications_validated` - 0 records (empty but used)
- `specification_requirements_validated` - 0 records (empty but used)
- `specification_constraints_validated` - 0 records (empty but used)

**Templates** (MCP tools exist):
- `template_tasks` - 29 records
- `template_sprints` - 5 records

**Infrastructure** (synced by UnifiedFileMonitor):
- `projects` - 2 records - Project metadata
- `agents` - 5 records - Synced from .claude/agents/*.md
- `commands` - 7 records - Synced from .claude/commands/*.md
- `mcp_configs` - 0 records - Syncs .claude-mcp-config.json (**KEEP THIS!**)

---

### ❌ SAFE TO REMOVE - 6 Tables

**Empty, no tools, no sync**:
1. `backlog_items` - Planned feature never implemented
2. `sync_metadata` - Old sync tracking (not used)
3. `document_tags` - Feature not implemented
4. `approved_document_tags` - Feature not implemented
5. `approved_specification_requirements` - Duplicate/old validation system
6. `approved_specification_constraints` - Duplicate/old validation system

---

### ⚠️ NEEDS INVESTIGATION - 4 Tables

**Have data but unclear purpose**:
1. `approved_entity_requirements` - 385 records
2. `approved_entity_constraints` - 374 records
3. `conversations` - 60 records
4. `conversation_messages` - 111 records

**Questions**:
- Are these used by frontend?
- Are these from an old/deprecated system?
- Is "entity" a different system than "specifications"?
- What are "conversations" for?

---

## Corrected Recommendations

### Immediate Removal (Safe) - 6 Tables

```sql
DROP TABLE IF EXISTS backlog_items CASCADE;
DROP TABLE IF EXISTS sync_metadata CASCADE;
DROP TABLE IF EXISTS document_tags CASCADE;
DROP TABLE IF EXISTS approved_document_tags CASCADE;
DROP TABLE IF EXISTS approved_specification_requirements CASCADE;
DROP TABLE IF EXISTS approved_specification_constraints CASCADE;
```

**Impact**: None - all empty, no tools, no sync

### Needs User Decision - 4 Tables

Before removing these, need to know:
- Are they used by frontend?
- What is the "entity" system? (approved_entity_*)
- What are conversations for?

---

## My Mistake - Apologies!

**mcp_configs**: I incorrectly flagged this as unused. It's actually:
- ✅ Used by UnifiedFileMonitor
- ✅ Syncs .claude-mcp-config.json
- ✅ Part of active bidirectional sync system
- Empty because file hasn't been synced yet (not because it's unused)

**Lesson**: Need to check sync code, not just MCP tools and data counts.

---

## Questions for You

1. **Entity system**: Do you know what `approved_entity_requirements` and `approved_entity_constraints` are? Are they from an old/deprecated requirements system?

2. **Conversations**: What is the conversations system? Frontend feature? Old chat system?

3. **Proceed with safe removals?** Can I remove the 6 definitely unused tables?

