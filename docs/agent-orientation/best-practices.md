# Agent Development Best Practices

*Guidelines for effective AI agent development with this MCP system*

## Core Principles

### 1. Always Check Project Initialization First

**Why**: Most tools require a project directory to be set. Operations fail if the project isn't initialized.

**How**:
```python
# At start of any workflow
health = mcp__claude-tasks__system_health_check()

if health.get("status") != "success":
    # Project not initialized
    init_result = mcp__claude-tasks__system_set_project_directory(".")

    if init_result.get("status") != "success":
        # Handle initialization failure
        print(f"Failed to initialize: {init_result.get('error')}")
        return
```

**When to Skip**: Never skip this check. It's fast and prevents wasted operations.

### 2. Use Search Before Creating Duplicates

**Why**: Prevents duplicate tasks and cluttered task lists.

**How**:
```python
# Before creating a task, search for existing ones
search_result = mcp__claude-tasks__task_search(
    query="authentication",
    status="pending"
)

if search_result.get("tasks"):
    # Task exists
    existing_task = search_result["tasks"][0]
    print(f"Found existing task: {existing_task['id']} - {existing_task['title']}")

    # Update existing task instead
    result = mcp__claude-tasks__task_update(
        task_id=existing_task["id"],
        priority="high"
    )
else:
    # No existing task, safe to create
    result = mcp__claude-tasks__task_create(
        title="Implement authentication",
        priority="high"
    )
```

**Search Strategies**:
- Use specific keywords from your task title
- Filter by status to find active work
- Search across title, description, and tags

### 3. Validate Inputs Before Calling Tools

**Why**: Reduces error responses and wasted API calls.

**How**:
```python
# Define valid values
VALID_PRIORITIES = ["low", "medium", "high", "critical"]
VALID_STATUSES = ["pending", "in_progress", "completed", "blocked"]
VALID_SESSION_TYPES = ["carry-on", "investigation", "documentation"]

# Validate before calling
def create_task_safely(title, priority):
    if priority not in VALID_PRIORITIES:
        print(f"Invalid priority: {priority}. Using 'medium'")
        priority = "medium"

    return mcp__claude-tasks__task_create(
        title=title,
        priority=priority
    )
```

**Common Validations**:
- Priority: `low`, `medium`, `high`, `critical`
- Status: `pending`, `in_progress`, `completed`, `blocked`
- Task IDs: Format `TASK-YYYY-NNN`
- Sprint IDs: Format `SPRINT-YYYY-QN-NNN`

### 4. Handle Errors Gracefully

**Why**: Errors are normal. Good agents recover and continue.

**How**:
```python
def safe_task_operation(task_id, operation):
    """Wrapper for safe task operations with error handling"""

    try:
        result = operation(task_id)

        if result.get("status") == "error":
            error_msg = result.get("error", "Unknown error")

            # Different recovery strategies based on error
            if "not found" in error_msg:
                print(f"Task {task_id} not found. Searching...")
                # Recovery: Search for task
                return search_and_retry(task_id, operation)

            elif "Invalid" in error_msg:
                print(f"Invalid parameters: {error_msg}")
                # Recovery: Use default values
                return None

            else:
                print(f"Operation failed: {error_msg}")
                return None

        return result

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None
```

**Error Categories**:
1. **Not Found**: Search for correct ID
2. **Invalid Input**: Use valid values
3. **Project Not Initialized**: Initialize project
4. **Permission Denied**: Check file permissions

### 5. Use Appropriate Tool for the Task

**Why**: Each tool is optimized for specific operations.

**Tool Selection Guide**:

```python
# Getting work recommendations
# ✅ Good: Use dedicated recommendation tool
tasks = mcp__claude-tasks__get_next_tasks(
    limit=5,
    criteria="priority,dependencies"
)

# ❌ Bad: Manual filtering
all_tasks = mcp__claude-tasks__task_list(limit="100")
# ... manual sorting and filtering


# Searching for specific tasks
# ✅ Good: Use search with filters
results = mcp__claude-tasks__task_search(
    query="authentication",
    status="pending",
    priority="high"
)

# ❌ Bad: Get all and filter
all_tasks = mcp__claude-tasks__task_list(limit="1000")
# ... manual filtering


# Getting single task details
# ✅ Good: Use task_get
task = mcp__claude-tasks__task_get(task_id="TASK-2025-042")

# ❌ Bad: List all and find
tasks = mcp__claude-tasks__task_list(limit="1000")
# ... search for specific task
```

