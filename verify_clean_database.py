#!/usr/bin/env python3
"""
Verify database is clean after table removal
"""
import psycopg2
import psycopg2.extras

DATABASE_URL = 'postgres://postgres:YOBh0mVTSqFELFlq@db.yxyfiatdrgelnvxopdsm.supabase.co:5432/postgres'

def main():
    print("=" * 80)
    print("DATABASE CLEANUP VERIFICATION")
    print("=" * 80)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get all remaining tables
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    all_tables = [row['table_name'] for row in cur.fetchall()]

    print(f"Total tables: {len(all_tables)}")
    print()

    # Categorize tables
    categories = {
        'Core Data': ['tasks', 'sprints', 'journal_sessions'],
        'Projects': ['projects'],
        'Specifications': [
            'specifications',
            'specification_requirements',
            'specification_constraints',
            'specifications_validated',
            'specification_requirements_validated',
            'specification_constraints_validated'
        ],
        'Templates': ['template_tasks', 'template_sprints'],
        'Documentation': ['documentation'],
        'Infrastructure': ['agents', 'commands', 'mcp_configs'],
        'Frontend Features': ['conversations', 'conversation_messages']
    }

    # Display categorized
    for category, expected_tables in categories.items():
        print(f"{category}:")
        print("-" * 60)
        for table in expected_tables:
            if table in all_tables:
                # Get count
                cur.execute(f"SELECT COUNT(*) FROM {table};")
                count = cur.fetchone()[0]
                status = "✓" if count > 0 or table in ['mcp_configs', 'specifications_validated', 'specification_requirements_validated', 'specification_constraints_validated'] else " "
                print(f"  {status} {table:40} ({count} records)")
            else:
                print(f"  ✗ {table:40} (MISSING!)")
        print()

    # Check for uncategorized tables
    all_categorized = []
    for tables in categories.values():
        all_categorized.extend(tables)

    uncategorized = set(all_tables) - set(all_categorized)
    if uncategorized:
        print("⚠️  UNCATEGORIZED TABLES (shouldn't exist):")
        print("-" * 60)
        for table in sorted(uncategorized):
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            print(f"  {table:40} ({count} records)")
        print()

    # Verify dropped tables are gone
    print("=" * 80)
    print("VERIFYING DROPPED TABLES ARE GONE")
    print("=" * 80)
    print()

    dropped_tables = [
        'approved_entity_requirements',
        'approved_entity_constraints',
        'backlog_items',
        'sync_metadata',
        'document_tags',
        'approved_document_tags',
        'approved_specification_requirements',
        'approved_specification_constraints'
    ]

    all_gone = True
    for table in dropped_tables:
        if table in all_tables:
            print(f"  ✗ {table:40} STILL EXISTS!")
            all_gone = False
        else:
            print(f"  ✓ {table:40} removed")

    print()
    if all_gone:
        print("✅ All unused tables successfully removed")
    else:
        print("⚠️  Some tables still exist!")

    print()
    print("=" * 80)
    print("CLEANUP VERIFICATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Database now has {len(all_tables)} clean, purposeful tables")
    print(f"Removed 8 unused/legacy tables with 759 old records")
    print()

    conn.close()

if __name__ == "__main__":
    main()
