# Data Integrity Checker Tool

**Display ID:** `data_integrity_checker`
**Type:** Validator
**Status:** Specification

## Overview

Automated validation tool to ensure database integrity, verify Dual-ID system consistency, and detect data corruption across all MCP server tables. Validates both hierarchical entities (specifications with parent-child relationships) and flat entities (tasks with workflow dependencies only).

## Purpose

Prevent and detect data integrity issues after schema changes, migrations, or manual database edits. Particularly critical for:
- **Specifications**: Maintaining Dual-ID architecture where `parent_id` (UUID) must stay synchronized with `parent_display_id` (display_id)
- **Tasks**: Maintaining hierarchy integrity with `parent_task_id` and `child_task_ids` (separate from workflow dependencies)

## Requirements

### 1. Dual-ID System Validation
- **Verify parent_id matches parent_display_id**: For each specification with `parent_display_id`, resolve it to UUID and verify it matches `parent_id`
- **Detect mismatches**: Report cases where UUID lookup of `parent_display_id` != stored `parent_id`
- **Check null inconsistencies**: Flag records with `parent_id` but no `parent_display_id` (or vice versa)

### 2. Referential Integrity Checks
- **Orphaned parent_id**: Detect specifications where `parent_id` points to non-existent UUID
- **Orphaned parent_display_id**: Detect specifications where `parent_display_id` points to non-existent display_id
- **Project FK validation**: Verify all `project_id` values reference existing projects
- **Circular references**: Detect circular parent-child relationships

### 3. Uniqueness Validation
- **display_id uniqueness**: Ensure display_ids are unique within project/machine scope
- **UUID uniqueness**: Verify UUID primary keys are globally unique (should be guaranteed by DB)

### 4. Required Field Validation
- **Missing required fields**: Check for NULL values in required columns
  - Specifications: `display_id`, `specification_name`, `specification_type`
  - Tasks: `id`, `title`, `status`, `priority`
  - All entities: `project_id`, `machine_id`

### 5. Architecture Compliance
- **Task hierarchy check**: Verify `parent_task_id` references exist, `child_task_ids` arrays are consistent
- **Task circular references**: Detect circular parent-child relationships in tasks
- **Specification hierarchy check**: Verify specifications properly use parent_id/parent_display_id
- **Dependency structure**: Validate task dependencies use correct JSONB format (`blocks`, `blocked_by`, `related`)

### 6. Global Resource Validation
- **Template validation**: Check template_type required, scope/is_global consistency
- **Command validation**: Check command_name required, content present
- **Agent validation**: Check agent_name required, content present, tools_config structure
- **Documentation validation**: Check file_path required, doc_title present

### 7. Reporting & Statistics
- **Summary metrics**: Total entities checked, issues found by severity
- **Categorized issues**: Group by type (FK violations, Dual-ID mismatches, missing fields)
- **Fix suggestions**: Provide specific repair commands for each issue type

### 8. Repair Capabilities
- **Check-only mode**: Default - no modifications, just reporting
- **Auto-repair mode**: Fix safe issues automatically (requires `--fix` flag)
  - Safe fixes: Update `parent_id` from `parent_display_id` lookup (specifications)
  - Safe fixes: Clear orphaned parent references
  - Safe fixes: Sync child_task_ids arrays with actual parent_task_id values
- **Manual fix mode**: Generate fix scripts for destructive operations

## Constraints

1. **Non-destructive by default**: Check-only mode never modifies data
2. **Explicit confirmation**: Fix mode requires `--fix` flag
3. **Performance**: Complete checks in <30 seconds for typical datasets (<1000 specifications)
4. **Preserve valid data**: Auto-repair only touches corrupted records
5. **Actionable output**: Every issue includes a suggested fix command
6. **Schema-aware**: Validate against actual database schema, not assumptions
7. **Offline support**: Can check local JSON files when database unavailable
8. **Display-id first**: All repairs maintain display_id-first architecture

## Implementation Design

### File Location
`/home/dev/projects/mcp-management-system/dev/mcp-server/check_data_integrity.py`

### Usage
```bash
# Check only (default)
python check_data_integrity.py

# Check with detailed output
python check_data_integrity.py --verbose

# Auto-fix safe issues
python check_data_integrity.py --fix

# Check specific table only
python check_data_integrity.py --table specifications

# Output JSON report
python check_data_integrity.py --format json > integrity_report.json
```

### Output Format

