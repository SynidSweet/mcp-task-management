# Project ID File-Based Architecture Design

**Date**: 2025-10-28
**Purpose**: Enable same project identification across different machines with different paths

---

## Problem Statement

**Current Issue**: Using `path` to identify projects fails across machines because:
```
Machine A: /home/alice/projects/myrepo  ← Same project
Machine B: /home/bob/projects/myrepo    ← Same project (different path!)
Machine C: /Users/charlie/myrepo        ← Same project (different path!)
```

**Solution**: Store project_id in the project folder itself (`.claude-tasks/project_id`)

---

## Proposed Architecture

### 1. Project ID File

**Location**: `.claude-tasks/project_id`

**Content**: Simple UUID text file
```
19717129-ac4d-4268-9b80-5a4a4643eeb1
```

**Lifecycle**:
- Created when project is first initialized
- Should be committed to version control (travels with repo)
- Read by all machines accessing this project
- Never regenerated (permanent project identifier)

### 2. Database Schema Changes

#### Before (Current):
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,              -- Auto-generated per machine
    path TEXT UNIQUE NOT NULL,        -- ❌ Blocks multi-machine
    name TEXT NOT NULL,
    machine_id TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**Problem**:
- `path UNIQUE` prevents same project on multiple machines
- Each machine tries to create new project with different path
- INSERT fails due to... wait, they have different paths, so UNIQUE won't trigger
- But query by path won't find the same project across machines

#### After (Proposed):
```sql
CREATE TABLE projects (
    id UUID NOT NULL,                 -- From project_id file
    machine_id TEXT NOT NULL,         -- Which machine
    path TEXT NOT NULL,               -- Path on THIS machine
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    PRIMARY KEY (id, machine_id)      -- ✓ Same project, different machines
);

-- Index for quick lookups
CREATE INDEX idx_projects_path ON projects(path);
```

**Benefits**:
- Same `id` across all machines
- Each machine has its own row with its local path
- Query by `(id, machine_id)` gets machine-specific info
- Query by `id` gets all machines accessing this project

### 3. Project Manager Changes

Add methods to handle project_id file:

```python
class ProjectManager:
    def get_project_id_file(self) -> Path:
        """Get path to project_id file"""
        return self.data_dir / "project_id"

    def read_project_id(self) -> Optional[str]:
        """Read project_id from file, or None if doesn't exist"""
        id_file = self.get_project_id_file()
        if id_file.exists():
            return id_file.read_text().strip()
        return None

    def write_project_id(self, project_id: str) -> None:
        """Write project_id to file"""
        id_file = self.get_project_id_file()
        id_file.write_text(project_id + '\n')

    def get_or_generate_project_id(self) -> str:
        """Get project_id from file, or generate and save new one"""
        project_id = self.read_project_id()
        if not project_id:
            import uuid
            project_id = str(uuid.uuid4())
            self.write_project_id(project_id)
        return project_id
```

### 4. get_or_create_project_id() Changes

**Before (Broken)**:
```python
def get_or_create_project_id(project_path):
    # Query by path AND machine_id ❌
    result = client.table('projects').select('id')\
        .eq('path', str(project_path))\
        .eq('machine_id', machine_id)\
        .execute()

    # Each machine creates different project_id ❌
```

**After (Correct)**:
```python
def get_or_create_project_id(project_manager):
    """Get or create project in database using file-based project_id"""

    # 1. Get project_id from file (or generate)
    project_id = project_manager.get_or_generate_project_id()

    # 2. Get machine_id
    machine_id = get_machine_id()

    # 3. Check if this machine already registered for this project
    result = client.table('projects').select('*')\
        .eq('id', project_id)\
        .eq('machine_id', machine_id)\
        .execute()

    if result.data:
        # Update path if it changed
        if result.data[0]['path'] != str(project_manager.project_path):
            client.table('projects').update({
                'path': str(project_manager.project_path),
                'updated_at': 'NOW()'
            }).eq('id', project_id).eq('machine_id', machine_id).execute()
        return project_id, None

    # 4. Insert new machine record for this project
    new_record = {
        'id': project_id,  # From file
        'machine_id': machine_id,
        'path': str(project_manager.project_path),
        'name': os.path.basename(str(project_manager.project_path))
    }

    result = client.table('projects').insert(new_record).execute()
    return project_id, None
```

---

## Migration Strategy

### Step 1: Create Migration for Database Schema

```sql
-- Drop old UNIQUE constraint on path (if exists)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_path_key;

-- Change primary key to composite
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_pkey;
ALTER TABLE projects ADD PRIMARY KEY (id, machine_id);

-- Add index for path lookups
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
```

