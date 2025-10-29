#!/usr/bin/env python3
"""
Display migrations for manual execution in Supabase SQL Editor
"""
from pathlib import Path

def main():
    print("=" * 80)
    print("MIGRATIONS FOR MANUAL EXECUTION")
    print("=" * 80)
    print()
    print("INSTRUCTIONS:")
    print("  1. Go to: https://yxyfiatdrgelnvxopdsm.supabase.co")
    print("  2. Open SQL Editor")
    print("  3. Copy and paste each migration below (in order)")
    print("  4. Click 'Run' for each one")
    print("  5. Verify no errors in output")
    print()
    print("=" * 80)
    print()

    migrations = [
        "supabase/migrations/20251028000001_file_based_project_id.sql",
        "supabase/migrations/20251028000002_fix_composite_foreign_keys.sql"
    ]

    for i, migration_file in enumerate(migrations, 1):
        path = Path(migration_file)

        if not path.exists():
            print(f"❌ Migration {i}: File not found: {migration_file}")
            print()
            continue

        with open(path, 'r') as f:
            sql = f.read()

        print(f"{'=' * 80}")
        print(f"MIGRATION {i}: {path.name}")
        print(f"{'=' * 80}")
        print()
        print("Copy everything below this line:")
        print("-" * 80)
        print(sql)
        print("-" * 80)
        print()
        print(f"✓ Migration {i} ready to copy")
        print()
        print("After running this migration, press Enter to continue...")
        if i < len(migrations):
            input()
        print()

    print("=" * 80)
    print("ALL MIGRATIONS DISPLAYED")
    print("=" * 80)
    print()
    print("After running all migrations in Supabase SQL Editor:")
    print()
    print("  1. Run verification:")
    print("     python3 verify_composite_fks_final.py")
    print()
    print("  2. Test system:")
    print("     python3 test_file_based_project_id.py")
    print()
    print("  3. Audit database:")
    print("     python3 audit_database.py")
    print()

if __name__ == "__main__":
    main()
