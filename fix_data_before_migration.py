#!/usr/bin/env python3
"""
Fix data inconsistencies before running composite key migration
"""
import psycopg2

DATABASE_URL = 'postgres://postgres:YOBh0mVTSqFELFlq@db.yxyfiatdrgelnvxopdsm.supabase.co:5432/postgres'

def main():
    print("=" * 80)
    print("FIX DATA BEFORE COMPOSITE KEY MIGRATION")
    print("=" * 80)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # ===================================================================
    # 1. Delete test project
    # ===================================================================
    print("1. Cleaning up test projects...")
    cur.execute("DELETE FROM projects WHERE path LIKE '/test%' OR machine_id = 'test';")
    deleted = cur.rowcount
    print(f"   Deleted {deleted} test project(s)")
    conn.commit()

    # ===================================================================
    # 2. Update agents machine_id from test-machine to hetzner
    # ===================================================================
    print("\n2. Updating agents machine_id...")
    cur.execute("""
        UPDATE agents
        SET machine_id = 'hetzner'
        WHERE machine_id = 'test-machine';
    """)
    updated = cur.rowcount
    print(f"   Updated {updated} agent(s)")
    conn.commit()

    # ===================================================================
    # 3. Update commands machine_id from test-machine to hetzner
    # ===================================================================
    print("\n3. Updating commands machine_id...")
    cur.execute("""
        UPDATE commands
        SET machine_id = 'hetzner'
        WHERE machine_id = 'test-machine';
    """)
    updated = cur.rowcount
    print(f"   Updated {updated} command(s)")
    conn.commit()

    # ===================================================================
    # 4. Update all core tables machine_id
    # ===================================================================
    print("\n4. Updating core tables machine_id...")

    # Tasks
    cur.execute("UPDATE tasks SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} task(s) from test-machine")
    cur.execute("UPDATE tasks SET machine_id = 'hetzner' WHERE machine_id = 'test-machine-prod';")
    print(f"   Updated {cur.rowcount} task(s) from test-machine-prod")

    # Sprints
    cur.execute("UPDATE sprints SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} sprint(s) from test-machine")
    cur.execute("UPDATE sprints SET machine_id = 'hetzner' WHERE machine_id = 'test-machine-prod';")
    print(f"   Updated {cur.rowcount} sprint(s) from test-machine-prod")

    # Journal sessions
    cur.execute("UPDATE journal_sessions SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} journal session(s) from test-machine")
    cur.execute("UPDATE journal_sessions SET machine_id = 'hetzner' WHERE machine_id = 'test-machine-prod';")
    print(f"   Updated {cur.rowcount} journal session(s) from test-machine-prod")

    # Documentation
    cur.execute("UPDATE documentation SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} documentation(s) from test-machine")
    cur.execute("UPDATE documentation SET machine_id = 'hetzner' WHERE machine_id = 'test-machine-prod';")
    print(f"   Updated {cur.rowcount} documentation(s) from test-machine-prod")

    # Specifications
    cur.execute("UPDATE specifications SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} specification(s) from test-machine")
    cur.execute("UPDATE specifications SET machine_id = 'hetzner' WHERE machine_id = 'test-machine-prod';")
    print(f"   Updated {cur.rowcount} specification(s) from test-machine-prod")

    # Template tasks
    cur.execute("UPDATE template_tasks SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} template task(s) from test-machine")

    # Template sprints
    cur.execute("UPDATE template_sprints SET machine_id = 'hetzner' WHERE machine_id = 'test-machine';")
    print(f"   Updated {cur.rowcount} template sprint(s) from test-machine")

    conn.commit()

    # ===================================================================
    # 5. Verify data consistency
    # ===================================================================
    print("\n5. Verifying data consistency...")

    # Check tasks
    cur.execute("""
        SELECT COUNT(*)
        FROM tasks t
        WHERE NOT EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id::text = t.project_id AND p.machine_id = t.machine_id
        );
    """)
    orphaned_tasks = cur.fetchone()[0]

    # Check sprints
    cur.execute("""
        SELECT COUNT(*)
        FROM sprints s
        WHERE NOT EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id::text = s.project_id AND p.machine_id = s.machine_id
        );
    """)
    orphaned_sprints = cur.fetchone()[0]

    # Check agents
    cur.execute("""
        SELECT COUNT(*)
        FROM agents a
        WHERE a.project_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM projects p
              WHERE p.id = a.project_id AND p.machine_id = a.machine_id
          );
    """)
    orphaned_agents = cur.fetchone()[0]

    # Check commands
    cur.execute("""
        SELECT COUNT(*)
        FROM commands c
        WHERE c.project_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM projects p
              WHERE p.id = c.project_id AND p.machine_id = c.machine_id
          );
    """)
    orphaned_commands = cur.fetchone()[0]

    if orphaned_tasks == 0 and orphaned_sprints == 0 and orphaned_agents == 0 and orphaned_commands == 0:
        print("   ✓ All data has matching projects - ready for FK constraints")
    else:
        print(f"   ⚠️  Orphaned tasks: {orphaned_tasks}")
        print(f"   ⚠️  Orphaned sprints: {orphaned_sprints}")
        print(f"   ⚠️  Orphaned agents: {orphaned_agents}")
        print(f"   ⚠️  Orphaned commands: {orphaned_commands}")

    # ===================================================================
    # 6. Show final state
    # ===================================================================
    print("\n6. Final state:")
    print("\n   Projects:")
    cur.execute("SELECT id, machine_id, path FROM projects ORDER BY path;")
    for row in cur.fetchall():
        print(f"     {row[0]} - {row[1]:15} - {row[2]}")

    print("\n   Agents (with project_id):")
    cur.execute("SELECT agent_name, project_id, machine_id FROM agents WHERE project_id IS NOT NULL;")
    for row in cur.fetchall():
        print(f"     {row[0]:30} - {str(row[1])[:8]}... - {row[2]}")

    print("\n   Commands (with project_id):")
    cur.execute("SELECT command_name, project_id, machine_id FROM commands WHERE project_id IS NOT NULL;")
    for row in cur.fetchall():
        print(f"     {row[0]:30} - {str(row[1])[:8]}... - {row[2]}")

    conn.close()

    print()
    print("=" * 80)
    print("DATA CLEANUP COMPLETE")
    print("=" * 80)
    print()
    print("Next step: Run the composite key migration")
    print("  python3 run_migration.py supabase/migrations/20251028000005_composite_key_final.sql")
    print()

if __name__ == "__main__":
    main()
