"""
Usage examples for SharedIdentifierManager integration.
These examples show how to integrate the SharedIdentifierManager with document and entity systems.
"""

import asyncio
from typing import Dict, Any, Optional
from .shared_id_manager import SharedIdentifierManager


class DocumentSystemIntegration:
    """Example integration with a document management system."""
    
    def __init__(self, shared_id_manager: SharedIdentifierManager):
        self.shared_id_manager = shared_id_manager
    
    async def create_document(self, title: str, content: str, 
                             custom_display_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new document with managed identifier."""
        try:
            # Generate identifier
            id_result = await self.shared_id_manager.generate_identifier(
                display_id=custom_display_id,
                system_type='document'
            )
            
            if id_result['status'] == 'error':
                return id_result
            
            # Create document record (this would integrate with actual document storage)
            document = {
                'id': id_result['id'],
                'display_id': id_result['display_id'],
                'title': title,
                'content': content,
                'system_type': 'document',
                'created_at': id_result.get('created_at')
            }
            
            return {
                'status': 'success',
                'document': document,
                'identifier_info': id_result
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create document: {str(e)}'
            }
    
    async def create_reference_to_entity(self, document_id: str, 
                                       entity_display_id: str) -> Dict[str, Any]:
        """Create a reference from document to entity using display_id."""
        try:
            # Verify entity exists
            entity_info = await self.shared_id_manager.get_identifier_info(entity_display_id)
            if entity_info['status'] == 'error' or not entity_info.get('found'):
                return {
                    'status': 'error',
                    'message': f'Entity with display_id {entity_display_id} not found'
                }
            
            # Create cross-reference (this would integrate with actual cross-reference storage)
            cross_reference = {
                'source_type': 'document',
                'source_id': document_id,
                'target_type': 'entity',
                'target_id': entity_info['id'],
                'target_display_id': entity_display_id,
                'reference_type': 'relates_to'
            }
            
            return {
                'status': 'success',
                'cross_reference': cross_reference,
                'entity_info': entity_info
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create reference: {str(e)}'
            }


class EntitySystemIntegration:
    """Example integration with entity management system."""
    
    def __init__(self, shared_id_manager: SharedIdentifierManager):
        self.shared_id_manager = shared_id_manager
    
    async def create_entity(self, entity_path: str, entity_name: str,
                           custom_display_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new entity with managed identifier."""
        try:
            # Generate identifier
            id_result = await self.shared_id_manager.generate_identifier(
                display_id=custom_display_id,
                system_type='entity'
            )
            
            if id_result['status'] == 'error':
                return id_result
            
            # Create entity record (this would integrate with actual entity storage)
            entity = {
                'id': id_result['id'],
                'display_id': id_result['display_id'],
                'entity_path': entity_path,
                'entity_name': entity_name,
                'system_type': 'entity',
                'created_at': id_result.get('created_at')
            }
            
            return {
                'status': 'success',
                'entity': entity,
                'identifier_info': id_result
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create entity: {str(e)}'
            }
    
    async def update_entity_display_id(self, entity_uuid: str, 
                                     new_display_id: str) -> Dict[str, Any]:
        """Update entity display ID through the shared manager."""
        return await self.shared_id_manager.update_display_id(entity_uuid, new_display_id)


class CrossReferenceManager:
    """Manages cross-references between documents and entities using display IDs."""
    
    def __init__(self, shared_id_manager: SharedIdentifierManager):
        self.shared_id_manager = shared_id_manager
    
    async def resolve_display_id_reference(self, display_id: str) -> Dict[str, Any]:
        """Resolve a display ID to its full information."""
        try:
            # Get identifier info
            info = await self.shared_id_manager.get_identifier_info(display_id)
            
            if info['status'] == 'error' or not info.get('found'):
                return {
                    'status': 'error',
                    'message': f'Display ID {display_id} not found'
                }
            
            return {
                'status': 'success',
                'resolved': True,
                'display_id': display_id,
                'uuid': info['id'],
                'system_type': info['entity_type'],
                'is_auto_generated': info['is_auto_generated'],
                'created_at': info['created_at']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to resolve display ID: {str(e)}'
            }
    
    async def parse_content_references(self, content: str) -> Dict[str, Any]:
        """Parse content for |display_id| references and resolve them."""
        import re
        
        try:
            # Find all |display_id| patterns
            reference_pattern = r'\|([a-zA-Z0-9_-]+)\|'
            matches = re.findall(reference_pattern, content)
            
            resolved_references = {}
            unresolved_references = []
            
            for display_id in set(matches):  # Remove duplicates
                resolution = await self.resolve_display_id_reference(display_id)
                if resolution['status'] == 'success':
                    resolved_references[display_id] = resolution
                else:
                    unresolved_references.append({
                        'display_id': display_id,
                        'error': resolution['message']
                    })
            
            return {
                'status': 'success',
                'total_references': len(set(matches)),
                'resolved_count': len(resolved_references),
                'unresolved_count': len(unresolved_references),
                'resolved_references': resolved_references,
                'unresolved_references': unresolved_references
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to parse references: {str(e)}'
            }


# Example usage functions

async def example_document_workflow(shared_id_manager: SharedIdentifierManager):
    """Example workflow for creating documents with references."""
    
    doc_integration = DocumentSystemIntegration(shared_id_manager)
    entity_integration = EntitySystemIntegration(shared_id_manager)
    cross_ref_manager = CrossReferenceManager(shared_id_manager)
    
    print("📄 Document Workflow Example")
    print("-" * 30)
    
    # Create an entity first
    entity_result = await entity_integration.create_entity(
        entity_path="auth.user_management",
        entity_name="User Authentication Module",
        custom_display_id="auth-module"
    )
    print(f"Created entity: {entity_result}")
    
    # Create a document that references the entity
    doc_content = """
    # Authentication System Documentation
    
    This document describes the authentication system. The main component 
    is the |auth-module| which handles user login and session management.
    
    Related components:
    - |user-session| - Session management
    - |password-policy| - Password validation
    """
    
    doc_result = await doc_integration.create_document(
        title="Authentication System Guide",
        content=doc_content,
        custom_display_id="auth-system-doc"
    )
    print(f"Created document: {doc_result}")
    
    # Parse references in the document
    references = await cross_ref_manager.parse_content_references(doc_content)
    print(f"Parsed references: {references}")
    
    return {
        'entity': entity_result,
        'document': doc_result,
        'references': references
    }


async def example_id_management_workflow(shared_id_manager: SharedIdentifierManager):
    """Example workflow for ID management operations."""
    
    print("🔧 ID Management Workflow Example")
    print("-" * 40)
    
    # Generate auto IDs for both systems
    auto_entity = await shared_id_manager.generate_identifier(system_type='entity')
    auto_document = await shared_id_manager.generate_identifier(system_type='document')
    
    print(f"Auto entity ID: {auto_entity}")
    print(f"Auto document ID: {auto_document}")
    
    # List all identifiers
    all_ids = await shared_id_manager.list_identifiers()
    print(f"All identifiers: {all_ids}")
    
    # Filter by system type
    entity_ids = await shared_id_manager.list_identifiers(system_type='entity')
    document_ids = await shared_id_manager.list_identifiers(system_type='document')
    
    print(f"Entity IDs only: {entity_ids}")
    print(f"Document IDs only: {document_ids}")
    
    return {
        'auto_entity': auto_entity,
        'auto_document': auto_document,
        'all_ids': all_ids,
        'entity_ids': entity_ids,
        'document_ids': document_ids
    }