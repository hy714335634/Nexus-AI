"""Agent manager - handles agent lifecycle"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from .base import ResourceManager
from ..models.agent import Agent, AgentConfig


class AgentManager(ResourceManager):
    """Manages Nexus-AI agents"""
    
    MANAGED_PATH = "agents/generated_agents"
    EXCLUDED_PATHS = ["agents/system_agents", "agents/template_agents"]
    
    def list_agents(self, project: Optional[str] = None) -> List[Agent]:
        """List all agents or agents for a specific project"""
        agents = []
        
        if not self.fs.exists(self.MANAGED_PATH):
            return agents
        
        # List all agent directories
        for agent_path in self.fs.list_directory(self.MANAGED_PATH):
            if agent_path.is_dir():
                agent_name = agent_path.name
                
                # If project filter is specified, check if agent belongs to project
                if project:
                    project_agent_dir = f"projects/{project}/agents/{agent_name}"
                    if not self.fs.exists(project_agent_dir):
                        continue
                
                try:
                    agent = self.get_agent(agent_name)
                    if agent:
                        agents.append(agent)
                except Exception:
                    continue
        
        return sorted(agents, key=lambda a: a.name)
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a specific agent"""
        agent_path = f"{self.MANAGED_PATH}/{name}"
        
        if not self.fs.exists(agent_path):
            return None
        
        # Load agent configuration from prompt file
        agent_config_data = self.config.load_agent_config(agent_path)
        
        agent_config = None
        tools_dependencies = []
        
        if agent_config_data:
            # Extract tools_dependencies from metadata or versions
            metadata = agent_config_data.get('metadata', {})
            if isinstance(metadata, dict):
                tools_dependencies = metadata.get('tools_dependencies', [])
            
            # Also check versions for tools_dependencies
            versions = agent_config_data.get('versions', [])
            if isinstance(versions, list) and len(versions) > 0:
                # Get the latest version
                latest_version = versions[0]
                if isinstance(latest_version, dict):
                    version_metadata = latest_version.get('metadata', {})
                    if isinstance(version_metadata, dict):
                        version_tools = version_metadata.get('tools_dependencies', [])
                        if isinstance(version_tools, list):
                            tools_dependencies = version_tools
            
            agent_config = AgentConfig(
                name=agent_config_data.get('name', name),
                description=agent_config_data.get('description', ''),
                category=agent_config_data.get('category', ''),
                version=agent_config_data.get('version', '1.0.0'),
                tools_dependencies=tools_dependencies if isinstance(tools_dependencies, list) else [],
                supported_models=agent_config_data.get('supported_models', []),
                system_prompt=agent_config_data.get('system_prompt', '')
            )
        
        # Try to determine which project this agent belongs to
        project_name = None
        projects_dir = "projects"
        if self.fs.exists(projects_dir):
            for project_path in self.fs.list_directory(projects_dir):
                if project_path.is_dir():
                    proj_name = project_path.name
                    if self.fs.exists(f"projects/{proj_name}/agents/{name}"):
                        project_name = proj_name
                        break
        
        # Get timestamps
        try:
            agent_file = f"{agent_path}/{name}.py"
            if self.fs.exists(agent_file):
                created_at = datetime.fromtimestamp(self.fs.get_modification_time(agent_file))
                updated_at = created_at
            else:
                created_at = datetime.now()
                updated_at = created_at
        except:
            created_at = datetime.now()
            updated_at = created_at
        
        return Agent(
            name=name,
            path=Path(agent_path),
            project=project_name,
            config=agent_config,
            dependencies=agent_config.tools_dependencies if agent_config else [],
            created_at=created_at,
            updated_at=updated_at
        )
