"""Tool category mapping for subscription filtering"""

# Map each tool to its category
TOOL_CATEGORIES = {
    # System tools (3 tools)
    "system_set_project_directory": "system",
    "system_health_check": "system",
    "workflow_load_context": "system",

    # Task tools (7 tools)
    "task_create": "task",
    "task_update": "task",
    "task_delete": "task",
    "task_get": "task",
    "task_search": "task",
    "get_next_task_full": "task",
    "task_create_from_template": "task",

    # Sprint tools (8 tools)
    "sprint_get_current": "sprint",
    "sprint_update": "sprint",
    "sprint_update_strategic_context": "sprint",
    "sprint_add_task": "sprint",
    "sprint_remove_task": "sprint",
    "sprint_create_from_template": "sprint",
    "sprint_template_list": "sprint",
    "sprint_template_get": "sprint",

    # Journal tools (3 tools)
    "journal_create_session": "journal",
    "journal_get_recent": "journal",
    "journal_search": "journal",

    # Git tools (2 tools)
    "session_commit_start": "git",
    "session_list_history": "git",

    # Specification tools (5 tools)
    "specification_create": "specification",
    "specification_update": "specification",
    "specification_delete": "specification",
    "specification_query": "specification",
    "specification_get": "specification",

    # Template tools (2 tools - others are counted in task/sprint)
    "template_list": "template",
    "template_get": "template",

    # Document tools (5 tools)
    "document_create": "document",
    "document_update": "document",
    "document_delete": "document",
    "document_get": "document",
    "document_query": "document",
}


def get_tool_category(tool_name: str) -> str:
    """Get category for a tool name.

    Args:
        tool_name: Name of the tool

    Returns:
        Category name (e.g., "task", "sprint", "document") or "unknown" if not found
    """
    return TOOL_CATEGORIES.get(tool_name, "unknown")


def get_tools_by_category(category: str) -> list:
    """Get all tools in a specific category.

    Args:
        category: Category name (e.g., "task", "sprint", "document")

    Returns:
        List of tool names in that category
    """
    return [tool for tool, cat in TOOL_CATEGORIES.items() if cat == category]


def get_all_categories() -> list:
    """Get list of all available categories.

    Returns:
        List of unique category names
    """
    return sorted(set(TOOL_CATEGORIES.values()))


def get_tool_count_by_category() -> dict:
    """Get count of tools in each category.

    Returns:
        Dictionary mapping category names to tool counts
    """
    counts = {}
    for category in TOOL_CATEGORIES.values():
        counts[category] = counts.get(category, 0) + 1
    return counts
