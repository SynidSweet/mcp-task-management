#!/usr/bin/env python3
"""
Tests for Specification Validation System

Tests the validation status calculation, query enhancements, and validated table integration.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import validation helpers
from tools.specification_tools import (
    calculate_validation_status,
    fetch_validated_specifications,
    enhance_with_validation_status
)


class TestValidationStatusCalculation:
    """Test calculate_validation_status() function."""

    def test_status_new_when_no_validated_record(self):
        """Should return 'new' when validated_spec is None."""
        current_spec = {
            'id': '123',
            'display_id': 'test_spec',
            'specification_name': 'Test Spec',
            'description': 'Test description'
        }

        status = calculate_validation_status(current_spec, None)
        assert status == "new"

    def test_status_validated_when_all_fields_match(self):
        """Should return 'validated' when all key fields match."""
        current_spec = {
            'id': '123',
            'display_id': 'test_spec',
            'specification_name': 'Test Spec',
            'specification_type': 'api',
            'description': 'Test description',
            'parent_display_id': 'parent_spec'
        }

        validated_spec = {
            'id': '123',
            'display_id': 'test_spec',
            'specification_name': 'Test Spec',
            'specification_type': 'api',
            'description': 'Test description',
            'parent_display_id': 'parent_spec',
            'validated_at': '2025-10-20T12:00:00Z'
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "validated"

    def test_status_modified_when_specification_name_differs(self):
        """Should return 'modified' when specification_name differs."""
        current_spec = {
            'specification_name': 'Updated Name',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None
        }

        validated_spec = {
            'specification_name': 'Original Name',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "modified"

    def test_status_modified_when_description_differs(self):
        """Should return 'modified' when description differs."""
        current_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'New description',
            'parent_display_id': None
        }

        validated_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Old description',
            'parent_display_id': None
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "modified"

    def test_status_modified_when_type_differs(self):
        """Should return 'modified' when specification_type differs."""
        current_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'component',
            'description': 'Test',
            'parent_display_id': None
        }

        validated_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "modified"

    def test_status_modified_when_display_id_differs(self):
        """Should return 'modified' when display_id differs."""
        current_spec = {
            'specification_name': 'Test',
            'display_id': 'new_id',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None
        }

        validated_spec = {
            'specification_name': 'Test',
            'display_id': 'old_id',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "modified"

    def test_status_modified_when_parent_differs(self):
        """Should return 'modified' when parent_display_id differs."""
        current_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': 'new_parent'
        }

        validated_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': 'old_parent'
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "modified"

    def test_ignores_non_key_fields(self):
        """Should ignore changes to non-key fields (approved, implemented, etc)."""
        current_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None,
            'approved': True,
            'implemented': True,
            'level_depth': 2
        }

        validated_spec = {
            'specification_name': 'Test',
            'display_id': 'test_spec',
            'specification_type': 'api',
            'description': 'Test',
            'parent_display_id': None,
            'approved': False,
            'implemented': False,
            'level_depth': 1
        }

        status = calculate_validation_status(current_spec, validated_spec)
        assert status == "validated"  # Non-key fields don't affect status


class TestEnhanceWithValidationStatus:
    """Test enhance_with_validation_status() function."""

    def test_adds_status_new_for_unvalidated_specs(self):
        """Should add validation_status='new' when no validated record exists."""
        specifications = [
            {'id': '123', 'specification_name': 'Test', 'display_id': 'test'}
        ]
        validated_map = {}  # No validated records

        result = enhance_with_validation_status(specifications, validated_map, 'minimal')

        assert result[0]['validation_status'] == 'new'

    def test_adds_status_validated_for_matching_specs(self):
        """Should add validation_status='validated' when specs match."""
        specifications = [
            {
                'id': '123',
                'specification_name': 'Test',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        ]
        validated_map = {
            '123': {
                'specification_name': 'Test',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None,
                'validated_at': '2025-10-20T12:00:00Z'
            }
        }

        result = enhance_with_validation_status(specifications, validated_map, 'minimal')

        assert result[0]['validation_status'] == 'validated'

    def test_adds_status_modified_for_differing_specs(self):
        """Should add validation_status='modified' when specs differ."""
        specifications = [
            {
                'id': '123',
                'specification_name': 'Updated Name',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        ]
        validated_map = {
            '123': {
                'specification_name': 'Original Name',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None,
                'validated_at': '2025-10-20T12:00:00Z'
            }
        }

        result = enhance_with_validation_status(specifications, validated_map, 'minimal')

        assert result[0]['validation_status'] == 'modified'

    def test_adds_validation_hint_in_compact_mode(self):
        """Should add validation_hint in compact mode for modified specs."""
        specifications = [
            {
                'id': '123',
                'specification_name': 'Updated',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        ]
        validated_map = {
            '123': {
                'specification_name': 'Original',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        }

        result = enhance_with_validation_status(specifications, validated_map, 'compact')

        assert 'validation_hint' in result[0]
        assert result[0]['validation_hint'] == 'Has unvalidated changes'

    def test_no_validation_hint_for_validated_specs(self):
        """Should not add validation_hint for validated specs even in compact mode."""
        specifications = [
            {
                'id': '123',
                'specification_name': 'Test',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        ]
        validated_map = {
            '123': {
                'specification_name': 'Test',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        }

        result = enhance_with_validation_status(specifications, validated_map, 'compact')

        assert 'validation_hint' not in result[0]

    def test_adds_validated_snapshot_in_full_mode(self):
        """Should add validated_snapshot in full mode."""
        specifications = [
            {
                'id': '123',
                'specification_name': 'Test',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Test',
                'parent_display_id': None
            }
        ]
        validated_map = {
            '123': {
                'specification_name': 'Validated Name',
                'display_id': 'test',
                'specification_type': 'api',
                'description': 'Validated Description',
                'parent_display_id': None,
                'validated_at': '2025-10-20T12:00:00Z',
                'validated_by': 'user@example.com'
            }
        }

        result = enhance_with_validation_status(specifications, validated_map, 'full')

        assert 'validated_snapshot' in result[0]
        snapshot = result[0]['validated_snapshot']
        assert snapshot['specification_name'] == 'Validated Name'
        assert snapshot['description'] == 'Validated Description'
        assert snapshot['validated_at'] == '2025-10-20T12:00:00Z'
        assert snapshot['validated_by'] == 'user@example.com'

    def test_no_snapshot_in_minimal_mode(self):
        """Should not add validated_snapshot in minimal mode."""
        specifications = [
            {'id': '123', 'specification_name': 'Test', 'display_id': 'test'}
        ]
        validated_map = {
            '123': {
                'specification_name': 'Test',
                'validated_at': '2025-10-20T12:00:00Z'
            }
        }

        result = enhance_with_validation_status(specifications, validated_map, 'minimal')

        assert 'validated_snapshot' not in result[0]

    def test_handles_multiple_specifications(self):
        """Should correctly enhance multiple specifications."""
        specifications = [
            {'id': '1', 'specification_name': 'New', 'display_id': 'new'},
            {'id': '2', 'specification_name': 'Modified', 'display_id': 'mod'},
            {'id': '3', 'specification_name': 'Validated', 'display_id': 'val'}
        ]
        validated_map = {
            '2': {'specification_name': 'Original', 'display_id': 'mod'},
            '3': {'specification_name': 'Validated', 'display_id': 'val'}
        }

        result = enhance_with_validation_status(specifications, validated_map, 'minimal')

        assert result[0]['validation_status'] == 'new'
        assert result[1]['validation_status'] == 'modified'
        assert result[2]['validation_status'] == 'validated'


def run_tests():
    """Run all validation tests."""
    print("Running Specification Validation System Tests...")
    print()

    # Test validation status calculation
    print("Testing calculate_validation_status()...")
    test_class = TestValidationStatusCalculation()

    test_class.test_status_new_when_no_validated_record()
    print("  ✓ Returns 'new' for unvalidated specs")

    test_class.test_status_validated_when_all_fields_match()
    print("  ✓ Returns 'validated' when fields match")

    test_class.test_status_modified_when_specification_name_differs()
    test_class.test_status_modified_when_description_differs()
    test_class.test_status_modified_when_type_differs()
    test_class.test_status_modified_when_display_id_differs()
    test_class.test_status_modified_when_parent_differs()
    print("  ✓ Returns 'modified' when any key field differs")

    test_class.test_ignores_non_key_fields()
    print("  ✓ Ignores non-key field changes")

    print()

    # Test enhancement function
    print("Testing enhance_with_validation_status()...")
    test_enhance = TestEnhanceWithValidationStatus()

    test_enhance.test_adds_status_new_for_unvalidated_specs()
    print("  ✓ Adds 'new' status correctly")

    test_enhance.test_adds_status_validated_for_matching_specs()
    print("  ✓ Adds 'validated' status correctly")

    test_enhance.test_adds_status_modified_for_differing_specs()
    print("  ✓ Adds 'modified' status correctly")

    test_enhance.test_adds_validation_hint_in_compact_mode()
    test_enhance.test_no_validation_hint_for_validated_specs()
    print("  ✓ Adds validation hints in compact mode")

    test_enhance.test_adds_validated_snapshot_in_full_mode()
    test_enhance.test_no_snapshot_in_minimal_mode()
    print("  ✓ Adds validated snapshots in full mode")

    test_enhance.test_handles_multiple_specifications()
    print("  ✓ Handles multiple specifications correctly")

    print()
    print("=" * 60)
    print("All validation tests passed! ✓")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()
