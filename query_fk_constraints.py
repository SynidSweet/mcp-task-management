#!/usr/bin/env python3
"""
Query database for actual FK constraint names using psycopg2
Requires: PostgreSQL connection string (DATABASE_URL)
"""
import sys

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("✗ psycopg2 not installed")
    print("  Run: ./venv/bin/python3 -m pip install psycopg2-binary")
    sys.exit(1)

def main():
    print("=" * 80)
    print("QUERY FOREIGN KEY CONSTRAINTS - Direct PostgreSQL Access")
    print("=" * 80)
    print()

    # Get DATABASE_URL from environment or ask user
    import os
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        print("DATABASE_URL not found in environment.")
        print()
        print("Please provide the PostgreSQL connection string from Supabase:")
        print("  1. Go to: https://yxyfiatdrgelnvxopdsm.supabase.co")
        print("  2. Settings → Database → Connection String")
        print("  3. Look for 'URI' or 'Connection pooling' string")
        print("  4. Format: postgres://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres")
        print()
        print("You can:")
        print("  a) Set environment variable: export DATABASE_URL='postgres://...'")
        print("  b) Pass as argument: python3 query_fk_constraints.py 'postgres://...'")
        print()

        if len(sys.argv) > 1:
            database_url = sys.argv[1]
            print(f"Using connection string from argument")
        else:
            sys.exit(1)

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        print("✓ Connected successfully")
        print()

        # Query FK constraints
        print("-" * 80)
        print("FOREIGN KEY CONSTRAINTS TO PROJECTS TABLE")
        print("-" * 80)
        print()

        query = """
        SELECT
            tc.table_name,
            tc.constraint_name,
            STRING_AGG(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns,
            COUNT(kcu.column_name) as column_count
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'projects'
          AND tc.table_schema = 'public'
        GROUP BY tc.table_name, tc.constraint_name
        ORDER BY tc.table_name;
        """

        cur.execute(query)
        rows = cur.fetchall()

        if not rows:
            print("✓ No FK constraints found (all already dropped or none exist)")
        else:
            print(f"Found {len(rows)} FK constraint(s):")
            print()
            for row in rows:
                print(f"  Table: {row['table_name']}")
                print(f"  Constraint: {row['constraint_name']}")
                print(f"  Columns: {row['columns']} ({row['column_count']} columns)")
                print()

        # Also check projects table PRIMARY KEY
        print("-" * 80)
        print("PROJECTS TABLE PRIMARY KEY")
        print("-" * 80)
        print()

        pk_query = """
        SELECT
            kcu.column_name,
            kcu.ordinal_position
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'projects'
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position;
        """

        cur.execute(pk_query)
        pk_rows = cur.fetchall()

        if pk_rows:
            pk_columns = [row['column_name'] for row in pk_rows]
            print(f"Primary key columns: {', '.join(pk_columns)}")

            if len(pk_columns) == 2 and set(pk_columns) == {'id', 'machine_id'}:
                print("✓ Composite PRIMARY KEY (id, machine_id) exists!")
            elif len(pk_columns) == 1 and pk_columns[0] == 'id':
                print("✗ Single-column PRIMARY KEY (id) - needs to be composite")
            else:
                print(f"? Unexpected PRIMARY KEY: {pk_columns}")
        else:
            print("⚠️  No PRIMARY KEY found on projects table!")

        print()

        # Check UNIQUE constraints
        print("-" * 80)
        print("UNIQUE CONSTRAINTS ON PROJECTS TABLE")
        print("-" * 80)
        print()

        unique_query = """
        SELECT
            tc.constraint_name,
            STRING_AGG(kcu.column_name, ', ') as columns
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'projects'
          AND tc.constraint_type = 'UNIQUE'
        GROUP BY tc.constraint_name;
        """

        cur.execute(unique_query)
        unique_rows = cur.fetchall()

        if unique_rows:
            for row in unique_rows:
                print(f"  {row['constraint_name']}: {row['columns']}")
                if 'path' in row['columns']:
                    print(f"    ✗ Path UNIQUE constraint still exists!")
        else:
            print("  ✓ No UNIQUE constraints (path constraint removed)")

        conn.close()

        print()
        print("=" * 80)
        print("QUERY COMPLETE")
        print("=" * 80)

    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
