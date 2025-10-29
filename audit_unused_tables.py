#!/usr/bin/env python3
"""
Audit all database tables to identify unused ones
"""
import psycopg2
import psycopg2.extras
from pathlib import Path

DATABASE_URL = 'postgres://postgres:YOBh0mVTSqFELFlq@db.yxyfiatdrgelnvxopdsm.supabase.co:5432/postgres'

def main():
    print("=" * 80)
    print("DATABASE TABLE AUDIT - Identify Unused Tables")
    print("=" * 80)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get all tables
    print("Step 1: List all tables in database")
    print("-" * 80)
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)

    all_tables = [row['table_name'] for row in cur.fetchall()]
    print(f"Found {len(all_tables)} tables:")
    for table in all_tables:
        print(f"  - {table}")

    print()

    # Check which tables have MCP tools
    print("Step 2: Check which tables have MCP tools")
    print("-" * 80)

    # Read all tool files
    tools_dir = Path(__file__).parent / 'tools'
    tool_files = list(tools_dir.glob('*.py'))

    tables_with_tools = set()
    for tool_file in tool_files:
        content = tool_file.read_text()
        for table in all_tables:
            # Look for table references in MCP tools
            if f"table('{table}')" in content or f'table("{table}")' in content:
                tables_with_tools.add(table)

    print(f"Tables with MCP tools: {len(tables_with_tools)}")
    for table in sorted(tables_with_tools):
        print(f"  ✓ {table}")

    print()

    # Check which tables have data
    print("Step 3: Check which tables have data")
    print("-" * 80)

    tables_with_data = {}
    for table in all_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            tables_with_data[table] = count
        except Exception as e:
            tables_with_data[table] = f"Error: {e}"

    print(f"Table data counts:")
    for table, count in sorted(tables_with_data.items()):
        if isinstance(count, int):
            status = "✓ Has data" if count > 0 else "  Empty"
            print(f"  {status:15} {table:35} ({count} records)")
        else:
            print(f"  ? Error      {table:35} ({count})")

    print()

    # Identify unused tables
    print("Step 4: Identify unused tables")
    print("-" * 80)
    print()

    unused_tables = []
    for table in all_tables:
        has_tool = table in tables_with_tools
        has_data = tables_with_data.get(table, 0) > 0 if isinstance(tables_with_data.get(table), int) else False

        if not has_tool and not has_data:
            unused_tables.append(table)
            print(f"❌ UNUSED: {table}")
            print(f"   - No MCP tools")
            print(f"   - No data")
            print()

    # Also flag tables with no tools but have data (may be legacy)
    legacy_tables = []
    for table in all_tables:
        has_tool = table in tables_with_tools
        has_data = tables_with_data.get(table, 0) > 0 if isinstance(tables_with_data.get(table), int) else False

        if not has_tool and has_data:
            legacy_tables.append(table)
            print(f"⚠️  LEGACY: {table}")
            print(f"   - No MCP tools (but has {tables_with_data[table]} records)")
            print()

    # Also check for deprecated tables mentioned in migrations
    print("Step 5: Check for deprecated tables mentioned in migrations")
    print("-" * 80)
    print()

    deprecated_keywords = ['deprecated', 'old', 'legacy', 'unused', 'drop']
    migrations_dir = Path(__file__).parent / 'supabase' / 'migrations'

    deprecated_mentions = {}
    for migration_file in migrations_dir.glob('*.sql'):
        content = migration_file.read_text().lower()
        for keyword in deprecated_keywords:
            if keyword in content:
                for table in all_tables:
                    if table.lower() in content and keyword in content:
                        if table not in deprecated_mentions:
                            deprecated_mentions[table] = []
                        deprecated_mentions[table].append(migration_file.name)

    if deprecated_mentions:
        print("Tables mentioned in migration comments as deprecated/old:")
        for table, migrations in deprecated_mentions.items():
            print(f"  - {table}: {', '.join(set(migrations)[:2])}")
    else:
        print("  No specific deprecated mentions found")

    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    print(f"Total tables: {len(all_tables)}")
    print(f"Tables with MCP tools: {len(tables_with_tools)}")
    print(f"Tables with data: {sum(1 for c in tables_with_data.values() if isinstance(c, int) and c > 0)}")
    print(f"Empty unused tables: {len(unused_tables)}")
    print(f"Legacy tables (data but no tools): {len(legacy_tables)}")
    print()

    if unused_tables:
        print("=" * 80)
        print("RECOMMENDED FOR REMOVAL (Unused Tables)")
        print("=" * 80)
        for table in unused_tables:
            print(f"  - {table}")
        print()

    if legacy_tables:
        print("=" * 80)
        print("REVIEW RECOMMENDED (Legacy Tables)")
        print("=" * 80)
        for table in legacy_tables:
            count = tables_with_data.get(table, 0)
            print(f"  - {table} ({count} records - may need data migration)")
        print()

    conn.close()

    # Generate drop statements
    if unused_tables:
        print("=" * 80)
        print("DROP STATEMENTS FOR UNUSED TABLES")
        print("=" * 80)
        print()
        for table in unused_tables:
            print(f"DROP TABLE IF EXISTS {table} CASCADE;")
        print()

if __name__ == "__main__":
    main()
