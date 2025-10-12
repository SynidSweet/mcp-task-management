"""
Template data models for the task management system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class TemplateType(Enum):
    """Template types for different use cases."""
    TASK = "task"
    DOCUMENTATION = "documentation"  
    SPRINT = "sprint"
    JOURNAL = "journal"
    STATUS_UPDATE = "status_update"
    TECHNICAL = "technical"
    ACHIEVEMENT = "achievement"


@dataclass
class TemplateSection:
    """A section within a template."""
    section_name: str
    content: str
    placement_hint: Optional[str] = None  # e.g., "after:## Current Status"
    priority: str = "medium"  # high, medium, low
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateMetadata:
    """Metadata for template tracking and validation."""
    template_id: str
    name: str
    description: str
    template_type: TemplateType
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)  # Template variables like {{task_title}}
    scope: str = "project"  # project or global
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at


@dataclass  
class Template:
    """A complete template with metadata and content."""
    metadata: TemplateMetadata
    sections: List[TemplateSection] = field(default_factory=list)
    full_template: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)  # Variable values for rendering
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for storage."""
        return {
            'metadata': {
                'template_id': self.metadata.template_id,
                'name': self.metadata.name,
                'description': self.metadata.description,
                'template_type': self.metadata.template_type.value,
                'version': self.metadata.version,
                'created_at': self.metadata.created_at.isoformat() if self.metadata.created_at else None,
                'updated_at': self.metadata.updated_at.isoformat() if self.metadata.updated_at else None,
                'created_by': self.metadata.created_by,
                'tags': self.metadata.tags,
                'variables': self.metadata.variables,
                'scope': self.metadata.scope
            },
            'sections': [
                {
                    'section_name': section.section_name,
                    'content': section.content,
                    'placement_hint': section.placement_hint,
                    'priority': section.priority,
                    'order': section.order,
                    'metadata': section.metadata
                } for section in self.sections
            ],
            'full_template': self.full_template,
            'variables': self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create template from dictionary."""
        metadata_dict = data['metadata']
        metadata = TemplateMetadata(
            template_id=metadata_dict['template_id'],
            name=metadata_dict['name'],
            description=metadata_dict['description'],
            template_type=TemplateType(metadata_dict['template_type']),
            version=metadata_dict.get('version', '1.0.0'),
            created_at=datetime.fromisoformat(metadata_dict['created_at'].replace('Z', '+00:00')) if metadata_dict.get('created_at') else None,
            updated_at=datetime.fromisoformat(metadata_dict['updated_at'].replace('Z', '+00:00')) if metadata_dict.get('updated_at') else None,
            created_by=metadata_dict.get('created_by', 'system'),
            tags=metadata_dict.get('tags', []),
            variables=metadata_dict.get('variables', []),
            scope=metadata_dict.get('scope', 'project')
        )
        
        sections = [
            TemplateSection(
                section_name=section_dict['section_name'],
                content=section_dict['content'],
                placement_hint=section_dict.get('placement_hint'),
                priority=section_dict.get('priority', 'medium'),
                order=section_dict.get('order', 0),
                metadata=section_dict.get('metadata', {})
            ) for section_dict in data.get('sections', [])
        ]
        
        return cls(
            metadata=metadata,
            sections=sections,
            full_template=data.get('full_template', ''),
            variables=data.get('variables', {})
        )
    
    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """Render template with provided variables."""
        if variables:
            self.variables.update(variables)
        
        content = self.full_template
        for var_name, var_value in self.variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, str(var_value))
        
        return content
    
    def add_section(self, section: TemplateSection):
        """Add a section to the template."""
        self.sections.append(section)
        # Update full_template if needed
        if not self.full_template:
            self._rebuild_full_template()
    
    def _rebuild_full_template(self):
        """Rebuild full template from sections."""
        sorted_sections = sorted(self.sections, key=lambda x: x.order)
        self.full_template = "\n\n".join(section.content for section in sorted_sections)


@dataclass
class TemplateCollection:
    """A collection of related templates."""
    name: str
    description: str
    templates: Dict[str, Template] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_template(self, template: Template):
        """Add a template to the collection."""
        self.templates[template.metadata.template_id] = template
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[Template]:
        """List all templates in the collection."""
        return list(self.templates.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'templates': {
                template_id: template.to_dict()
                for template_id, template in self.templates.items()
            },
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateCollection':
        """Create collection from dictionary."""
        collection = cls(
            name=data['name'],
            description=data['description'],
            metadata=data.get('metadata', {})
        )
        
        for template_id, template_data in data.get('templates', {}).items():
            template = Template.from_dict(template_data)
            collection.add_template(template)
        
        return collection