### 6. Don't Over-Engineer

**Why**: Simple solutions are easier to maintain and debug.

**Examples**:

```python
# ✅ Good: Simple and direct
result = mcp__claude-tasks__task_create(
    title="Fix login bug",
    priority="high"
)

if result.get("status") == "success":
    task_id = result["task"]["id"]
    print(f"Created: {task_id}")


# ❌ Bad: Over-engineered
class TaskCreationStrategy:
    def __init__(self, validator, transformer, repository):
        self.validator = validator
        self.transformer = transformer
        self.repository = repository

    async def execute(self, task_data):
        validated = await self.validator.validate(task_data)
        transformed = await self.transformer.transform(validated)
        result = await self.repository.create(transformed)
        return self.transformer.reverse_transform(result)

# Too complex for simple task creation
```

**Keep It Simple**:
- Use tools directly, don't wrap unnecessarily
- Validate inputs, but don't over-validate
- Handle common errors, but don't handle every edge case
- Document complex logic, but keep code simple

### 7. Follow Existing Patterns

**Why**: Consistency makes the system predictable and maintainable.

**Pattern: Task Lifecycle**
```python
# Standard task lifecycle pattern
def complete_task_workflow(title, description, priority="medium"):
    # 1. Create task
    create_result = mcp__claude-tasks__task_create(
        title=title,
        description=description,
        priority=priority
    )

    if create_result.get("status") != "success":
        return None

    task_id = create_result["task"]["id"]

    # 2. Add to current sprint
    sprint = mcp__claude-tasks__sprint_get_current()
    if sprint.get("sprint"):
        mcp__claude-tasks__sprint_add_task(
            sprint_id=sprint["sprint"]["id"],
            task_id=task_id
        )

    # 3. Start work
    mcp__claude-tasks__task_update(
        task_id=task_id,
        status="in_progress"
    )

    # 4. Do the work
    # ... implementation ...

    # 5. Complete task
    mcp__claude-tasks__task_update(
        task_id=task_id,
        status="completed"
    )

    # 6. Record in journal
    mcp__claude-tasks__journal_create_session(
        session_type="carry-on",
        duration_minutes=30,
        tasks_worked=json.dumps([{
            "task_id": task_id,
            "status_change": "completed",
            "work_summary": f"Completed: {title}"
        }])
    )

    return task_id
```

**Pattern: Error Recovery**
```python
# Standard error recovery pattern
def retry_with_search(operation, search_query):
    # Try operation
    result = operation()

    # If failed with "not found"
    if result.get("status") == "error" and "not found" in result.get("error", ""):
        # Search for correct item
        search_result = mcp__claude-tasks__task_search(query=search_query)

        if search_result.get("tasks"):
            # Retry with found item
            return operation(search_result["tasks"][0]["id"])

    return result
```

### 8. Test Changes Before Marking Complete

**Why**: Prevents marking incomplete work as done.

**How**:
```python
def verify_implementation(task_id):
    """Verify implementation before marking task complete"""

    # 1. Get task details
    task = mcp__claude-tasks__task_get(task_id=task_id)

    if task.get("status") != "success":
        return False

    task_data = task["task"]

    # 2. Check if requirements are met
    requirements_met = verify_requirements(task_data)

    # 3. Run tests if applicable
    tests_pass = run_tests(task_data)

    # 4. Verify no new issues introduced
    no_regressions = check_regressions(task_data)

    # 5. Only mark complete if all checks pass
    if requirements_met and tests_pass and no_regressions:
        result = mcp__claude-tasks__task_update(
            task_id=task_id,
            status="completed"
        )
        return True
    else:
        # Keep as in_progress
        print("Not ready for completion. Issues found.")
        return False
```

**Verification Checklist**:
- [ ] All acceptance criteria met
- [ ] Tests passing
- [ ] No regressions introduced
- [ ] Documentation updated
- [ ] Code reviewed (if applicable)

### 9. Update Journal for Significant Work

**Why**: Creates audit trail and helps with debugging and context.

**When to Journal**:
- After completing multiple tasks
- After significant discoveries
- After hitting blockers
- After investigation sessions
- After completing sprints

