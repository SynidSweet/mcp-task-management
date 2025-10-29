#!/usr/bin/env python3
"""
Run migration step-by-step to find exact failure point
"""
import psycopg2
import sys
from pathlib import Path

DATABASE_URL = 'postgres://postgres:YOBh0mVTSqFELFlq@db.yxyfiatdrgelnvxopdsm.supabase.co:5432/postgres'

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 run_migration_stepwise.py <migration_file>")
        sys.exit(1)

    migration_file = sys.argv[1]
    migration_path = Path(migration_file)

    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    with open(migration_path, 'r') as f:
        sql = f.read()

    print("=" * 80)
    print("STEP-BY-STEP MIGRATION EXECUTION")
    print("=" * 80)
    print()

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False  # Use transaction
        cur = conn.cursor()

        # Split on semicolons (simple approach)
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        print(f"Found {len(statements)} statement(s) to execute")
        print()

        for i, stmt in enumerate(statements, 1):
            # Skip DO blocks for now (they're multi-line)
            if stmt.upper().startswith('DO $$'):
                # Find the matching END $$
                # For simplicity, we'll execute DO blocks as-is
                pass

            # Show first 60 chars of statement
            preview = stmt[:60].replace('\n', ' ')
            if len(stmt) > 60:
                preview += "..."

            print(f"[{i}/{len(statements)}] {preview}")

            try:
                cur.execute(stmt)
                print(f"     ✓ Success")
            except psycopg2.Error as e:
                print(f"     ✗ FAILED: {e}")
                print()
                print("=" * 80)
                print(f"MIGRATION STOPPED AT STATEMENT {i}")
                print("=" * 80)
                print()
                print("Failed statement:")
                print("-" * 80)
                print(stmt)
                print("-" * 80)
                print()
                print("Error:", e)
                conn.rollback()
                conn.close()
                sys.exit(1)

        # Commit all changes
        conn.commit()
        print()
        print("=" * 80)
        print("✅ ALL STATEMENTS EXECUTED SUCCESSFULLY")
        print("=" * 80)
        conn.close()

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
