"""Build manager - handles Docker image building"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
import click

from .base import ResourceManager
from ..models.build import (
    BuildOptions, BuildConfig, BuildResult, 
    DockerfileTemplate, AgentBuildInfo
)
from ..adapters.docker_adapter import DockerAdapter
from ..adapters.ecr_adapter import ECRAdapter
from ..config import get_build_config


class BuildManager(ResourceManager):
    """Manages Docker image building for Nexus-AI projects"""
    
    def __init__(self, fs, config):
        super().__init__(fs, config)
        self.docker = DockerAdapter()
        self.ecr = ECRAdapter()
        self.build_config = get_build_config()
    
    def validate_build_environment(self) -> tuple[bool, str]:
        """Validate that Docker is available
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.docker.is_docker_available():
            return False, (
                "Docker is not installed or not running.\n"
                "Please install Docker and ensure the Docker daemon is running.\n"
                "Visit https://docs.docker.com/get-docker/ for installation instructions."
            )
        return True, ""
    
    def build_project(
        self,
        project_name: str,
        options: BuildOptions
    ) -> List[BuildResult]:
        """Build all agents in a project
        
        Args:
            project_name: Name of the project to build
            options: Build options
            
        Returns:
            List of BuildResult for each agent
        """
        # Validate environment
        is_valid, error_msg = self.validate_build_environment()
        if not is_valid:
            raise RuntimeError(error_msg)
        
        # Validate project exists
        project_path = f"projects/{project_name}"
        if not self.fs.exists(project_path):
            raise ValueError(
                f"Project '{project_name}' not found.\n"
                f"Run 'nexus-cli project list' to see available projects."
            )
        
        # Get project configuration
        project_config = self.config.load_project_config(project_name)
        
        # Load build configuration
        build_config = self._load_build_config(project_name)
        
        # Get agents to build
        if options.agent:
            # Build specific agent
            agents = [options.agent]
        else:
            # Build all agents in project
            agents = self._get_project_agents(project_name)
        
        if not agents:
            raise ValueError(
                f"No agents found in project '{project_name}'.\n"
                f"Project may not have any agents to build."
            )
        
        # Display build header
        click.echo(f"\nBuilding project: {project_name}")
        click.echo("━" * 50)
        
        # Build each agent
        results = []
        for agent_name in agents:
            try:
                result = self.build_agent(project_name, agent_name, options, build_config)
                results.append(result)
                
                # Stop on first failure (fail-fast)
                if not result.success:
                    click.echo(f"\n✗ Build failed for agent: {agent_name}", err=True)
                    click.echo(f"Error: {result.error}", err=True)
                    if result.log_file:
                        click.echo(f"See log file: {result.log_file}", err=True)
                    break
                
            except Exception as e:
                click.echo(f"\n✗ Build failed for agent: {agent_name}", err=True)
                click.echo(f"Error: {e}", err=True)
                # Create failed result
                result = BuildResult(
                    success=False,
                    project_name=project_name,
                    agent_name=agent_name,
                    error=str(e)
                )
                results.append(result)
                break  # Fail-fast
        
        return results
    
    def build_agent(
        self,
        project_name: str,
        agent_name: str,
        options: BuildOptions,
        build_config: Optional[BuildConfig] = None
    ) -> BuildResult:
        """Build a specific agent
        
        Args:
            project_name: Name of the project
            agent_name: Name of the agent to build
            options: Build options
            build_config: Optional build configuration (loaded if not provided)
            
        Returns:
            BuildResult with build information
        """
        # Load build config if not provided
        if build_config is None:
            build_config = self._load_build_config(project_name)
        
        # Get agent build info
        agent_info = self._get_agent_build_info(
            project_name, 
            agent_name, 
            build_config,
            options
        )
        
        # Ensure Dockerfile exists
        if not agent_info.dockerfile_exists():
            click.echo(f"\nWarning: Dockerfile not found at {agent_info.dockerfile_path}")
            click.echo("Generating Dockerfile from template...")
            self._generate_dockerfile(project_name, agent_name, build_config, agent_info)
        
        # Display build info
        click.echo(f"\nAgent: {agent_name}")
        click.echo(f"Dockerfile: {agent_info.dockerfile_path}")
        click.echo(f"Context: {agent_info.context_path}")
        click.echo(f"Image: {agent_info.image_tag}")
        
        # Prepare log file
        log_file = None
        if build_config.logs.get('enabled', True):
            log_dir = Path(build_config.logs.get('directory', 'logs/builds'))
            log_filename = self.build_config.format_log_filename(
                project=project_name,
                agent=agent_name,
                tag=options.tag
            )
            log_file = self.fs.base_path / log_dir / log_filename
            click.echo(f"Log file: {log_file}")
        
        click.echo()  # Empty line before build output
        
        # Build image
        result = self.docker.build_image(
            project_name=project_name,
            agent_name=agent_name,
            dockerfile_path=str(agent_info.dockerfile_path),
            context_path=str(agent_info.context_path),
            tag=agent_info.image_tag,
            log_file=log_file,
            build_args=options.build_args or build_config.build_args,
            no_cache=options.no_cache,
            platform=options.platform
        )
        
        # Display result
        if result.success:
            click.echo(f"\n✓ Build successful!")
            click.echo(f"\nImage: {result.image_tag}")
            click.echo(f"Image ID: {result.image_id}")
            click.echo(f"Size: {result.format_size()}")
            click.echo(f"Duration: {result.duration:.1f}s")
            if result.log_file:
                click.echo(f"Build log saved to: {result.log_file}")
            
            # Push if requested
            if options.push:
                self._push_image(result.image_tag, options.push, build_config, options.create_ecr_repo)
        
        return result
    
    def list_buildable_agents(self, project_name: str) -> List[str]:
        """List agents that can be built for a project
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of agent names
        """
        return self._get_project_agents(project_name)
    
    def _load_build_config(self, project_name: str) -> BuildConfig:
        """Load build configuration for a project
        
        Args:
            project_name: Name of the project
            
        Returns:
            BuildConfig object
        """
        # Start with global defaults from centralized config
        default_config = BuildConfig(
            base_image=self.build_config.get_base_image(),
            registry=self.build_config.get_default_registry(),
            build_args=self.build_config.get_default_build_args(),
            env=self.build_config.get_default_env(),
            logs={
                'enabled': self.build_config.get('logging.enabled', True),
                'directory': self.build_config.get_log_directory(),
                'retention_days': self.build_config.get_log_retention_days()
            }
        )
        
        # Try to load project-specific overrides
        config_path = f"projects/{project_name}/config.yaml"
        
        if self.fs.exists(config_path):
            try:
                data = self.fs.read_yaml(config_path)
                project_data = data.get('project', {})
                build_data = project_data.get('build', {})
                
                if build_data:
                    # Merge project config with defaults
                    merged_config = default_config.to_dict()
                    merged_config.update(build_data)
                    return BuildConfig.from_dict(merged_config)
            except Exception:
                pass
        
        # Return default config from centralized configuration
        return default_config
    
    def _get_project_agents(self, project_name: str) -> List[str]:
        """Get list of agents for a project
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of agent names
        """
        agents = []
        
        # Check agents directory
        agents_dir = f"agents/generated_agents/{project_name}"
        if self.fs.exists(agents_dir) and self.fs.is_directory(agents_dir):
            for agent_file in self.fs.list_directory(agents_dir, "*.py"):
                if agent_file.name != "__init__.py":
                    agents.append(agent_file.stem)
        
        return agents
    
    def _get_agent_build_info(
        self,
        project_name: str,
        agent_name: str,
        build_config: BuildConfig,
        options: BuildOptions
    ) -> AgentBuildInfo:
        """Get build information for an agent
        
        Args:
            project_name: Name of the project
            agent_name: Name of the agent
            build_config: Build configuration
            options: Build options
            
        Returns:
            AgentBuildInfo object
        """
        # Determine Dockerfile path
        dockerfile_path = self.fs.base_path / "deployment" / project_name / agent_name / "Dockerfile"
        
        # Context is the repository root
        context_path = self.fs.base_path
        
        # Determine image tag
        if options.tag:
            # Custom tag provided
            tag_pattern = f"{{project}}:{{agent}}-{options.tag}"
        else:
            # Use default tag format from config
            tag_pattern = self.build_config.get_default_tag_format()
        
        # Format the tag
        formatted_tag = self.build_config.format_tag(
            tag_pattern,
            project=project_name,
            agent=agent_name
        )
        
        # Add registry prefix
        image_tag = f"{build_config.registry}/{formatted_tag}"
        
        # Get ports from config
        ports = ["8080", "8000"]  # Default ports
        for agent_config in build_config.agents:
            if agent_config.get('name') == agent_name:
                ports = agent_config.get('ports', ports)
                break
        
        return AgentBuildInfo(
            name=agent_name,
            dockerfile_path=dockerfile_path,
            context_path=context_path,
            image_tag=image_tag,
            ports=ports
        )
    
    def _generate_dockerfile(
        self,
        project_name: str,
        agent_name: str,
        build_config: BuildConfig,
        agent_info: AgentBuildInfo
    ):
        """Generate Dockerfile from template
        
        Args:
            project_name: Name of the project
            agent_name: Name of the agent
            build_config: Build configuration
            agent_info: Agent build information
        """
        # Create template
        template = DockerfileTemplate(
            base_image=build_config.base_image,
            project_name=project_name,
            agent_name=agent_name,
            env_vars=build_config.env,
            ports=agent_info.ports,
            build_args=build_config.build_args
        )
        
        # Generate Dockerfile content
        dockerfile_content = template.generate()
        
        # Ensure directory exists
        agent_info.dockerfile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write Dockerfile
        with open(agent_info.dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        click.echo(f"✓ Generated Dockerfile at {agent_info.dockerfile_path}")
    
    def _push_image(
        self,
        image_tag: str,
        push_option: str,
        build_config: BuildConfig,
        create_ecr_repo: bool = True
    ):
        """Push image to registry
        
        Args:
            image_tag: Image tag to push
            push_option: Push option (True for default, or custom URI)
            build_config: Build configuration
            create_ecr_repo: Whether to auto-create ECR repository
        """
        # Determine target tag
        if isinstance(push_option, str) and push_option.lower() not in ['true', '1', 'yes', 'default']:
            # Custom registry URI provided
            # Extract image name from current tag
            image_name = image_tag.split('/')[-1]
            target_tag = f"{push_option}/{image_name}"
            
            # Tag image with new registry
            click.echo(f"\nTagging image for custom registry: {target_tag}")
            if not self.docker.tag_image(image_tag, target_tag):
                click.echo("✗ Failed to tag image", err=True)
                return
            
            push_tag = target_tag
        else:
            # Use default registry (already in image tag)
            push_tag = image_tag
        
        # Check and create ECR repository if needed
        if create_ecr_repo:
            click.echo(f"\nChecking ECR repository...")
            success, message = self.ecr.ensure_repository_exists(
                image_uri=push_tag,
                auto_create=True,
                image_scanning=True,
                encryption_type="AES256",
                set_lifecycle_policy=True,
                max_image_count=100,
                tags={
                    'ManagedBy': 'nexus-cli',
                    'CreatedBy': 'auto-build'
                }
            )
            
            if success:
                if "created successfully" in message:
                    click.echo(f"✓ {message}")
                elif "already exists" in message:
                    click.echo(f"✓ {message}")
                else:
                    click.echo(f"  {message}")
            else:
                click.echo(f"⚠ Warning: {message}", err=True)
                click.echo("  Continuing with push attempt...", err=True)
        
        # Push image
        success, message = self.docker.push_image(push_tag)
        
        if success:
            click.echo(f"✓ Successfully pushed image: {push_tag}")
        else:
            click.echo(f"✗ Failed to push image", err=True)
            click.echo(f"Error: {message}", err=True)