**How**:
```python
def create_meaningful_journal_entry(tasks_worked, duration):
    """Create journal entry with rich context"""

    # Categorize work
    achievements = []
    discoveries = []
    blockers = []

    for task_work in tasks_worked:
        if task_work["status_change"] == "completed":
            achievements.append(task_work["work_summary"])

        if "discovered" in task_work.get("notes", ""):
            discoveries.append(task_work["notes"])

        if task_work["status_change"] == "blocked":
            blockers.append(task_work["work_summary"])

    # Create entry
    result = mcp__claude-tasks__journal_create_session(
        session_type="carry-on",
        duration_minutes=duration,
        tasks_worked=json.dumps(tasks_worked),
        key_achievements=achievements,
        discoveries=discoveries + blockers,  # Include blockers as discoveries
        sprint_progress_impact=f"Completed {len(achievements)} tasks"
    )

    return result
```

**Journal Entry Quality**:
- Be specific in achievements ("Added OAuth2" not "Made progress")
- Document discoveries for future reference
- Include context about decisions made
- Note any technical debt created

### 10. Use Sprints to Organize Work

**Why**: Sprints provide context and prevent scope creep.

**How**:
```python
def align_work_with_sprint():
    """Ensure work aligns with current sprint objectives"""

    # 1. Get current sprint
    sprint_result = mcp__claude-tasks__sprint_get_current()

    if not sprint_result.get("sprint"):
        print("No active sprint. Create one first.")
        return

    sprint = sprint_result["sprint"]
    objective = sprint.get("primary_objective", "")

    # 2. Get next task
    tasks = mcp__claude-tasks__get_next_tasks(limit=5)

    for task in tasks.get("recommended_tasks", []):
        # 3. Check if task aligns with sprint objective
        if is_aligned_with_objective(task, objective):
            # Work on aligned task
            work_on_task(task)
        else:
            print(f"Task {task['id']} not aligned with sprint. Skipping.")
```

**Sprint Alignment Check**:
```python
def is_aligned_with_objective(task, objective):
    """Check if task serves sprint objective"""

    # Simple keyword matching
    task_keywords = set(task["title"].lower().split())
    objective_keywords = set(objective.lower().split())

    # Check overlap
    overlap = task_keywords.intersection(objective_keywords)

    return len(overlap) > 0
```

## Common Anti-Patterns to Avoid

### Anti-Pattern 1: Ignoring Error Responses

```python
# ❌ Bad: Ignoring errors
result = mcp__claude-tasks__task_create(title="New task")
task_id = result["task"]["id"]  # Crashes if creation failed!

# ✅ Good: Checking errors
result = mcp__claude-tasks__task_create(title="New task")
if result.get("status") == "success":
    task_id = result["task"]["id"]
else:
    print(f"Creation failed: {result.get('error')}")
```

### Anti-Pattern 2: Creating Duplicate Tasks

```python
# ❌ Bad: Not checking for duplicates
for item in todo_list:
    mcp__claude-tasks__task_create(title=item)
# Creates duplicates if run twice!

# ✅ Good: Search first
for item in todo_list:
    existing = mcp__claude-tasks__task_search(query=item)
    if not existing.get("tasks"):
        mcp__claude-tasks__task_create(title=item)
```

### Anti-Pattern 3: Not Using Sprint Context

```python
# ❌ Bad: Working on random tasks
tasks = mcp__claude-tasks__task_list(limit="100")
work_on_first_task(tasks[0])

# ✅ Good: Using sprint context
sprint = mcp__claude-tasks__sprint_get_current()
sprint_tasks = sprint.get("sprint", {}).get("task_ids", [])
next_task = get_highest_priority_sprint_task(sprint_tasks)
work_on_task(next_task)
```

### Anti-Pattern 4: Overly Broad Searches

```python
# ❌ Bad: Too broad
all_tasks = mcp__claude-tasks__task_search(query="")
# Returns everything!

# ✅ Good: Specific search
auth_tasks = mcp__claude-tasks__task_search(
    query="authentication",
    status="pending",
    priority="high"
)
```

### Anti-Pattern 5: Not Recording Work

```python
# ❌ Bad: Completing work without journal
complete_task(task_id)
# No record of what was done!

# ✅ Good: Recording work
work_summary = complete_task(task_id)
mcp__claude-tasks__journal_create_session(
    session_type="carry-on",
    duration_minutes=30,
    tasks_worked=json.dumps([{
        "task_id": task_id,
        "status_change": "completed",
        "work_summary": work_summary
    }])
)
```

