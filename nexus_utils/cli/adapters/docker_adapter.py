"""Docker adapter for Docker CLI operations"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from ..models.build import BuildResult


class DockerAdapter:
    """Adapter for Docker CLI operations"""
    
    def __init__(self):
        self.docker_cmd = "docker"
    
    def is_docker_available(self) -> bool:
        """Check if Docker is installed and running"""
        try:
            result = subprocess.run(
                [self.docker_cmd, "info"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def build_image(
        self,
        project_name: str,
        agent_name: str,
        dockerfile_path: str,
        context_path: str,
        tag: str,
        log_file: Optional[Path] = None,
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False,
        platform: Optional[str] = None
    ) -> BuildResult:
        """Build Docker image
        
        Args:
            project_name: Name of the project
            agent_name: Name of the agent
            dockerfile_path: Path to Dockerfile
            context_path: Build context path
            tag: Image tag
            log_file: Optional path to save build logs
            build_args: Optional build arguments
            no_cache: Whether to build without cache
            platform: Optional target platform
            
        Returns:
            BuildResult with build information
        """
        cmd = [self.docker_cmd, "build"]
        
        # Add options
        if no_cache:
            cmd.append("--no-cache")
        
        if platform:
            cmd.extend(["--platform", platform])
        
        # Add build args
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
        
        # Add tag
        cmd.extend(["-t", tag])
        
        # Add dockerfile and context
        cmd.extend(["-f", dockerfile_path, context_path])
        
        # Execute build
        start_time = datetime.now()
        
        try:
            # Open log file if specified
            log_handle = None
            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                log_handle = open(log_file, 'w')
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=context_path
            )
            
            # Stream output
            output_lines = []
            for line in process.stdout:
                # Print to console
                print(line, end='')
                # Save to memory
                output_lines.append(line)
                # Write to log file
                if log_handle:
                    log_handle.write(line)
                    log_handle.flush()
            
            process.wait()
            
            if log_handle:
                log_handle.close()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if process.returncode == 0:
                # Get image info
                image_info = self.get_image_info(tag)
                
                return BuildResult(
                    success=True,
                    project_name=project_name,
                    agent_name=agent_name,
                    image_tag=tag,
                    image_id=image_info.get('Id'),
                    size=image_info.get('Size'),
                    duration=duration,
                    logs=''.join(output_lines),
                    log_file=log_file
                )
            else:
                return BuildResult(
                    success=False,
                    project_name=project_name,
                    agent_name=agent_name,
                    error='Build failed',
                    duration=duration,
                    logs=''.join(output_lines),
                    log_file=log_file
                )
        
        except Exception as e:
            if log_handle:
                log_handle.close()
            
            return BuildResult(
                success=False,
                project_name=project_name,
                agent_name=agent_name,
                error=str(e),
                duration=(datetime.now() - start_time).total_seconds(),
                log_file=log_file
            )
    
    def get_image_info(self, tag: str) -> Dict[str, Any]:
        """Get image information
        
        Args:
            tag: Image tag
            
        Returns:
            Dictionary with image information
        """
        try:
            result = subprocess.run(
                [self.docker_cmd, "inspect", tag],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return info[0] if info else {}
            
            return {}
        except Exception:
            return {}
    
    def push_image(self, tag: str) -> tuple[bool, str]:
        """Push image to registry
        
        Args:
            tag: Image tag to push
            
        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"\nPushing image: {tag}")
            
            process = subprocess.Popen(
                [self.docker_cmd, "push", tag],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Stream output
            output_lines = []
            for line in process.stdout:
                print(line, end='')
                output_lines.append(line)
            
            process.wait()
            
            if process.returncode == 0:
                return True, "Push successful"
            else:
                return False, ''.join(output_lines)
        
        except Exception as e:
            return False, str(e)
    
    def tag_image(self, source_tag: str, target_tag: str) -> bool:
        """Tag an image
        
        Args:
            source_tag: Source image tag
            target_tag: Target image tag
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                [self.docker_cmd, "tag", source_tag, target_tag],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def remove_image(self, tag: str) -> bool:
        """Remove an image
        
        Args:
            tag: Image tag to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                [self.docker_cmd, "rmi", tag],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False
