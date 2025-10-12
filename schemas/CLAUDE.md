# Schema Management System

*Last updated: 2025-08-07 | Created CLAUDE.md for improved AI assistance with schema validation and JSON structure*

## 🎯 Purpose
Simple JSON schema definitions for the MCP Task Management Server. Basic validation for data structure consistency.

## 🏗️ Key Components

### **journal_validator.py** - Basic JSON Validation
- **Purpose**: Simple validation for journal.json structure
- **Usage**: Basic schema checking for JSON data integrity

### **journal_schema.json** - Journal Data Structure Schema
- **Purpose**: Defines expected journal file structure and field constraints
- **Schema Version**: `journal-v1.0` 
- **Key Sections**: Sessions array, metadata object, field validation rules
- **Validation Rules**: Session ID format, timestamp validation, required fields

## 🔧 Schema Usage

### JSON File Structure
- **tasks.json**: `{"tasks": [...], "metadata": {...}}`
- **sprints.json**: `{"sprints": [...], "metadata": {...}}`
- **journal.json**: `{"sessions": [...], "metadata": {...}}`
- **backlog.json**: `{"backlog": [...], "metadata": {...}}`

### Basic Validation
The simplified server creates these files automatically with proper structure. Manual validation is rarely needed since the operations are direct JSON read/write.