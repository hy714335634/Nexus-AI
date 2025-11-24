"""Project manager - handles project lifecycle"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base import ResourceManager
from ..models.project import Project, ProjectConfig, ProjectStatus
from ..models.common import Dependency, DirectoryTree


class ProjectManager(ResourceManager):
    """Manages Nexus-AI projects"""
    
    def list_projects(self) -> List[Project]:
        """List all projects"""
        projects = []
        projects_dir = "projects"
        
        if not self.fs.exists(projects_dir):
            return projects
        
        # List all directories in projects/
        for project_path in self.fs.list_directory(projects_dir):
            if project_path.is_dir():
                project_name = project_path.name
                try:
                    project = self.get_project(project_name)
                    if project:
                        projects.append(project)
                except Exception:
                    # Skip projects that can't be loaded
                    continue
        
        return sorted(projects, key=lambda p: p.created_at, reverse=True)
    
    def get_project(self, name: str) -> Optional[Project]:
        """Get a specific project"""
        project_path = f"projects/{name}"
        
        if not self.fs.exists(project_path):
            return None
        
        # Load configuration
        config = self.config.load_project_config(name)
        status = self.config.load_project_status(name)
        
        # Get timestamps
        config_file = f"{project_path}/config.yaml"
        if not self.fs.exists(config_file):
            config_file = f"{project_path}/project_config.json"
        
        try:
            created_at = datetime.fromtimestamp(self.fs.get_modification_time(config_file))
        except:
            created_at = datetime.now()
        
        try:
            status_file = f"{project_path}/status.yaml"
            updated_at = datetime.fromtimestamp(self.fs.get_modification_time(status_file))
        except:
            updated_at = created_at
        
        # Get resource lists
        agents = self.get_project_agents(name)
        templates = self.get_project_templates(name)
        prompts = self.get_project_prompts(name)
        tools = self.get_project_tools(name)
        
        return Project(
            name=name,
            path=Path(project_path),
            config=config,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            agents=agents,
            templates=templates,
            prompts=prompts,
            tools=tools
        )
    
    def get_project_agents(self, name: str) -> List[str]:
        """Get list of agents for a project"""
        agents = []
        
        # Check if project has an agent directory in generated_agents
        project_agent_dir = f"agents/generated_agents/{name}"
        if self.fs.exists(project_agent_dir) and self.fs.is_directory(project_agent_dir):
            # List Python files in the agent directory
            for agent_file in self.fs.list_directory(project_agent_dir, "*.py"):
                if agent_file.name != "__init__.py":
                    # Agent name is the file stem
                    agents.append(agent_file.stem)
        
        return agents
    
    def get_project_templates(self, name: str) -> List[str]:
        """Get list of templates for a project"""
        templates = []
        prompts_dir = f"prompts/generated_agents_prompts/{name}"
        
        if not self.fs.exists(prompts_dir):
            return templates
        
        # List YAML files in the prompts directory
        for template_file in self.fs.list_directory(prompts_dir, "*.yaml"):
            templates.append(template_file.stem)
        
        return templates
    
    def get_project_prompts(self, name: str) -> List[str]:
        """Get list of prompts for a project"""
        # For now, same as templates
        return self.get_project_templates(name)
    
    def get_project_tools(self, name: str) -> List[str]:
        """Get list of tools for a project by parsing tools_dependencies from prompt files"""
        tools = set()  # Use set to avoid duplicates
        
        # Get all agents for this project
        agents = self.get_project_agents(name)
        
        # For each agent, get its tools_dependencies from the prompt file
        for agent_name in agents:
            # The prompt file path is based on project name and agent name
            prompt_path = f"prompts/generated_agents_prompts/{name}/{agent_name}.yaml"
            
            if self.fs.exists(prompt_path):
                try:
                    prompt_data = self.fs.read_yaml(prompt_path)
                    agent_config = prompt_data.get('agent', {})
                    
                    # Check versions for tools_dependencies (preferred location)
                    versions = agent_config.get('versions', [])
                    if isinstance(versions, list):
                        for version in versions:
                            if isinstance(version, dict):
                                version_metadata = version.get('metadata', {})
                                if isinstance(version_metadata, dict):
                                    tools_deps = version_metadata.get('tools_dependencies', [])
                                    if isinstance(tools_deps, list):
                                        tools.update(tools_deps)
                    
                    # Also check top-level metadata as fallback
                    metadata = agent_config.get('metadata', {})
                    if isinstance(metadata, dict):
                        tools_deps = metadata.get('tools_dependencies', [])
                        if isinstance(tools_deps, list):
                            tools.update(tools_deps)
                except Exception:
                    # Skip if can't read prompt file
                    pass
        
        return sorted(list(tools))
    
    def get_project_tree(self, name: str) -> DirectoryTree:
        """Get directory tree for a project"""
        project_path = f"projects/{name}"
        return self.fs.get_directory_tree(project_path)
    
    def get_project_dependencies(self, name: str) -> List[Dependency]:
        """Get dependencies for a project"""
        dependencies = []
        
        # Get agents and their dependencies
        agents = self.get_project_agents(name)
        for agent_name in agents:
            agent_path = f"agents/generated_agents/{agent_name}"
            agent_config = self.config.load_agent_config(agent_path)
            
            # Add tool dependencies
            for tool_dep in agent_config.get('tools_dependencies', []):
                dependencies.append(Dependency(
                    name=tool_dep,
                    type='tool',
                    available=True  # Simplified check
                ))
        
        # Get package dependencies from requirements.txt
        req_file = f"projects/{name}/requirements.txt"
        if self.fs.exists(req_file):
            try:
                content = self.fs.read_file(req_file)
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        dependencies.append(Dependency(
                            name=line,
                            type='package',
                            available=True  # Simplified check
                        ))
            except:
                pass
        
        return dependencies
    
    def get_project_resource_counts(self, name: str) -> Dict[str, int]:
        """Get resource counts for a project"""
        return {
            'agents': len(self.get_project_agents(name)),
            'templates': len(self.get_project_templates(name)),
            'prompts': len(self.get_project_prompts(name)),
            'tools': len(self.get_project_tools(name))
        }
    
    def create_project(self, name: str, config: Optional[ProjectConfig] = None) -> Project:
        """Create a new project"""
        project_path = f"projects/{name}"
        
        if self.fs.exists(project_path):
            raise ValueError(f"Project '{name}' already exists")
        
        # Create project directory
        self.fs.create_directory(project_path)
        self.fs.create_directory(f"{project_path}/agents")
        
        # Create default config if not provided
        if config is None:
            config = ProjectConfig(name=name)
        
        # Save configuration
        self.config.save_project_config(name, config)
        
        # Create initial status
        status = ProjectStatus(overall_status='pending')
        self.config.save_project_status(name, status)
        
        # Create README
        readme_content = f"# {name}\n\n{config.description}\n"
        self.fs.write_file(f"{project_path}/README.md", readme_content)
        
        return self.get_project(name)
    
    def update_project(self, name: str, config: ProjectConfig) -> Optional[Project]:
        """Update project configuration"""
        if not self.fs.exists(f"projects/{name}"):
            return None
        
        self.config.save_project_config(name, config)
        return self.get_project(name)
    
    def delete_project(self, name: str) -> bool:
        """Delete a project and all its related resources"""
        project_path = f"projects/{name}"
        
        if not self.fs.exists(project_path):
            return False
        
        # Get all related resources before deletion
        agents = self.get_project_agents(name)
        
        # 1. Delete generated agents
        agent_dir = f"agents/generated_agents/{name}"
        if self.fs.exists(agent_dir):
            self.fs.delete_directory(agent_dir)
        
        # 2. Delete prompts
        prompts_dir = f"prompts/generated_agents_prompts/{name}"
        if self.fs.exists(prompts_dir):
            self.fs.delete_directory(prompts_dir)
        
        # 3. Delete tools
        tools_dir = f"tools/generated_tools/{name}"
        if self.fs.exists(tools_dir):
            self.fs.delete_directory(tools_dir)
        
        # 4. Delete project directory
        self.fs.delete_directory(project_path)
        
        return True