### Step 2: Migrate Existing Projects

For each existing project:
1. Generate UUID for project_id file
2. Write to `.claude-tasks/project_id`
3. Update database record with composite key

```python
# For existing projects
project_id = str(uuid.uuid4())
write_project_id_file(project_id)

# Update database
old_record = get_existing_project()
client.table('projects').delete().eq('id', old_record['id']).execute()
client.table('projects').insert({
    'id': project_id,  # New UUID from file
    'machine_id': machine_id,
    'path': old_record['path'],
    'name': old_record['name']
}).execute()
```

### Step 3: Update Code

1. Update `ProjectManager` with project_id methods
2. Update `get_or_create_project_id()` to use file-based ID
3. Update all callers to pass `project_manager` instead of `project_path`

---

## Multi-Machine Workflow Example

### Machine A (hetzner) - First Time

1. User clones repo to `/home/alice/projects/myrepo`
2. MCP server starts, calls `get_or_create_project_id()`
3. No `.claude-tasks/project_id` exists
4. Generate: `project_id = "19717129-ac4d-4268-9b80-5a4a4643eeb1"`
5. Write to `.claude-tasks/project_id`
6. Insert to database:
   ```
   id: 19717129-ac4d-4268-9b80-5a4a4643eeb1
   machine_id: hetzner
   path: /home/alice/projects/myrepo
   ```
7. User commits project_id file to repo

### Machine B (laptop) - Clone Same Repo

1. User clones same repo to `/Users/bob/myrepo`
2. `.claude-tasks/project_id` exists (from repo) ✓
3. Read: `project_id = "19717129-ac4d-4268-9b80-5a4a4643eeb1"`
4. Query database for: `id=19717129... AND machine_id=laptop`
5. Not found, insert:
   ```
   id: 19717129-ac4d-4268-9b80-5a4a4643eeb1  ← Same!
   machine_id: laptop
   path: /Users/bob/myrepo  ← Different path!
   ```

### Result

Database now has:
```
projects:
  (19717129..., hetzner,  /home/alice/projects/myrepo)
  (19717129..., laptop,   /Users/bob/myrepo)

tasks (Machine A):
  project_id: 19717129...
  machine_id: hetzner
  title: "Task 1"

tasks (Machine B):
  project_id: 19717129...
  machine_id: laptop
  title: "Task 1"  ← Same project, different machine state
```

---

## Queries

### Get project info for current machine
```sql
SELECT * FROM projects
WHERE id = '19717129...'
  AND machine_id = 'hetzner';
```

### Get all machines accessing this project
```sql
SELECT machine_id, path, updated_at
FROM projects
WHERE id = '19717129...'
ORDER BY updated_at DESC;
```

### Get tasks for this project on current machine
```sql
SELECT * FROM tasks
WHERE project_id = '19717129...'
  AND machine_id = 'hetzner';
```

### Get tasks for this project on all machines
```sql
SELECT * FROM tasks
WHERE project_id = '19717129...'
ORDER BY machine_id, created_at;
```

---

## Benefits

✅ **Correct multi-machine support**
- Same repo = same project_id across all machines

✅ **Different paths handled correctly**
- Each machine stores its local path
- No path conflicts

✅ **Machine-specific state**
- Tasks/data separated by project_id + machine_id

✅ **Source control friendly**
- Project_id file can be committed
- Travels with the repository

✅ **Simple and explicit**
- No complex heuristics
- Clear project identity

---

## Edge Cases

### Project ID File Not Committed

If `.claude-tasks/` is in `.gitignore`:
- Each machine generates different project_id
- Behaves like separate projects (current behavior)
- User should commit project_id file for multi-machine support

### Project ID File Deleted

- System generates new project_id
- Creates new project records in database
- Old data orphaned (can be cleaned up by path matching)
- User should restore from version control

### Merge Conflicts

If two machines generate different project_ids before syncing:
- Git merge conflict in project_id file
- User must resolve manually (keep one, update database)
- Rare scenario (only if both machines initialize simultaneously)

---

## Implementation Checklist

- [ ] Add project_id methods to ProjectManager
- [ ] Create database migration (remove UNIQUE on path, add composite PK)
- [ ] Update get_or_create_project_id() implementation
- [ ] Migrate existing projects to file-based IDs
- [ ] Update all callers of get_or_create_project_id()
- [ ] Test multi-machine scenario
- [ ] Update documentation
- [ ] Add .gitignore check/warning for project_id file

---

## Recommendation

This architecture correctly handles the user's requirement:
- **Same repo = same project_id** (via file)
- **Different machines = different paths** (stored per machine)
- **State separation** (via project_id + machine_id)

**Should we proceed with implementation?**
