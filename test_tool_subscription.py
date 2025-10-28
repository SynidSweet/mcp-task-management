#!/usr/bin/env python3
"""Test tool subscription filtering"""

import json
import tempfile
from pathlib import Path
from utils.tool_filter import ToolSubscriptionFilter, create_default_config


def test_no_config():
    """All tools available when no config"""
    filter = ToolSubscriptionFilter()
    assert filter.should_register_tool("task_create") is True
    assert filter.should_register_tool("sprint_delete") is True
    print("✅ No config test passed")


def test_include_tools_only():
    """Only specific tools when include_tools set"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "tool_subscription": {
                "include_tools": ["task_create", "task_get"]
            }
        }
        json.dump(config, f)
        config_path = Path(f.name)

    try:
        filter = ToolSubscriptionFilter(config_path)
        assert filter.should_register_tool("task_create") is True
        assert filter.should_register_tool("task_get") is True
        assert filter.should_register_tool("task_delete") is False
        assert filter.should_register_tool("sprint_get_current") is False
        print("✅ Include tools test passed")
    finally:
        config_path.unlink()


def test_exclude_tools():
    """All except specific tools"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "tool_subscription": {
                "exclude_tools": ["task_delete", "sprint_delete"]
            }
        }
        json.dump(config, f)
        config_path = Path(f.name)

    try:
        filter = ToolSubscriptionFilter(config_path)
        assert filter.should_register_tool("task_create") is True
        assert filter.should_register_tool("task_delete") is False
        assert filter.should_register_tool("sprint_delete") is False
        assert filter.should_register_tool("sprint_get_current") is True
        print("✅ Exclude tools test passed")
    finally:
        config_path.unlink()


def test_include_categories():
    """Only specific categories"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "tool_subscription": {
                "include_categories": ["task", "sprint"]
            }
        }
        json.dump(config, f)
        config_path = Path(f.name)

    try:
        filter = ToolSubscriptionFilter(config_path)
        assert filter.should_register_tool("task_create") is True
        assert filter.should_register_tool("sprint_get_current") is True
        assert filter.should_register_tool("document_create") is False
        assert filter.should_register_tool("specification_create") is False
        print("✅ Include categories test passed")
    finally:
        config_path.unlink()


def test_exclude_categories():
    """All except specific categories"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "tool_subscription": {
                "exclude_categories": ["git", "specification"]
            }
        }
        json.dump(config, f)
        config_path = Path(f.name)

    try:
        filter = ToolSubscriptionFilter(config_path)
        assert filter.should_register_tool("task_create") is True
        assert filter.should_register_tool("session_commit_start") is False
        assert filter.should_register_tool("specification_create") is False
        print("✅ Exclude categories test passed")
    finally:
        config_path.unlink()


def test_complex_filtering():
    """Combine category inclusion with tool exclusion"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "tool_subscription": {
                "include_categories": ["task", "sprint"],
                "exclude_tools": ["task_delete", "sprint_delete"]
            }
        }
        json.dump(config, f)
        config_path = Path(f.name)

    try:
        filter = ToolSubscriptionFilter(config_path)
        assert filter.should_register_tool("task_create") is True
        assert filter.should_register_tool("task_delete") is False  # Excluded
        assert filter.should_register_tool("sprint_get_current") is True
        assert filter.should_register_tool("sprint_delete") is False  # Excluded
        assert filter.should_register_tool("document_create") is False  # Not in categories
        print("✅ Complex filtering test passed")
    finally:
        config_path.unlink()


def test_precedence():
    """include_tools takes precedence over everything"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "tool_subscription": {
                "include_tools": ["task_delete"],  # Explicitly include
                "exclude_tools": ["task_delete"],  # But also exclude
                "include_categories": ["sprint"]    # And different category
            }
        }
        json.dump(config, f)
        config_path = Path(f.name)

    try:
        filter = ToolSubscriptionFilter(config_path)
        # include_tools is most restrictive - only it matters
        assert filter.should_register_tool("task_delete") is True
        assert filter.should_register_tool("task_create") is False
        assert filter.should_register_tool("sprint_get_current") is False
        print("✅ Precedence test passed")
    finally:
        config_path.unlink()


def test_default_config_creation():
    """Test default config file creation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config" / "tool_subscription.json"

        # Config should not exist yet
        assert not config_path.exists()

        # Create default config
        result = create_default_config(config_path)
        assert result is True, "Should return True when creating new config"

        # Config should now exist
        assert config_path.exists(), "Config file should exist after creation"

        # Load and verify contents
        with open(config_path, 'r') as f:
            data = json.load(f)

        # Check that it has the expected structure
        assert "tool_subscription" in data
        assert "exclude_categories" in data["tool_subscription"]
        assert "document" in data["tool_subscription"]["exclude_categories"]

        # Try creating again - should return False (already exists)
        result2 = create_default_config(config_path)
        assert result2 is False, "Should return False when config already exists"

        # Create filter with default config
        filter = ToolSubscriptionFilter(config_path)

        # Verify document tools are excluded
        assert filter.should_register_tool("task_create") is True
        assert filter.should_register_tool("document_create") is False
        assert filter.should_register_tool("document_update") is False

        print("✅ Default config creation test passed")


if __name__ == "__main__":
    print("Testing tool subscription filtering...\n")

    test_no_config()
    test_include_tools_only()
    test_exclude_tools()
    test_include_categories()
    test_exclude_categories()
    test_complex_filtering()
    test_precedence()
    test_default_config_creation()

    print("\n🎉 All tests passed!")
