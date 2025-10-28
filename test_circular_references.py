#!/usr/bin/env python3
"""
Test Circular Reference Detection

Tests both runtime and validation-time cycle detection.
"""

import asyncio
import sys
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.project_manager import ProjectManager
from tools.template_tools import _resolve_task_reference
from check_data_integrity import IntegrityChecker


async def test_runtime_circular_detection():
    """Test that circular references are detected during resolution."""
    print("\n" + "="*60)
    print("TEST 1: Runtime Circular Reference Detection")
    print("="*60)

    # Create temporary templates with circular reference
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir) / ".claude-tasks" / "templates"
        templates_dir.mkdir(parents=True)

        # Create circular templates: A -> B -> A
        circular_templates = {
            "templates": {
                "template_a": {
                    "metadata": {
                        "template_id": "template_a",
                        "name": "Template A",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task A",
                        "priority": "high"
                    },
                    "subtasks": [
                        {
                            "template_ref": "template_b"
                        }
                    ]
                },
                "template_b": {
                    "metadata": {
                        "template_id": "template_b",
                        "name": "Template B",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task B",
                        "priority": "medium"
                    },
                    "subtasks": [
                        {
                            "template_ref": "template_a"  # ← Circular reference!
                        }
                    ]
                }
            }
        }

        # Write templates to file
        templates_file = templates_dir / "task_templates.json"
        with open(templates_file, 'w') as f:
            json.dump(circular_templates, f)

        # Try to resolve template_a (should detect cycle)
        project_manager = ProjectManager(Path(tmpdir))

        try:
            task_def = {"template_ref": "template_a"}
            resolved = await _resolve_task_reference(task_def, {}, project_manager)
            print("\n✗ Test FAILED: Should have raised ValueError for circular reference")
            return False

        except ValueError as e:
            error_msg = str(e)
            print(f"✓ Correctly raised ValueError: {error_msg}")

            # Verify error message contains cycle information
            if "Circular" in error_msg or "circular" in error_msg:
                print("✓ Error message indicates circular reference")
            else:
                print(f"✗ Error message doesn't mention circular reference: {error_msg}")
                return False

            # Verify cycle path is in error
            if "template_a" in error_msg and "template_b" in error_msg:
                print("✓ Error message shows cycle path")
            else:
                print(f"✗ Error message doesn't show cycle path: {error_msg}")
                return False

            print("\n✓ Runtime circular reference detection PASSED!")
            return True

        except Exception as e:
            print(f"\n✗ Test FAILED with unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_validation_circular_detection():
    """Test that validator detects circular references via DFS."""
    print("\n" + "="*60)
    print("TEST 2: Validation-Time Circular Reference Detection")
    print("="*60)

    # Create temporary templates with circular reference
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir) / ".claude-tasks" / "templates"
        templates_dir.mkdir(parents=True)

        # Create circular templates: A -> B -> C -> A
        circular_templates = {
            "templates": {
                "template_a": {
                    "metadata": {
                        "template_id": "template_a",
                        "name": "Template A",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task A",
                        "priority": "high"
                    },
                    "subtasks": [
                        {"template_ref": "template_b"}
                    ]
                },
                "template_b": {
                    "metadata": {
                        "template_id": "template_b",
                        "name": "Template B",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task B",
                        "priority": "medium"
                    },
                    "subtasks": [
                        {"template_ref": "template_c"}
                    ]
                },
                "template_c": {
                    "metadata": {
                        "template_id": "template_c",
                        "name": "Template C",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task C",
                        "priority": "low"
                    },
                    "subtasks": [
                        {"template_ref": "template_a"}  # ← Back to A! Cycle!
                    ]
                }
            }
        }

        # Write templates to file
        templates_file = templates_dir / "task_templates.json"
        with open(templates_file, 'w') as f:
            json.dump(circular_templates, f)

        # Run integrity checker
        checker = IntegrityChecker(project_path=tmpdir, verbose=False)
        checker.check_template_references()

        # Check if circular reference was detected
        template_issues = [
            issue for issue in checker.issues
            if issue.category == 'template_references'
        ]

        if not template_issues:
            print("\n✗ Test FAILED: Validator did not detect circular reference")
            return False

        print(f"✓ Validator detected {len(template_issues)} template issue(s)")

        # Verify the issue is about circular reference
        circular_detected = False
        for issue in template_issues:
            print(f"\n  Issue: {issue.message}")
            if "circular" in issue.message.lower() or "cycle" in issue.message.lower():
                circular_detected = True
                # Verify cycle path is complete
                if "template_a" in issue.message and "template_b" in issue.message and "template_c" in issue.message:
                    print("✓ Full cycle path detected in error message")
                else:
                    print(f"✗ Incomplete cycle path: {issue.message}")
                    return False

        if circular_detected:
            print("\n✓ Validation-time circular reference detection PASSED!")
            return True
        else:
            print("\n✗ Test FAILED: Issue detected but not identified as circular")
            return False


