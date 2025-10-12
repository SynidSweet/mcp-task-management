"""
Template manager that provides high-level template operations.
Integrates with storage system and handles template resolution.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from .models import Template, TemplateCollection, TemplateType, TemplateMetadata, TemplateSection


class TemplateManager:
    """
    High-level template management with resolution logic.
    Handles project vs global template resolution and caching.
    """
    
    def __init__(self, storage_manager):
        self.storage_manager = storage_manager
        self.template_store = storage_manager.template_store
        self.logger = logging.getLogger(__name__)
        
        # Cache for resolved templates
        self._resolved_cache = {}
        
    async def get_template(self, template_id: str, template_type: str = None) -> Optional[Template]:
        """
        Get a template with resolution logic (project overrides global).
        
        Args:
            template_id: The template identifier
            template_type: Optional specific template type to search
            
        Returns:
            Template if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"{template_id}_{template_type or 'all'}"
            if cache_key in self._resolved_cache:
                return self._resolved_cache[cache_key]
            
            # Search project-level first (higher priority)
            template = await self._search_template_in_scope(template_id, template_type, "project")
            
            if not template:
                # Fallback to global templates
                template = await self._search_template_in_scope(template_id, template_type, "global")
            
            # Cache the result
            if template:
                self._resolved_cache[cache_key] = template
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    async def _search_template_in_scope(self, template_id: str, template_type: str, scope: str) -> Optional[Template]:
        """Search for template in specific scope."""
        try:
            # Search all template types using the scope-aware list_templates method
            template_types = [template_type] if template_type else None
            templates = await self.template_store.list_templates(template_type=template_types[0] if template_types else None, scope=scope)
            
            for template in templates:
                if template.metadata.template_id == template_id:
                    return template
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching template {template_id} in {scope}: {e}")
            return None
    
    async def save_template(self, template: Template, scope: str = "project") -> bool:
        """
        Save a template to storage.
        
        Args:
            template: The template to save
            scope: "project" or "global" scope
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Update template metadata
            template.metadata.scope = scope
            
            # Determine template type file
            template_type = f"{template.metadata.template_type.value}_templates"
            
            # Clear cache for this template
            self._invalidate_cache(template.metadata.template_id)
            
            # Save using storage manager
            return await self.storage_manager.save_template(template, template_type, scope)
            
        except Exception as e:
            self.logger.error(f"Error saving template {template.metadata.template_id}: {e}")
            return False
    
    async def delete_template(self, template_id: str, template_type: str = None, scope: str = "project") -> bool:
        """
        Delete a template from storage.
        
        Args:
            template_id: The template identifier
            template_type: Optional specific template type
            scope: "project" or "global" scope
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Delete using storage manager
            result = await self.storage_manager.delete_template(template_id, template_type, scope)
            
            # Clear cache after successful deletion
            if result:
                self._invalidate_cache(template_id)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error deleting template {template_id}: {e}")
            return False
    
    async def list_templates(self, template_type: TemplateType = None, scope: str = None, include_inherited: bool = True) -> List[Template]:
        """
        List templates with optional filtering.
        
        Args:
            template_type: Filter by template type
            scope: Filter by scope ("project", "global", or None for both)
            include_inherited: Whether to include global templates when scope is "project"
            
        Returns:
            List of templates
        """
        try:
            templates = []
            
            # Determine template type string
            type_str = f"{template_type.value}_templates" if template_type else None
            
            if scope:
                # Get templates from specific scope
                scope_templates = await self.template_store.list_templates(type_str, scope)
                templates.extend(scope_templates)
                
                # If project scope and include_inherited, also get global templates
                if scope == "project" and include_inherited:
                    global_templates = await self.template_store.list_templates(type_str, "global")
                    # Only add global templates that don't have project overrides
                    project_ids = {t.metadata.template_id for t in templates}
                    for global_template in global_templates:
                        if global_template.metadata.template_id not in project_ids:
                            templates.append(global_template)
            else:
                # Get templates from all scopes with project priority
                project_templates = await self.template_store.list_templates(type_str, "project")
                global_templates = await self.template_store.list_templates(type_str, "global")
                
                templates.extend(project_templates)
                
                # Add global templates that don't have project overrides
                project_ids = {t.metadata.template_id for t in project_templates}
                for global_template in global_templates:
                    if global_template.metadata.template_id not in project_ids:
                        templates.append(global_template)
            
            return templates
            
        except Exception as e:
            self.logger.error(f"Error listing templates: {e}")
            return []
    
    async def create_template(
        self, 
        template_id: str,
        name: str,
        description: str,
        template_type: TemplateType,
        content: str = "",
        sections: List[TemplateSection] = None,
        variables: Dict[str, Any] = None,
        tags: List[str] = None,
        scope: str = "project"
    ) -> Template:
        """
        Create a new template.
        
        Args:
            template_id: Unique identifier for the template
            name: Human-readable name
            description: Template description
            template_type: Type of template
            content: Template content (full template)
            sections: List of template sections
            variables: Template variables
            tags: Template tags
            scope: Template scope
            
        Returns:
            Created template
        """
        try:
            # Create metadata
            metadata = TemplateMetadata(
                template_id=template_id,
                name=name,
                description=description,
                template_type=template_type,
                tags=tags or [],
                variables=list(variables.keys()) if variables else [],
                scope=scope
            )
            
            # Create template
            template = Template(
                metadata=metadata,
                sections=sections or [],
                full_template=content,
                variables=variables or {}
            )
            
            # If no full template but sections exist, build it
            if not content and sections:
                template._rebuild_full_template()
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error creating template {template_id}: {e}")
            raise
    
    async def render_template(self, template_id: str, variables: Dict[str, Any] = None) -> Optional[str]:
        """
        Render a template with provided variables.
        
        Args:
            template_id: Template to render
            variables: Variables to substitute
            
        Returns:
            Rendered template content
        """
        try:
            template = await self.get_template(template_id)
            if not template:
                return None
            
            return template.render(variables)
            
        except Exception as e:
            self.logger.error(f"Error rendering template {template_id}: {e}")
            return None
    
    async def get_template_collection(self, collection_name: str) -> Optional[TemplateCollection]:
        """Get a template collection by name."""
        try:
            collections_data = await self.template_store.get_data('collections')
            if not collections_data:
                return None
            
            collection_data = collections_data.data.get('collections', {}).get(collection_name)
            if not collection_data:
                return None
            
            return TemplateCollection.from_dict(collection_data)
            
        except Exception as e:
            self.logger.error(f"Error getting template collection {collection_name}: {e}")
            return None
    
    async def save_template_collection(self, collection: TemplateCollection, scope: str = "project") -> bool:
        """Save a template collection."""
        try:
            collections_data = await self.template_store.get_data('collections')
            if not collections_data:
                from ..storage.base import SyncableData
                from datetime import datetime, timezone
                collections_data = SyncableData(
                    data={'collections': {}},
                    timestamp=datetime.now(timezone.utc),
                    hash="",
                    version=1
                )
            
            collections_data.data['collections'][collection.name] = collection.to_dict()
            
            return await self.template_store.save_data('collections', collections_data, scope)
            
        except Exception as e:
            self.logger.error(f"Error saving template collection {collection.name}: {e}")
            return False
    
    def _invalidate_cache(self, template_id: str = None):
        """Invalidate template cache."""
        if template_id:
            # Remove specific template from cache
            keys_to_remove = [key for key in self._resolved_cache.keys() if key.startswith(f"{template_id}_")]
            for key in keys_to_remove:
                del self._resolved_cache[key]
        else:
            # Clear entire cache
            self._resolved_cache.clear()
    
    async def validate_template(self, template: Template) -> Dict[str, Any]:
        """
        Validate a template for consistency and correctness.
        
        Returns:
            Validation result with status and issues
        """
        issues = []
        warnings = []
        
        try:
            # Check required fields
            if not template.metadata.template_id:
                issues.append("Template ID is required")
            
            if not template.metadata.name:
                issues.append("Template name is required")
            
            if not template.metadata.description:
                warnings.append("Template description is recommended")
            
            # Check template content
            if not template.full_template and not template.sections:
                issues.append("Template must have either full_template or sections")
            
            # Check variable consistency
            declared_vars = set(template.metadata.variables)
            used_vars = set()
            
            # Extract variables from template content
            import re
            content = template.full_template
            for section in template.sections:
                content += section.content
            
            var_pattern = r'\{\{(\w+)\}\}'
            used_vars.update(re.findall(var_pattern, content))
            
            # Check for undeclared variables
            undeclared = used_vars - declared_vars
            if undeclared:
                warnings.append(f"Variables used but not declared: {', '.join(undeclared)}")
            
            # Check for unused declared variables
            unused = declared_vars - used_vars
            if unused:
                warnings.append(f"Variables declared but not used: {', '.join(unused)}")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'warnings': warnings,
                'template_id': template.metadata.template_id
            }
            
        except Exception as e:
            return {
                'valid': False,
                'issues': [f"Validation error: {str(e)}"],
                'warnings': [],
                'template_id': getattr(template.metadata, 'template_id', 'unknown')
            }
    
    async def get_template_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for templates."""
        try:
            all_templates = await self.list_templates()
            
            stats = {
                'total_templates': len(all_templates),
                'by_type': {},
                'by_scope': {'project': 0, 'global': 0},
                'templates': []
            }
            
            for template in all_templates:
                # Count by type
                type_name = template.metadata.template_type.value
                stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1
                
                # Count by scope
                scope = template.metadata.scope
                stats['by_scope'][scope] = stats['by_scope'].get(scope, 0) + 1
                
                # Add template info
                stats['templates'].append({
                    'id': template.metadata.template_id,
                    'name': template.metadata.name,
                    'type': type_name,
                    'scope': scope,
                    'created_at': template.metadata.created_at.isoformat() if template.metadata.created_at else None,
                    'tags': template.metadata.tags
                })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting template usage stats: {e}")
            return {
                'total_templates': 0,
                'by_type': {},
                'by_scope': {},
                'templates': [],
                'error': str(e)
            }