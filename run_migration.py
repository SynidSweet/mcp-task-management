#!/usr/bin/env python3
"""Run a SQL migration against the Supabase database."""

import sys
from pathlib import Path
from tools.document_tools import get_supabase_client

def run_migration(migration_file: str):
    """Run a SQL migration file."""
    print(f"Running migration: {migration_file}")

    # Read migration file
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    with open(migration_path, 'r') as f:
        sql = f.read()

    print(f"\nSQL to execute:")
    print("-" * 60)
    print(sql)
    print("-" * 60)
    print()

    # Get Supabase client
    client, error = get_supabase_client()
    if error:
        print(f"❌ Database connection failed: {error}")
        return False

    # Execute SQL using exec_ddl function
    try:
        result = client.rpc('exec_ddl', {'sql_statement': sql}).execute()
        print("✅ Migration executed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\n⚠️  Manual execution required:")
        print(f"1. Open Supabase SQL Editor at: https://yxyfiatdrgelnvxopdsm.supabase.co")
        print(f"2. Run the following SQL:\n")
        print(sql)
        print(f"\n3. Or copy from file: {migration_file}")
        return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 run_migration.py <migration_file>")
        sys.exit(1)

    migration_file = sys.argv[1]
    success = run_migration(migration_file)
    sys.exit(0 if success else 1)
