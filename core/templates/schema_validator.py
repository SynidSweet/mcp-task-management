"""
Template schema validation using JSON schema.
Provides validation for template structure and content.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path


TEMPLATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Task Template Schema",
    "type": "object",
    "required": ["metadata", "sections"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["template_id", "name", "description", "template_type"],
            "properties": {
                "template_id": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_-]+$",
                    "minLength": 1,
                    "maxLength": 100
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200
                },
                "description": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1000
                },
                "template_type": {
                    "type": "string",
                    "enum": ["task", "documentation", "sprint", "journal", "status_update", "technical", "achievement"]
                },
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+\\.\\d+$",
                    "default": "1.0.0"
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time"
                },
                "updated_at": {
                    "type": "string", 
                    "format": "date-time"
                },
                "created_by": {
                    "type": "string",
                    "default": "system"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "default": []
                },
                "variables": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$"
                    },
                    "default": []
                },
                "scope": {
                    "type": "string",
                    "enum": ["project", "global"],
                    "default": "project"
                }
            },
            "additionalProperties": False
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["section_name", "content"],
                "properties": {
                    "section_name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "content": {
                        "type": "string",
                        "minLength": 1
                    },
                    "placement_hint": {
                        "type": "string",
                        "pattern": "^(after|before|replace):.+$"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "default": "medium"
                    },
                    "order": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0
                    },
                    "metadata": {
                        "type": "object",
                        "default": {}
                    }
                },
                "additionalProperties": False
            }
        },
        "full_template": {
            "type": "string",
            "default": ""
        },
        "variables": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                    "type": ["string", "number", "boolean", "null"]
                }
            },
            "default": {}
        }
    },
    "additionalProperties": False
}

TEMPLATE_COLLECTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#", 
    "title": "Template Collection Schema",
    "type": "object",
    "required": ["name", "description", "templates"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500
        },
        "templates": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z0-9_-]+$": TEMPLATE_SCHEMA
            }
        },
        "metadata": {
            "type": "object",
            "default": {}
        }
    },
    "additionalProperties": False
}


class TemplateValidator:
    """Validates templates against JSON schema."""
    
    def __init__(self):
        try:
            import jsonschema
            self.jsonschema = jsonschema
            self.validator = jsonschema.Draft7Validator(TEMPLATE_SCHEMA)
            self.collection_validator = jsonschema.Draft7Validator(TEMPLATE_COLLECTION_SCHEMA)
            self.available = True
        except ImportError:
            self.jsonschema = None
            self.validator = None
            self.collection_validator = None
            self.available = False
    
    def validate_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate template data against schema.
        
        Returns:
            Validation result with status and errors
        """
        if not self.available:
            return {
                "valid": True,
                "errors": [],
                "warnings": ["JSON Schema validation not available - jsonschema package not installed"]
            }
        
        try:
            # Validate against schema
            errors = []
            for error in self.validator.iter_errors(template_data):
                errors.append({
                    "path": ".".join(str(p) for p in error.path),
                    "message": error.message,
                    "value": error.instance
                })
            
            # Additional custom validations
            warnings = []
            custom_issues = self._custom_validation(template_data)
            warnings.extend(custom_issues.get("warnings", []))
            errors.extend(custom_issues.get("errors", []))
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [{"path": "root", "message": f"Validation error: {str(e)}"}],
                "warnings": []
            }
    
    def validate_template_collection(self, collection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate template collection against schema."""
        if not self.available:
            return {
                "valid": True,
                "errors": [],
                "warnings": ["JSON Schema validation not available"]
            }
        
        try:
            errors = []
            for error in self.collection_validator.iter_errors(collection_data):
                errors.append({
                    "path": ".".join(str(p) for p in error.path),
                    "message": error.message,
                    "value": error.instance
                })
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": []
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [{"path": "root", "message": f"Validation error: {str(e)}"}],
                "warnings": []
            }
    
    def _custom_validation(self, template_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Perform custom validation logic."""
        errors = []
        warnings = []
        
        try:
            metadata = template_data.get("metadata", {})
            sections = template_data.get("sections", [])
            full_template = template_data.get("full_template", "")
            variables = template_data.get("variables", {})
            
            # Check template content consistency
            if not full_template and not sections:
                errors.append({
                    "path": "content",
                    "message": "Template must have either full_template or sections"
                })
            
            # Check variable consistency
            declared_vars = set(metadata.get("variables", []))
            used_vars = set()
            
            # Extract variables from content
            import re
            content_to_check = full_template
            for section in sections:
                content_to_check += " " + section.get("content", "")
            
            var_pattern = r'\{\{(\w+)\}\}'
            used_vars.update(re.findall(var_pattern, content_to_check))
            
            # Check for undeclared variables
            undeclared = used_vars - declared_vars
            if undeclared:
                warnings.append(f"Variables used but not declared: {', '.join(sorted(undeclared))}")
            
            # Check for unused declared variables
            unused = declared_vars - used_vars
            if unused:
                warnings.append(f"Variables declared but not used: {', '.join(sorted(unused))}")
            
            # Check section ordering
            orders = [section.get("order", 0) for section in sections]
            if len(orders) != len(set(orders)) and len(orders) > 1:
                warnings.append("Multiple sections have the same order value")
            
            # Check placement hints format
            for i, section in enumerate(sections):
                placement_hint = section.get("placement_hint")
                if placement_hint:
                    if not re.match(r'^(after|before|replace):.+', placement_hint):
                        errors.append({
                            "path": f"sections[{i}].placement_hint",
                            "message": f"Invalid placement hint format: {placement_hint}"
                        })
            
            return {"errors": errors, "warnings": warnings}
            
        except Exception as e:
            return {"errors": [{"path": "custom_validation", "message": str(e)}], "warnings": []}
    
    def validate_template_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate template from file."""
        try:
            with open(file_path, 'r') as f:
                template_data = json.load(f)
            
            result = self.validate_template(template_data)
            result["file_path"] = str(file_path)
            return result
            
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [{"path": "file", "message": f"Invalid JSON: {str(e)}"}],
                "warnings": [],
                "file_path": str(file_path)
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [{"path": "file", "message": f"Error reading file: {str(e)}"}],
                "warnings": [],
                "file_path": str(file_path)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the template schema."""
        return TEMPLATE_SCHEMA
    
    def get_collection_schema(self) -> Dict[str, Any]:
        """Get the template collection schema."""
        return TEMPLATE_COLLECTION_SCHEMA
    
    def is_available(self) -> bool:
        """Check if validation is available."""
        return self.available


# Global validator instance
template_validator = TemplateValidator()


def validate_template(template_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for template validation."""
    return template_validator.validate_template(template_data)


def validate_template_collection(collection_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for collection validation."""
    return template_validator.validate_template_collection(collection_data)


def validate_template_file(file_path: str) -> Dict[str, Any]:
    """Convenience function for file validation."""
    return template_validator.validate_template_file(Path(file_path))