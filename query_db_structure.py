#!/usr/bin/env python3
"""
Query database structure using direct PostgreSQL connection
"""
import sys
import psycopg2
import psycopg2.extras

# Database connection
DATABASE_URL = 'postgres://postgres:YOBh0mVTSqFELFlq@db.yxyfiatdrgelnvxopdsm.supabase.co:5432/postgres'

def main():
    print("=" * 80)
    print("DATABASE STRUCTURE QUERY - Direct PostgreSQL Access")
    print("=" * 80)
    print()

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        print("✓ Connected successfully")
        print()

        # ===================================================================
        # Query FK constraints
        # ===================================================================
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
            print("✓ No FK constraints found (all already dropped)")
        else:
            print(f"Found {len(rows)} FK constraint(s):")
            print()
            for row in rows:
                status = '✓ Composite' if row['column_count'] == 2 else '✗ Single-column'
                print(f"{status}")
                print(f"  Table: {row['table_name']}")
                print(f"  Constraint: {row['constraint_name']}")
                print(f"  Columns: {row['columns']}")
                print()

        # ===================================================================
        # Check projects PRIMARY KEY
        # ===================================================================
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
          AND tc.table_schema = 'public'
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
            print("⚠️  No PRIMARY KEY found!")

        print()

        # ===================================================================
        # Check UNIQUE constraints
        # ===================================================================
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
          AND tc.table_schema = 'public'
        GROUP BY tc.constraint_name;
        """

        cur.execute(unique_query)
        unique_rows = cur.fetchall()

        if unique_rows:
            print(f"Found {len(unique_rows)} UNIQUE constraint(s):")
            for row in unique_rows:
                print(f"  {row['constraint_name']}: {row['columns']}")
                if 'path' in row['columns']:
                    print(f"    ✗ Path UNIQUE constraint exists (should be removed)")
        else:
            print("✓ No UNIQUE constraints (correct)")

        print()

        # ===================================================================
        # Summary
        # ===================================================================
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()

        # Save results for migration generation
        global fk_constraints
        fk_constraints = [(r['table_name'], r['constraint_name']) for r in rows] if rows else []

        print(f"FK constraints to drop: {len(fk_constraints)}")
        print(f"Primary key status: {'Composite' if len(pk_columns) == 2 else 'Single-column'}")
        print(f"UNIQUE constraints: {len(unique_rows) if unique_rows else 0}")
        print()

        if fk_constraints:
            print("Will generate DROP statements for:")
            for table, constraint in fk_constraints:
                print(f"  - {table}: {constraint}")

        conn.close()

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
