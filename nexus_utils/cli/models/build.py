"""Build models for Docker image building"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class BuildOptions:
    """Options for building Docker images"""
    agent: Optional[str] = None
    tag: Optional[str] = None
    no_cache: bool = False
    push: Optional[str] = None  # Custom registry URI, or True for default
    platform: Optional[str] = None
    build_args: Dict[str, str] = field(default_factory=dict)
    create_ecr_repo: bool = True  # Auto-create ECR repository if not exists


@dataclass
class BuildConfig:
    """Build configuration for a project"""
    enabled: bool = True
    base_image: str = "public.ecr.aws/docker/library/python:3.12-slim"
    registry: str = "533267047935.dkr.ecr.us-west-2.amazonaws.com/nexus-ai"
    build_args: Dict[str, str] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    agents: List[Dict[str, Any]] = field(default_factory=list)
    logs: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'directory': 'logs/builds',
        'retention_days': 30
    })
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuildConfig':
        """Create BuildConfig from dictionary"""
        return cls(
            enabled=data.get('enabled', True),
            base_image=data.get('base_image', 'public.ecr.aws/docker/library/python:3.12-slim'),
            registry=data.get('registry', '533267047935.dkr.ecr.us-west-2.amazonaws.com/nexus-ai'),
            build_args=data.get('build_args', {}),
            env=data.get('env', {}),
            agents=data.get('agents', []),
            logs=data.get('logs', {
                'enabled': True,
                'directory': 'logs/builds',
                'retention_days': 30
            })
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert BuildConfig to dictionary"""
        return {
            'enabled': self.enabled,
            'base_image': self.base_image,
            'registry': self.registry,
            'build_args': self.build_args,
            'env': self.env,
            'agents': self.agents,
            'logs': self.logs
        }


@dataclass
class BuildResult:
    """Result of a Docker build operation"""
    success: bool
    project_name: str
    agent_name: str
    image_tag: Optional[str] = None
    image_id: Optional[str] = None
    size: Optional[int] = None
    duration: float = 0.0
    logs: str = ""
    log_file: Optional[Path] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def format_size(self) -> str:
        """Format size in human-readable format"""
        if not self.size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.size < 1024.0:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.1f} PB"


@dataclass
class DockerfileTemplate:
    """Template for generating Dockerfiles"""
    base_image: str
    project_name: str
    agent_name: str
    env_vars: Dict[str, str]
    ports: List[str]
    build_args: Dict[str, str] = field(default_factory=dict)
    
    def generate(self) -> str:
        """Generate Dockerfile content from template"""
        # Format environment variables
        env_lines = []
        for key, value in self.env_vars.items():
            env_lines.append(f'ENV {key}="{value}"')
        env_section = '\n'.join(env_lines) if env_lines else ''
        
        # Format ports
        port_lines = []
        for port in self.ports:
            port_lines.append(f'EXPOSE {port}')
        ports_section = '\n'.join(port_lines) if port_lines else ''
        
        # Generate Dockerfile
        dockerfile = f"""FROM {self.base_image}
WORKDIR /app

ENV PYTHONPATH="/app:/app/nexus_utils:$PYTHONPATH"

# Copy requirements and dependencies
COPY projects/{self.project_name}/requirements.txt projects/{self.project_name}/requirements.txt
COPY nexus_utils nexus_utils

# Install dependencies
RUN pip install -r projects/{self.project_name}/requirements.txt
RUN pip install aws-opentelemetry-distro>=0.10.1

# Environment configuration
{env_section}

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

# Expose ports
{ports_section}

# Copy entire project
COPY . .

# Run agent
CMD ["opentelemetry-instrument", "python", "-m", "agents.generated_agents.{self.project_name}.{self.agent_name}"]
"""
        return dockerfile.strip()


@dataclass
class AgentBuildInfo:
    """Information about an agent to build"""
    name: str
    dockerfile_path: Path
    context_path: Path
    image_tag: str
    ports: List[str] = field(default_factory=lambda: ["8080", "8000"])
    
    def dockerfile_exists(self) -> bool:
        """Check if Dockerfile exists"""
        return self.dockerfile_path.exists()
