"""Configuration loader"""

from pathlib import Path
from typing import Dict, Any, Optional
from .filesystem import FileSystemAdapter
from ..models.project import ProjectConfig, ProjectStatus


class ConfigLoader:
    """Loads and validates configurations"""
    
    def __init__(self, fs_adapter: FileSystemAdapter):
        """Initialize with file system adapter"""
        self.fs = fs_adapter
    
    def load_project_config(self, project_name: str) -> ProjectConfig:
        """Load project configuration"""
        config_path = f"projects/{project_name}/config.yaml"
        
        try:
            data = self.fs.read_yaml(config_path)
            # Check if data has 'project' key (nested structure)
            if 'project' in data:
                project_data = data['project']
            else:
                project_data = data
            
            return ProjectConfig(
                name=project_data.get('name', project_name),
                description=project_data.get('description', ''),
                version=project_data.get('version', '1.0.0'),
                dependencies=project_data.get('dependencies', []),
                metadata=project_data.get('metadata', {})
            )
        except FileNotFoundError:
            # Try JSON format
            config_path = f"projects/{project_name}/project_config.json"
            try:
                data = self.fs.read_json(config_path)
                # Check if data has 'project' key (nested structure)
                if 'project' in data:
                    project_data = data['project']
                else:
                    project_data = data
                
                return ProjectConfig(
                    name=project_data.get('name', project_name),
                    description=project_data.get('description', ''),
                    version=project_data.get('version', '1.0.0'),
                    dependencies=project_data.get('dependencies', []),
                    metadata=project_data.get('metadata', {})
                )
            except FileNotFoundError:
                # Return default config
                return ProjectConfig(name=project_name)
    
    def load_project_status(self, project_name: str) -> ProjectStatus:
        """Load project status"""
        status_path = f"projects/{project_name}/status.yaml"
        
        try:
            data = self.fs.read_yaml(status_path)
            return ProjectStatus(
                overall_status=data.get('status', 'pending'),
                stages=data.get('stages', {}),
                progress=data.get('progress', 0.0)
            )
        except FileNotFoundError:
            return ProjectStatus(overall_status='pending')
    
    def save_project_config(self, project_name: str, config: ProjectConfig) -> bool:
        """Save project configuration"""
        config_path = f"projects/{project_name}/config.yaml"
        return self.fs.write_yaml(config_path, config.to_dict())
    
    def save_project_status(self, project_name: str, status: ProjectStatus) -> bool:
        """Save project status"""
        status_path = f"projects/{project_name}/status.yaml"
        return self.fs.write_yaml(status_path, status.to_dict())
    
    def load_agent_config(self, agent_path: str) -> Dict[str, Any]:
        """Load agent configuration from prompt file"""
        # Extract agent name from path
        # agent_path format: "agents/generated_agents/agent_name"
        agent_name = agent_path.split('/')[-1]
        
        # Construct prompt file path
        prompt_file = f"prompts/generated_agents_prompts/{agent_name}/{agent_name}.yaml"
        
        try:
            data = self.fs.read_yaml(prompt_file)
            return data.get('agent', {})
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
    
    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate configuration against schema"""
        # Basic validation - check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in config:
                return False
        return True
