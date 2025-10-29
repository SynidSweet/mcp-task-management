"""Project management functionality - simple file operations only"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ProjectManager:
    """Manages project directory and data file paths"""

    def __init__(self, project_path: Optional[Path] = None):
        if project_path:
            self.project_path = project_path.resolve()
        else:
            self.project_path = None

        self.data_dir = self.project_path / '.claude-tasks' / 'data' if self.project_path else None
        self.template_dir = self.project_path / '.claude-tasks' / 'templates' if self.project_path else None
        self.specs_dir = self.project_path / '.claude-specs' if self.project_path else None
        self.specs_data_dir = self.project_path / '.claude-specs' / 'data' if self.project_path else None

        if self.project_path:
            self._ensure_project_structure()
    
    def _ensure_project_structure(self):
        """Create .claude-tasks and .claude-specs structure"""
        if not self.data_dir:
            return
            
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create templates directory
        if self.template_dir:
            self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize JSON files if they don't exist
        for filename in ["tasks.json", "sprints.json", "journal.json", "documents.json"]:
            file_path = self.data_dir / filename
            if not file_path.exists():
                initial_data = {
                    filename.replace('.json', ''): [],
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0"
                    }
                }
                with open(file_path, 'w') as f:
                    json.dump(initial_data, f, indent=2)
        
        # Create .claude-specs directory structure
        if self.specs_data_dir:
            self.specs_data_dir.mkdir(parents=True, exist_ok=True)
            (self.specs_data_dir / 'specifications').mkdir(exist_ok=True)
            (self.specs_data_dir / 'proposals').mkdir(exist_ok=True)
            (self.specs_data_dir / 'resources').mkdir(exist_ok=True)
    
    def get_data_file(self, data_type: str) -> Path:
        """Get path to data file"""
        if not self.data_dir:
            raise ValueError("No project directory set")
        return self.data_dir / f'{data_type}.json'
    
    def get_spec_file(self, spec_type: str) -> Path:
        """Get path to specification file"""
        if not self.specs_data_dir:
            raise ValueError("No project directory set")
        
        # Handle cases where spec_type already includes .json extension
        if spec_type.endswith('.json'):
            return self.specs_data_dir / 'specifications' / spec_type
        else:
            return self.specs_data_dir / 'specifications' / f'{spec_type}.json'
    
    def get_template_file(self, template_type: str) -> Path:
        """Get path to template file"""
        if not self.template_dir:
            raise ValueError("No project directory set")

        # Handle cases where template_type already includes .json extension
        if template_type.endswith('.json'):
            return self.template_dir / template_type
        else:
            return self.template_dir / f'{template_type}.json'

    def get_project_id_file(self) -> Path:
        """Get path to project_id file.

        This file contains the folder name that uniquely identifies this project
        across all machines. It should be committed to version control.

        Returns:
            Path to .claude-tasks/data/project_id
        """
        if not self.data_dir:
            raise ValueError("No project directory set")
        return self.data_dir / 'project_id'

    def read_project_id(self) -> Optional[str]:
        """Read project_id from file.

        Returns:
            Folder name string if file exists, None otherwise
        """
        id_file = self.get_project_id_file()
        if id_file.exists():
            return id_file.read_text().strip()
        return None

    def write_project_id(self, project_id: str) -> None:
        """Write project_id to file.

        Args:
            project_id: Folder name string to write
        """
        id_file = self.get_project_id_file()
        # Ensure data directory exists
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(project_id + '\n')

    def get_or_generate_project_id(self) -> str:
        """Get project_id from file, or generate and save new one.

        This is the primary method for getting the project's unique identifier.
        If the file doesn't exist, generates project_id from folder name and saves it.

        Returns:
            Folder name string identifying this project
        """
        project_id = self.read_project_id()
        if not project_id:
            # Use folder name as project_id instead of UUID
            project_id = self.project_path.name
            self.write_project_id(project_id)
        return project_id

    def set_project_directory(self, project_dir: str) -> Dict[str, Any]:
        """Set project directory"""
        project_path = Path(project_dir).resolve()

        if not project_path.exists():
            return {"status": "error", "message": f"Directory does not exist: {project_dir}"}

        self.project_path = project_path
        self.data_dir = self.project_path / '.claude-tasks' / 'data'
        self.template_dir = self.project_path / '.claude-tasks' / 'templates'
        self.specs_dir = self.project_path / '.claude-specs'
        self.specs_data_dir = self.project_path / '.claude-specs' / 'data'
        self._ensure_project_structure()

        return {
            "status": "success",
            "project_path": str(self.project_path),
            "data_dir": str(self.data_dir)
        }
    
    def is_initialized(self) -> bool:
        """Check if project is initialized"""
        return self.project_path is not None
    
    def get_initialization_error(self) -> Dict[str, Any]:
        """Get clear error message for uninitialized state"""
        return {
            "error": "No project directory set", 
            "solution": "Add --project-dir to your MCP config or use system_set_project_directory",
            "example": 'claude mcp add claude-tasks python server.py --project-dir "$(pwd)"'
        }
    
    async def get_storage_data(self, entity_type: str) -> Optional[Dict[str, Any]]:
        """Get data from local file."""
        try:
            file_path = self.get_data_file(entity_type)
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception:
            return None

    async def save_storage_data(self, entity_type: str, data: Dict[str, Any]) -> bool:
        """Save data to local file."""
        try:
            file_path = self.get_data_file(entity_type)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    async def get_template_data(self, template_type: str) -> Optional[Dict[str, Any]]:
        """Get template data from local file."""
        try:
            file_path = self.get_template_file(template_type)
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception:
            return None

    async def save_template_data(self, template_type: str, data: Dict[str, Any], scope: str = "project") -> bool:
        """Save template data to local file."""
        try:
            file_path = self.get_template_file(template_type)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False