async def test_self_reference_detection():
    """Test that self-references (A -> A) are detected."""
    print("\n" + "="*60)
    print("TEST 3: Self-Reference Detection")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir) / ".claude-tasks" / "templates"
        templates_dir.mkdir(parents=True)

        # Create self-referencing template
        self_ref_templates = {
            "templates": {
                "template_a": {
                    "metadata": {
                        "template_id": "template_a",
                        "name": "Template A",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task A",
                        "priority": "high"
                    },
                    "subtasks": [
                        {"template_ref": "template_a"}  # ← Self reference!
                    ]
                }
            }
        }

        templates_file = templates_dir / "task_templates.json"
        with open(templates_file, 'w') as f:
            json.dump(self_ref_templates, f)

        # Test runtime detection
        project_manager = ProjectManager(Path(tmpdir))

        try:
            task_def = {"template_ref": "template_a"}
            resolved = await _resolve_task_reference(task_def, {}, project_manager)
            print("\n✗ Test FAILED: Should have raised ValueError for self-reference")
            return False

        except ValueError as e:
            print(f"✓ Runtime detection caught self-reference: {e}")

        # Test validation detection
        checker = IntegrityChecker(project_path=tmpdir, verbose=False)
        checker.check_template_references()

        template_issues = [
            issue for issue in checker.issues
            if issue.category == 'template_references'
        ]

        if template_issues:
            print(f"✓ Validator detected self-reference")
            print("\n✓ Self-reference detection PASSED!")
            return True
        else:
            print("\n✗ Test FAILED: Validator did not detect self-reference")
            return False


async def test_no_false_positives():
    """Test that valid multi-level composition doesn't trigger false alarms."""
    print("\n" + "="*60)
    print("TEST 4: No False Positives (Valid Multi-Level)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir) / ".claude-tasks" / "templates"
        templates_dir.mkdir(parents=True)

        # Create valid multi-level templates: A -> B -> C (no cycle)
        valid_templates = {
            "templates": {
                "template_a": {
                    "metadata": {
                        "template_id": "template_a",
                        "name": "Template A",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task A",
                        "priority": "high"
                    },
                    "subtasks": [
                        {"template_ref": "template_b"}
                    ]
                },
                "template_b": {
                    "metadata": {
                        "template_id": "template_b",
                        "name": "Template B",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task B",
                        "priority": "medium"
                    },
                    "subtasks": [
                        {"template_ref": "template_c"}
                    ]
                },
                "template_c": {
                    "metadata": {
                        "template_id": "template_c",
                        "name": "Template C",
                        "variables": []
                    },
                    "task_definition": {
                        "title": "Task C (base)",
                        "priority": "low"
                    }
                    # No subtasks - end of chain
                }
            }
        }

        templates_file = templates_dir / "task_templates.json"
        with open(templates_file, 'w') as f:
            json.dump(valid_templates, f)

        # Test runtime resolution (should succeed)
        project_manager = ProjectManager(Path(tmpdir))

        try:
            task_def = {"template_ref": "template_a"}
            resolved = await _resolve_task_reference(task_def, {}, project_manager)
            print("✓ Runtime resolution succeeded for valid multi-level template")
            print(f"  Resolved title: {resolved.get('title')}")
        except ValueError as e:
            print(f"\n✗ Test FAILED: Valid template raised error: {e}")
            return False

        # Test validation (should have no issues)
        checker = IntegrityChecker(project_path=tmpdir, verbose=False)
        checker.check_template_references()

        template_issues = [
            issue for issue in checker.issues
            if issue.category == 'template_references' and issue.severity == 'CRITICAL'
        ]

        if template_issues:
            print(f"\n✗ Test FAILED: Validator flagged valid templates:")
            for issue in template_issues:
                print(f"  - {issue.message}")
            return False
        else:
            print("✓ Validator passed valid multi-level templates")
            print("\n✓ No false positives test PASSED!")
            return True


async def main():
    """Run all circular reference tests."""
    print("\n" + "="*60)
    print("  CIRCULAR REFERENCE DETECTION TEST SUITE")
    print("="*60)

    tests = [
        ("Runtime Circular Detection", test_runtime_circular_detection),
        ("Validation Circular Detection", test_validation_circular_detection),
        ("Self-Reference Detection", test_self_reference_detection),
        ("No False Positives", test_no_false_positives),
    ]

    results = []
    for name, test_func in tests:
        result = await test_func()
        results.append((name, result))

    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All circular reference tests passed!\n")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