```
╔══════════════════════════════════════════════════════════════╗
║       DATA INTEGRITY CHECK - MCP Task Management System      ║
╚══════════════════════════════════════════════════════════════╝

Project: /home/dev/projects/mcp-management-system/dev/mcp-server
Database: yxyfiatdrgelnvxopdsm.supabase.co
Checked: 2025-10-16 18:45:23

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY
  ✓ Specifications checked: 45
  ✓ Tasks checked: 127
  ✓ Projects checked: 3
  ⚠ Issues found: 3 (2 critical, 1 warning)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 CRITICAL ISSUES

[1] Dual-ID Mismatch - Specification "api_gateway"
    Display ID: api_gateway
    parent_display_id: "backend_services"
    parent_id: null (SHOULD BE: uuid-456...)

    Impact: Hierarchy queries will fail
    Fix: python check_data_integrity.py --fix-dual-id api_gateway

[2] Orphaned Parent Reference - Specification "user_auth"
    parent_id: uuid-789... (NOT FOUND in database)
    parent_display_id: "deleted_module"

    Impact: FK constraint violation, cascade operations broken
    Fix: Update parent to existing specification or set to null

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  WARNINGS

[1] Duplicate Display ID - Specification "user_service"
    Found: 2 specifications with display_id "user_service"
    Project: same-project-id
    Machine: same-machine-id

    Impact: Ambiguous references, query results unpredictable
    Fix: Rename one to unique display_id

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 RECOMMENDATIONS

  • Run with --fix to auto-repair Dual-ID mismatches
  • Review orphaned references manually before fixing
  • Consider running check after every schema migration

Run 'python check_data_integrity.py --help' for options
```

### Check Categories

1. **Dual-ID Integrity** (Critical) - Specifications Only
   - Null `parent_id` with non-null `parent_display_id`
   - `parent_id` doesn't match resolved `parent_display_id`
   - Missing display_id on records

2. **Referential Integrity** (Critical)
   - Orphaned `parent_id` references (specifications)
   - Invalid `project_id` references (all tables)
   - Circular parent-child relationships (specifications)

3. **Architecture Compliance** (Critical)
   - Task hierarchy integrity (orphaned parent_task_id, inconsistent child_task_ids)
   - Task circular references in parent-child relationships
   - Specification hierarchy integrity (Dual-ID synchronization)
   - Invalid dependency structure in tasks

4. **Data Consistency** (Warning)
   - Duplicate display_ids in same project/machine
   - Missing required fields
   - Invalid parent_display_id references (points to non-existent display_id)

5. **Schema Compliance** (Info)
   - Extra fields in local JSON not in database
   - Field type mismatches
   - Deprecated field usage (e.g., `specification_path` column still in DB but unused)

## Validation Logic

### Dual-ID Check Algorithm
```python
for spec in specifications:
    if spec.parent_display_id:
        # Resolve display_id to UUID
        expected_uuid = resolve_specification_id(
            spec.parent_display_id,
            spec.project_id,
            spec.machine_id
        )

        # Compare with stored parent_id
        if spec.parent_id != expected_uuid:
            report_issue(
                severity="CRITICAL",
                type="dual_id_mismatch",
                spec_id=spec.display_id,
                expected=expected_uuid,
                actual=spec.parent_id
            )
```

### Auto-Repair Logic
```python
def repair_dual_id_mismatch(spec):
    """Safe auto-repair: Update parent_id from parent_display_id lookup."""
    if spec.parent_display_id:
        parent_uuid = resolve_specification_id(
            spec.parent_display_id,
            spec.project_id,
            spec.machine_id
        )
        if parent_uuid:
            # Safe update - just syncing the UUID
            update_specification(
                spec.id,
                parent_id=parent_uuid
            )
            return True
    return False
```

## Success Criteria

- Tool runs without errors on empty database
- Detects all constraint types listed in requirements (Dual-ID, FK, uniqueness, required fields)
- Provides actionable fix suggestions for every issue
- Auto-repair mode fixes Dual-ID mismatches without data loss
- Completes checks in under 10 seconds for 100 specifications
- Integrates with CI/CD pipeline (exit code 0 = pass, 1 = issues found)

## Database Cleanup Note

The `specification_path` column still exists in the database but is completely unused:
- All code ignores this field
- Sync system doesn't write to it
- Output formatters don't show it
- Can be safely dropped via migration: `ALTER TABLE specifications DROP COLUMN specification_path;`

## Future Enhancements

- **Pre-migration checks**: Run before schema changes to detect breaking changes
- **Continuous monitoring**: Scheduled integrity checks with alerting
- **Local JSON validation**: Check local files before sync to database
- **Integrity test suite**: Automated tests that intentionally corrupt data and verify detection
- **Repair audit log**: Track all auto-repairs with before/after snapshots
- **Schema cleanup detection**: Flag unused database columns for removal