## Performance Optimization

### 1. Batch Similar Operations

```python
# ✅ Good: Batch task updates
tasks_to_update = ["TASK-2025-001", "TASK-2025-002", "TASK-2025-003"]

for task_id in tasks_to_update:
    mcp__claude-tasks__task_update(
        task_id=task_id,
        status="completed"
    )
# Each update syncs to database automatically
```

### 2. Use Appropriate Verbosity

```python
# For lists, use minimal verbosity
entities = mcp__claude-tasks__requirements_list_entities(
    verbosity="minimal"  # Faster, less data
)

# Only use full verbosity when needed
entity_details = mcp__claude-tasks__requirements_list_entities(
    verbosity="full"  # Complete data, slower
)
```

### 3. Limit Result Counts

```python
# ✅ Good: Reasonable limits
tasks = mcp__claude-tasks__task_list(limit="20")

# ❌ Bad: Requesting too much
tasks = mcp__claude-tasks__task_list(limit="10000")
# Slow and unnecessary
```

## Security Considerations

### 1. Validate User Input

```python
def create_task_from_user_input(user_title, user_priority):
    # Sanitize and validate
    safe_title = sanitize_string(user_title)
    safe_priority = validate_priority(user_priority) or "medium"

    return mcp__claude-tasks__task_create(
        title=safe_title,
        priority=safe_priority
    )
```

### 2. Don't Expose Sensitive Data

```python
# ✅ Good: Sanitize output
task = mcp__claude-tasks__task_get(task_id="TASK-2025-042")
public_data = {
    "id": task["task"]["id"],
    "title": task["task"]["title"],
    "status": task["task"]["status"]
}
# Don't include sensitive fields

# ❌ Bad: Exposing everything
return task  # Might contain sensitive information
```

## Testing Agent Workflows

### Unit Test Example

```python
async def test_task_creation():
    """Test basic task creation"""

    # Create test task
    result = mcp__claude-tasks__task_create(
        title="Test Task",
        priority="medium"
    )

    # Verify success
    assert result.get("status") == "success"
    assert result["task"]["title"] == "Test Task"
    assert result["task"]["priority"] == "medium"
    assert result["task"]["status"] == "pending"

    # Cleanup
    task_id = result["task"]["id"]
    # Delete task if needed
```

### Integration Test Example

```python
async def test_complete_workflow():
    """Test complete task workflow"""

    # 1. Create task
    create_result = mcp__claude-tasks__task_create(
        title="Integration Test Task",
        priority="high"
    )

    assert create_result.get("status") == "success"
    task_id = create_result["task"]["id"]

    # 2. Update status
    update_result = mcp__claude-tasks__task_update(
        task_id=task_id,
        status="in_progress"
    )

    assert update_result.get("status") == "success"
    assert update_result["task"]["status"] == "in_progress"

    # 3. Complete task
    complete_result = mcp__claude-tasks__task_update(
        task_id=task_id,
        status="completed"
    )

    assert complete_result.get("status") == "success"
    assert complete_result["task"]["status"] == "completed"

    # 4. Verify in search
    search_result = mcp__claude-tasks__task_search(
        query="Integration Test",
        status="completed"
    )

    assert any(t["id"] == task_id for t in search_result.get("tasks", []))
```

## Summary

### Key Takeaways

1. **Initialize First**: Always check project initialization
2. **Search Before Create**: Prevent duplicates
3. **Validate Inputs**: Reduce errors
4. **Handle Errors**: Graceful recovery
5. **Use Right Tool**: Match tool to task
6. **Keep Simple**: Don't over-engineer
7. **Follow Patterns**: Maintain consistency
8. **Test Thoroughly**: Verify before marking complete
9. **Journal Work**: Create audit trail
10. **Use Sprints**: Organize and focus work

### Quick Reference Checklist

Before calling any tool:
- [ ] Project initialized?
- [ ] Valid parameters?
- [ ] Item exists (for updates)?
- [ ] Error handling in place?

After successful operation:
- [ ] Verify result
- [ ] Update related items
- [ ] Record in journal (if significant)
- [ ] Check sprint alignment

---

*For detailed workflows, see workflow.md. For system overview, see README.md.*
