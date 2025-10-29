#!/usr/bin/env python3
"""
Smart audit of database tables considering the architecture
"""
import psycopg2
import psycopg2.extras

DATABASE_URL = 'postgres://postgres:YOBh0mVTSqFELFlq@db.yxyfiatdrgelnvxopdsm.supabase.co:5432/postgres'

def main():
    print("=" * 80)
    print("SMART DATABASE TABLE AUDIT")
    print("=" * 80)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get all tables
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    all_tables = [row['table_name'] for row in cur.fetchall()]

    # Get data counts
    table_counts = {}
    for table in all_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            table_counts[table] = cur.fetchone()[0]
        except:
            table_counts[table] = 0

    # Categorize tables based on architecture knowledge
    categories = {
        'Core Data (via JSON files)': [
            'tasks',           # Used via tasks.json
            'sprints',         # Used via sprints.json
            'journal_sessions', # Used via journal.json
        ],
        'Documentation': [
            'documentation',   # Used via document tools
        ],
        'Specifications (MCP tools)': [
            'specifications',
            'specification_requirements',
            'specification_constraints',
        ],
        'Specification Validation': [
            'specifications_validated',
            'specification_requirements_validated',
            'specification_constraints_validated',
        ],
        'Templates (MCP tools)': [
            'template_tasks',
            'template_sprints',
        ],
        'System/Infrastructure': [
            'projects',        # Project metadata
            'agents',          # From UnifiedFileMonitor
            'commands',        # From UnifiedFileMonitor
        ],
        'Potentially Unused': [
            'backlog_items',               # No tools, no data
            'sync_metadata',               # No tools, no data
            'mcp_configs',                 # No tools, no data
            'document_tags',               # No tools, no data
            'approved_document_tags',      # No tools, no data
            'approved_specification_requirements',  # Duplicate of spec validation?
            'approved_specification_constraints',   # Duplicate of spec validation?
            'approved_entity_requirements',        # Entity system (no MCP tools)
            'approved_entity_constraints',         # Entity system (no MCP tools)
            'conversations',               # Unknown purpose
            'conversation_messages',       # Unknown purpose
        ]
    }

    # Display categorized
    for category, tables in categories.items():
        print(f"\n{category}:")
        print("-" * 60)
        for table in tables:
            if table in all_tables:
                count = table_counts.get(table, 0)
                status = "✓" if count > 0 else " "
                print(f"  {status} {table:40} ({count} records)")
            else:
                print(f"  ✗ {table:40} (doesn't exist)")

    # Find any uncategorized tables
    all_categorized = set()
    for tables in categories.values():
        all_categorized.update(tables)

    uncategorized = set(all_tables) - all_categorized
    if uncategorized:
        print(f"\nUncategorized:")
        print("-" * 60)
        for table in sorted(uncategorized):
            count = table_counts.get(table, 0)
            print(f"  ? {table:40} ({count} records)")

    # Recommend tables to remove
    print()
    print("=" * 80)
    print("REMOVAL RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Empty unused tables
    empty_unused = [t for t in categories['Potentially Unused'] if table_counts.get(t, 0) == 0]
    if empty_unused:
        print("✅ SAFE TO REMOVE (Empty, no tools):")
        for table in empty_unused:
            if table in all_tables:
                print(f"  - {table}")
        print()

    # Tables with data but questionable
    data_unused = [t for t in categories['Potentially Unused'] if table_counts.get(t, 0) > 0]
    if data_unused:
        print("⚠️  REVIEW BEFORE REMOVING (Has data):")
        for table in data_unused:
            if table in all_tables:
                count = table_counts.get(table, 0)
                print(f"  - {table} ({count} records)")
        print()

    conn.close()

    print("Next steps:")
    print("  1. Review recommendations above")
    print("  2. Confirm tables to remove")
    print("  3. Run cleanup migration")

if __name__ == "__main__":
    main()
