"""Build configuration loader for Nexus-AI CLI"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class BuildConfigLoader:
    """Loads and manages build configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config loader
        
        Args:
            config_path: Optional path to config file. If not provided, uses default.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default config path
            self.config_path = Path(__file__).parent / "build_config.yaml"
        
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Build config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path
        
        Args:
            key_path: Dot-notation path (e.g., 'registry.default')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_registry_config(self) -> Dict[str, Any]:
        """Get registry configuration"""
        return self.get('registry', {})
    
    def get_default_registry(self) -> str:
        """Get default registry URI"""
        return self.get('registry.default', '533267047935.dkr.ecr.us-west-2.amazonaws.com/nexus-ai')
    
    def get_tagging_config(self) -> Dict[str, Any]:
        """Get tagging configuration"""
        return self.get('tagging', {})
    
    def get_default_tag_format(self) -> str:
        """Get default tag format"""
        return self.get('tagging.default_format', '{project}:{agent}-latest')
    
    def get_tag_pattern(self, pattern_name: str) -> str:
        """Get tag pattern by name
        
        Args:
            pattern_name: Pattern name (e.g., 'version', 'timestamp')
            
        Returns:
            Tag pattern string
        """
        patterns = self.get('tagging.patterns', {})
        return patterns.get(pattern_name, self.get_default_tag_format())
    
    def format_tag(
        self,
        pattern: str,
        project: str,
        agent: str,
        version: Optional[str] = None,
        **kwargs
    ) -> str:
        """Format tag using pattern
        
        Args:
            pattern: Tag pattern with variables
            project: Project name
            agent: Agent name
            version: Optional version
            **kwargs: Additional variables
            
        Returns:
            Formatted tag string
        """
        variables = {
            'project': project,
            'agent': agent,
            'version': version or '1.0.0',
            'timestamp': datetime.now().strftime(self.get('tagging.timestamp_format', '%Y%m%d-%H%M%S')),
            **kwargs
        }
        
        # Try to get git info
        try:
            import subprocess
            git_commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            variables['git_commit'] = git_commit
            
            git_branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            variables['git_branch'] = git_branch
        except:
            variables['git_commit'] = 'unknown'
            variables['git_branch'] = 'unknown'
        
        return pattern.format(**variables)
    
    def get_build_config(self) -> Dict[str, Any]:
        """Get build configuration"""
        return self.get('build', {})
    
    def get_base_image(self) -> str:
        """Get default base image"""
        return self.get('build.base_image', 'public.ecr.aws/docker/library/python:3.12-slim')
    
    def get_default_build_args(self) -> Dict[str, str]:
        """Get default build arguments"""
        return self.get('build.default_args', {})
    
    def get_default_env(self) -> Dict[str, str]:
        """Get default environment variables"""
        return self.get('build.default_env', {})
    
    def get_default_ports(self) -> list:
        """Get default exposed ports"""
        return self.get('build.default_ports', ['8080', '8000'])
    
    def get_dockerfile_pattern(self) -> str:
        """Get Dockerfile location pattern"""
        return self.get('build.dockerfile_pattern', 'deployment/{project}/{agent}/Dockerfile')
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.get('logging', {})
    
    def get_log_directory(self) -> str:
        """Get log directory path"""
        return self.get('logging.directory', 'logs/builds')
    
    def get_log_filename_pattern(self) -> str:
        """Get log filename pattern"""
        return self.get('logging.filename_pattern', '{project}_{agent}_{timestamp}.log')
    
    def format_log_filename(
        self,
        project: str,
        agent: str,
        tag: Optional[str] = None
    ) -> str:
        """Format log filename
        
        Args:
            project: Project name
            agent: Agent name
            tag: Optional tag
            
        Returns:
            Formatted log filename
        """
        pattern = self.get_log_filename_pattern()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return pattern.format(
            project=project,
            agent=agent,
            timestamp=timestamp,
            tag=tag or 'latest'
        )
    
    def get_log_retention_days(self) -> int:
        """Get log retention days"""
        return self.get('logging.retention.days', 30)
    
    def get_ci_config(self) -> Dict[str, Any]:
        """Get CI/CD configuration"""
        return self.get('ci', {})
    
    def is_ci_environment(self) -> bool:
        """Check if running in CI environment"""
        if not self.get('ci.auto_detect', True):
            return False
        
        # Check common CI environment variables
        ci_vars = [
            'CI',
            'CONTINUOUS_INTEGRATION',
            'GITHUB_ACTIONS',
            'GITLAB_CI',
            'JENKINS_HOME',
            'CIRCLECI',
            'TRAVIS',
            'BUILDKITE'
        ]
        
        return any(os.getenv(var) for var in ci_vars)
    
    def get_ci_environment_name(self) -> Optional[str]:
        """Get CI environment name"""
        if os.getenv('GITHUB_ACTIONS'):
            return 'github_actions'
        elif os.getenv('GITLAB_CI'):
            return 'gitlab_ci'
        elif os.getenv('JENKINS_HOME'):
            return 'jenkins'
        elif os.getenv('CIRCLECI'):
            return 'circleci'
        return None
    
    def get_ci_tag_format(self) -> Optional[str]:
        """Get CI-specific tag format"""
        env_name = self.get_ci_environment_name()
        if env_name:
            return self.get(f'ci.environments.{env_name}.tag_format')
        return None
    
    def should_auto_push_in_ci(self) -> bool:
        """Check if should auto-push in CI"""
        if not self.is_ci_environment():
            return False
        
        if not self.get('ci.auto_push.enabled', False):
            return False
        
        # Check branch
        allowed_branches = self.get('ci.auto_push.branches', [])
        if allowed_branches:
            try:
                import subprocess
                current_branch = subprocess.check_output(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                
                if current_branch not in allowed_branches:
                    return False
            except:
                return False
        
        return True
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration"""
        return self.get('validation', {})
    
    def should_validate_docker(self) -> bool:
        """Check if should validate Docker availability"""
        return self.get('validation.check_docker', True)
    
    def get_dockerfile_auto_generate(self) -> bool:
        """Check if should auto-generate Dockerfile"""
        return self.get('dockerfile.auto_generate.enabled', True)
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self.get('performance', {})
    
    def is_parallel_builds_enabled(self) -> bool:
        """Check if parallel builds are enabled"""
        return self.get('performance.parallel.enabled', False)
    
    def get_max_parallel_workers(self) -> int:
        """Get maximum parallel workers"""
        return self.get('performance.parallel.max_workers', 4)
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        return self._config.copy()


# Global config instance
_global_config = None


def get_build_config(config_path: Optional[str] = None) -> BuildConfigLoader:
    """Get global build configuration instance
    
    Args:
        config_path: Optional custom config path
        
    Returns:
        BuildConfigLoader instance
    """
    global _global_config
    
    if _global_config is None or config_path:
        _global_config = BuildConfigLoader(config_path)
    
    return _global_config


def reload_build_config():
    """Reload global build configuration"""
    global _global_config
    if _global_config:
        _global_config.reload()
