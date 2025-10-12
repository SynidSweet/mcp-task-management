# Task Management System Schemas

## Overview

This directory contains JSON schema definitions and validation utilities for the task management system data structures.

## Schema Files

### journal_schema.json
**Purpose**: Defines the structure for session journaling data in `.claude-tasks/journal.json`

**Key Features**:
- Session entry format with structured data capture
- Metadata tracking for journal management
- Validation for session IDs, timestamps, and data integrity
- Support for task work tracking and issue documentation

**Session Structure**:
```json
{
  "session_id": "sess-YYYY-MM-DD-NNN",
  "timestamp": "ISO-8601 datetime",
  "session_type": "carry-on|investigation|refactor|planning|document|migrate",
  "duration_minutes": number,
  "tasks_worked": [
    {
      "task_id": "TASK-YYYY-NNN", 
      "status_change": "started|completed|blocked|progressed|abandoned",
      "work_summary": "description of work performed"
    }
  ],
  "key_achievements": ["string array of major accomplishments"],
  "discoveries": ["string array of insights or learnings"],
  "technical_decisions": ["string array of technical choices made"],
  "issues_encountered": [
    {
      "description": "issue description",
      "resolution": "how resolved (or null)",
      "follow_up_needed": boolean
    }
  ],
  "next_steps": ["string array of identified next actions"],
  "sprint_progress_impact": "string describing sprint advancement",
  "context_changes": "string describing important context updates"
}
```

### journal_validator.py
**Purpose**: Python validation utilities for journal data

**Key Classes**:
- `JournalValidator`: Core validation logic with comprehensive error reporting
- Validation methods for sessions, task work, issues, and metadata
- Session ID generation with duplicate prevention
- Default data structure creation

**Usage Example**:
```python
from journal_validator import JournalValidator, validate_journal_file

# Validate a journal file
is_valid, errors = validate_journal_file(Path("journal.json"))

# Validate data structure
validator = JournalValidator()
is_valid, errors = validator.validate_journal_structure(data)

# Generate unique session ID
session_id = validator.generate_session_id(existing_sessions)
```

## Validation Features

### Session ID Format
- Pattern: `sess-YYYY-MM-DD-NNN`
- Auto-incrementing daily counters
- Duplicate prevention
- Support for up to 999 sessions per day

### Field Validation
- **Required Fields**: All core session fields must be present
- **String Limits**: Configurable maximum lengths for text fields
- **Array Validation**: Proper structure for tasks_worked and issues_encountered
- **Enum Validation**: Session types and status changes restricted to valid values
- **Date Validation**: ISO-8601 timestamp format validation

### Data Integrity
- **Schema Versioning**: Tracks schema evolution for future migrations
- **Metadata Consistency**: Total session counts and last session tracking
- **Task ID Format**: Validates against established task ID patterns
- **Retention Policies**: Configurable cleanup settings

## Integration with System

### Config Manager Integration
The `ConfigManager` class includes journal file path and initialization:
- `config.journal_file`: Path to journal.json
- `config.ensure_journal_file()`: Creates journal with default structure
- `config.get_data_file_path('journal')`: Returns journal file path

### Data Directory Structure
Journal files are stored in the unified data directory:
- **Location**: `.claude-tasks/data/journal.json`
- **Consistency**: Same location used by CLI and MCP systems
- **Backup Integration**: Included in system backup procedures

### Error Handling
- **Graceful Degradation**: System continues operation with validation warnings
- **Detailed Error Reporting**: Specific field-level error messages
- **Schema Loading**: Handles missing or corrupted schema files
- **File Creation**: Automatic initialization of missing journal files

## Future Enhancements

### Planned Features
- **Advanced Queries**: Session search by task, keyword, or time range
- **Pattern Analysis**: Automatic detection of recurring issues or successful approaches
- **Context Integration**: Enhanced integration with PROJECT_CONTEXT.md updates
- **Performance Metrics**: Session duration and productivity tracking

### Schema Evolution
- **Version Migration**: Support for schema upgrades with data preservation
- **Extended Metadata**: Additional tracking fields as system evolves
- **Integration Points**: Hooks for external analysis tools
- **Archival Policies**: Long-term retention and compression strategies

This schema system provides the foundation for automated session journaling, reducing manual context management while maintaining comprehensive project history and enabling intelligent workflow optimization.