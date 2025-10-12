"""
SharedIdentifierManager for managing unique IDs across both documents and entities.
This class ensures display ID uniqueness across both systems using the system_identifiers table.
"""

import re
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging

try:
    from supabase import Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

from ..machine_id import get_machine_id


class SharedIdentifierManager:
    """
    Manages unique identifiers across both documents and entities.
    
    Features:
    - Generate UUID + display_id pairs
    - Ensure uniqueness across both systems
    - Support auto-generated IDs (DOC-001, ENT-001) and custom IDs
    - Handle project/machine isolation
    - Provide comprehensive validation
    """
    
    def __init__(self, storage_manager, machine_id: str = None):
        """
        Initialize the SharedIdentifierManager.
        
        Args:
            storage_manager: StorageManager instance for database access
            machine_id: Optional machine ID override
        """
        self.storage_manager = storage_manager
        self.machine_id = machine_id or get_machine_id()
        self.logger = logging.getLogger(__name__)
        
        # Display ID patterns
        self.auto_id_patterns = {
            'document': r'^DOC-\d{3,}$',
            'entity': r'^ENT-\d{3,}$'
        }
        
        # Valid custom ID pattern (alphanumeric, hyphens, underscores)
        self.custom_id_pattern = r'^[a-zA-Z0-9_-]{2,50}$'
    
    async def generate_identifier(self, display_id: Optional[str] = None, 
                                 system_type: str = 'entity') -> Dict[str, Any]:
        """
        Generate a new unique identifier with UUID and display_id.
        
        Args:
            display_id: Optional custom display ID, will auto-generate if None
            system_type: Type of system ('entity' or 'document')
            
        Returns:
            Dict with 'id' (UUID), 'display_id', 'is_auto_generated', and metadata
        """
        try:
            # Validate system type
            if system_type not in ['entity', 'document']:
                return {
                    "status": "error",
                    "message": f"Invalid system_type: {system_type}. Must be 'entity' or 'document'"
                }
            
            # Get project_id from storage manager
            if not hasattr(self.storage_manager, 'remote_store') or not self.storage_manager.remote_store:
                return {
                    "status": "error", 
                    "message": "Database connection not available"
                }
            
            project_id = await self._get_project_id()
            if not project_id:
                return {
                    "status": "error",
                    "message": "Could not determine project ID"
                }
            
            # Generate or validate display_id
            if display_id is None:
                # Auto-generate display_id
                display_id = await self._generate_auto_display_id(project_id, system_type)
                is_auto_generated = True
            else:
                # Validate custom display_id
                validation_result = await self.validate_display_id(display_id)
                if validation_result['status'] == 'error':
                    return validation_result
                is_auto_generated = False
            
            # Generate UUID
            entity_uuid = str(uuid.uuid4())
            
            # Get sequence number for ordering
            sequence_number = await self._get_next_sequence_number(project_id, system_type)
            
            # Insert into system_identifiers table
            client = self.storage_manager.remote_store.client
            result = client.table('system_identifiers').insert({
                'project_id': project_id,
                'machine_id': self.machine_id,
                'display_id': display_id,
                'entity_type': system_type,
                'entity_uuid': entity_uuid,
                'sequence_number': sequence_number,
                'is_auto_generated': is_auto_generated,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            if result.data:
                return {
                    "status": "success",
                    "id": entity_uuid,
                    "display_id": display_id,
                    "system_type": system_type,
                    "is_auto_generated": is_auto_generated,
                    "sequence_number": sequence_number,
                    "project_id": project_id,
                    "machine_id": self.machine_id
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to create identifier in database"
                }
                
        except Exception as e:
            self.logger.error(f"Error generating identifier: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    async def display_id_exists(self, display_id: str) -> bool:
        """
        Check if a display ID already exists in the system.
        
        Args:
            display_id: Display ID to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            project_id = await self._get_project_id()
            if not project_id:
                return False
            
            client = self.storage_manager.remote_store.client
            result = client.table('system_identifiers')\
                          .select('id')\
                          .eq('project_id', project_id)\
                          .eq('machine_id', self.machine_id)\
                          .eq('display_id', display_id)\
                          .limit(1)\
                          .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            self.logger.error(f"Error checking display_id existence: {e}")
            return True  # Err on the side of caution
    
    async def get_identifier_info(self, identifier: str) -> Dict[str, Any]:
        """
        Get identifier information by UUID or display_id.
        
        Args:
            identifier: Either a UUID or display_id
            
        Returns:
            Dict with identifier information or error
        """
        try:
            project_id = await self._get_project_id()
            if not project_id:
                return {
                    "status": "error",
                    "message": "Could not determine project ID"
                }
            
            client = self.storage_manager.remote_store.client
            
            # Try as UUID first
            try:
                uuid.UUID(identifier)  # Validate UUID format
                result = client.table('system_identifiers')\
                              .select('*')\
                              .eq('project_id', project_id)\
                              .eq('machine_id', self.machine_id)\
                              .eq('entity_uuid', identifier)\
                              .execute()
            except ValueError:
                # Try as display_id
                result = client.table('system_identifiers')\
                              .select('*')\
                              .eq('project_id', project_id)\
                              .eq('machine_id', self.machine_id)\
                              .eq('display_id', identifier)\
                              .execute()
            
            if result.data:
                info = result.data[0]
                return {
                    "status": "success",
                    "found": True,
                    "id": info['entity_uuid'],
                    "display_id": info['display_id'],
                    "entity_type": info['entity_type'],
                    "is_auto_generated": info['is_auto_generated'],
                    "sequence_number": info['sequence_number'],
                    "created_at": info['created_at'],
                    "updated_at": info['updated_at']
                }
            else:
                return {
                    "status": "success",
                    "found": False,
                    "message": f"Identifier '{identifier}' not found"
                }
                
        except Exception as e:
            self.logger.error(f"Error getting identifier info: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    async def update_display_id(self, entity_uuid: str, new_display_id: str) -> Dict[str, Any]:
        """
        Update display_id for an existing entity with uniqueness check.
        
        Args:
            entity_uuid: UUID of the entity to update
            new_display_id: New display ID to set
            
        Returns:
            Dict with success/error status
        """
        try:
            # Validate new display_id
            validation_result = await self.validate_display_id(new_display_id)
            if validation_result['status'] == 'error':
                return validation_result
            
            project_id = await self._get_project_id()
            if not project_id:
                return {
                    "status": "error",
                    "message": "Could not determine project ID"
                }
            
            # Check if entity exists
            info_result = await self.get_identifier_info(entity_uuid)
            if info_result['status'] == 'error' or not info_result.get('found'):
                return {
                    "status": "error",
                    "message": f"Entity with UUID '{entity_uuid}' not found"
                }
            
            # Update the display_id
            client = self.storage_manager.remote_store.client
            result = client.table('system_identifiers')\
                          .update({
                              'display_id': new_display_id,
                              'is_auto_generated': False,  # Manual update makes it non-auto
                              'updated_at': datetime.now(timezone.utc).isoformat()
                          })\
                          .eq('project_id', project_id)\
                          .eq('machine_id', self.machine_id)\
                          .eq('entity_uuid', entity_uuid)\
                          .execute()
            
            if result.data:
                return {
                    "status": "success",
                    "message": f"Display ID updated to '{new_display_id}'",
                    "entity_uuid": entity_uuid,
                    "new_display_id": new_display_id
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update display ID"
                }
                
        except Exception as e:
            self.logger.error(f"Error updating display_id: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    async def generate_auto_display_id(self, system_type: str = 'entity') -> str:
        """
        Generate auto-display ID in DOC-001/ENT-001 format.
        
        Args:
            system_type: Type of system ('entity' or 'document')
            
        Returns:
            Generated display_id string
        """
        try:
            project_id = await self._get_project_id()
            if not project_id:
                return f"{'DOC' if system_type == 'document' else 'ENT'}-001"
            
            return await self._generate_auto_display_id(project_id, system_type)
            
        except Exception as e:
            self.logger.error(f"Error generating auto display ID: {e}")
            return f"{'DOC' if system_type == 'document' else 'ENT'}-001"
    
    async def validate_display_id(self, display_id: str) -> Dict[str, Any]:
        """
        Validate display_id format and uniqueness.
        
        Args:
            display_id: Display ID to validate
            
        Returns:
            Dict with validation results
        """
        try:
            # Check format
            if not re.match(self.custom_id_pattern, display_id):
                return {
                    "status": "error",
                    "message": f"Invalid display_id format. Must match pattern: {self.custom_id_pattern}"
                }
            
            # Check length
            if len(display_id) < 2 or len(display_id) > 50:
                return {
                    "status": "error",
                    "message": "Display ID must be between 2 and 50 characters"
                }
            
            # Check uniqueness
            if await self.display_id_exists(display_id):
                return {
                    "status": "error",
                    "message": f"Display ID '{display_id}' already exists"
                }
            
            return {
                "status": "success",
                "message": "Display ID is valid",
                "display_id": display_id
            }
            
        except Exception as e:
            self.logger.error(f"Error validating display_id: {e}")
            return {
                "status": "error",
                "message": f"Validation error: {str(e)}"
            }
    
    async def list_identifiers(self, system_type: Optional[str] = None, 
                              limit: int = 100) -> Dict[str, Any]:
        """
        List identifiers in the system, optionally filtered by type.
        
        Args:
            system_type: Optional filter by system type
            limit: Maximum number of results
            
        Returns:
            Dict with list of identifiers
        """
        try:
            project_id = await self._get_project_id()
            if not project_id:
                return {
                    "status": "error",
                    "message": "Could not determine project ID"
                }
            
            client = self.storage_manager.remote_store.client
            query = client.table('system_identifiers')\
                         .select('*')\
                         .eq('project_id', project_id)\
                         .eq('machine_id', self.machine_id)\
                         .order('sequence_number', desc=False)\
                         .limit(limit)
            
            if system_type:
                query = query.eq('entity_type', system_type)
            
            result = query.execute()
            
            return {
                "status": "success",
                "identifiers": result.data,
                "count": len(result.data),
                "system_type_filter": system_type
            }
            
        except Exception as e:
            self.logger.error(f"Error listing identifiers: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    async def delete_identifier(self, identifier: str) -> Dict[str, Any]:
        """
        Delete an identifier from the system.
        
        Args:
            identifier: Either UUID or display_id to delete
            
        Returns:
            Dict with deletion results
        """
        try:
            # First get the identifier info
            info_result = await self.get_identifier_info(identifier)
            if info_result['status'] == 'error' or not info_result.get('found'):
                return {
                    "status": "error",
                    "message": f"Identifier '{identifier}' not found"
                }
            
            project_id = await self._get_project_id()
            if not project_id:
                return {
                    "status": "error",
                    "message": "Could not determine project ID"
                }
            
            # Delete the identifier
            client = self.storage_manager.remote_store.client
            result = client.table('system_identifiers')\
                          .delete()\
                          .eq('project_id', project_id)\
                          .eq('machine_id', self.machine_id)\
                          .eq('entity_uuid', info_result['id'])\
                          .execute()
            
            return {
                "status": "success",
                "message": f"Identifier '{identifier}' deleted",
                "deleted_entity_uuid": info_result['id'],
                "deleted_display_id": info_result['display_id']
            }
            
        except Exception as e:
            self.logger.error(f"Error deleting identifier: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    # Private helper methods
    
    async def _get_project_id(self) -> Optional[str]:
        """Get current project ID from storage manager."""
        try:
            if hasattr(self.storage_manager, 'remote_store') and self.storage_manager.remote_store:
                if hasattr(self.storage_manager.remote_store, 'project_id') and self.storage_manager.remote_store.project_id:
                    return self.storage_manager.remote_store.project_id
                else:
                    # Try to get project_id using the same method as other stores
                    client = self.storage_manager.remote_store.client
                    result = client.rpc('get_or_create_project', {
                        'project_path': str(self.storage_manager.project_path),
                        'project_name': os.path.basename(str(self.storage_manager.project_path))
                    }).execute()
                    
                    if result.data:
                        # Also cache it in the remote store for future use
                        self.storage_manager.remote_store.project_id = result.data
                        return result.data
            return None
        except Exception as e:
            self.logger.error(f"Error getting project ID: {e}")
            return None
    
    async def _generate_auto_display_id(self, project_id: str, system_type: str) -> str:
        """Generate auto display ID based on existing sequence."""
        try:
            prefix = 'DOC' if system_type == 'document' else 'ENT'
            
            # Get highest sequence number for this system type
            client = self.storage_manager.remote_store.client
            result = client.table('system_identifiers')\
                          .select('sequence_number')\
                          .eq('project_id', project_id)\
                          .eq('machine_id', self.machine_id)\
                          .eq('entity_type', system_type)\
                          .order('sequence_number', desc=True)\
                          .limit(1)\
                          .execute()
            
            if result.data:
                next_number = result.data[0]['sequence_number'] + 1
            else:
                next_number = 1
            
            return f"{prefix}-{next_number:03d}"
            
        except Exception as e:
            self.logger.error(f"Error generating auto display ID: {e}")
            prefix = 'DOC' if system_type == 'document' else 'ENT'
            return f"{prefix}-001"
    
    async def _get_next_sequence_number(self, project_id: str, system_type: str) -> int:
        """Get next sequence number for auto-generated IDs."""
        try:
            client = self.storage_manager.remote_store.client
            result = client.table('system_identifiers')\
                          .select('sequence_number')\
                          .eq('project_id', project_id)\
                          .eq('machine_id', self.machine_id)\
                          .eq('entity_type', system_type)\
                          .order('sequence_number', desc=True)\
                          .limit(1)\
                          .execute()
            
            if result.data:
                return result.data[0]['sequence_number'] + 1
            else:
                return 1
                
        except Exception as e:
            self.logger.error(f"Error getting next sequence number: {e}")
            return 1
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the SharedIdentifierManager.
        
        Returns:
            Dict with health information
        """
        status = {
            "manager_initialized": True,
            "machine_id": self.machine_id,
            "storage_manager_available": self.storage_manager is not None
        }
        
        if self.storage_manager:
            status["database_available"] = (
                hasattr(self.storage_manager, 'remote_store') and 
                self.storage_manager.remote_store is not None
            )
        else:
            status["database_available"] = False
        
        return {
            "status": "success",
            "health": status
        }