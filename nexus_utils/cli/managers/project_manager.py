"""Project manager - handles project lifecycle"""

import os
import hashlib
import json
import tarfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base import ResourceManager
from ..models.project import Project, ProjectConfig, ProjectStatus
from ..models.backup import Backup, BackupManifest
from ..models.common import Dependency, DirectoryTree, ValidationResult


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
    
    # ========================================================================
    # BACKUP AND RESTORE METHODS
    # ========================================================================
    
    def backup_project(self, name: str, output_path: Optional[str] = None) -> Backup:
        """Create a backup of a project
        
        Args:
            name: Name of the project to backup
            output_path: Optional custom output path for backup
            
        Returns:
            Backup object with backup information
        """
        # Validate project exists
        project = self.get_project(name)
        if not project:
            raise ValueError(f"Project '{name}' not found")
        
        # Ensure backup directory exists
        backup_dir = "backups"
        if not self.fs.exists(backup_dir):
            self.fs.create_directory(backup_dir)
        
        # Generate backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}.tar.gz"
        
        # Determine backup path
        if output_path:
            backup_path = Path(output_path) / backup_name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            backup_path = self.fs.base_path / backup_dir / backup_name
        
        # Collect all resources to backup
        resources = self._collect_project_resources(name)
        
        # Calculate checksums for all files
        checksums = self._calculate_checksums(resources)
        
        # Create manifest
        manifest = BackupManifest(
            version="1.0.0",
            project_name=name,
            created_at=datetime.now(),
            nexus_version="v2.1.0",
            resources=self._categorize_resources(resources),
            checksums=checksums,
            metadata={
                'total_files': len(resources),
                'total_size': sum(self._get_file_size(r) for r in resources),
                'compression': 'gzip'
            }
        )
        
        # Create tar.gz archive
        self._create_archive(backup_path, resources, manifest)
        
        # Calculate backup file checksum
        backup_checksum = self._calculate_file_checksum(backup_path)
        
        # Get backup file size
        backup_size = backup_path.stat().st_size
        
        return Backup(
            name=backup_name,
            path=backup_path,
            project_name=name,
            created_at=datetime.now(),
            size=backup_size,
            format="tar.gz",
            manifest=manifest,
            checksum=backup_checksum
        )
    
    def restore_project(self, backup_path: str, project_name: Optional[str] = None, 
                       force: bool = False) -> Project:
        """Restore a project from backup
        
        Args:
            backup_path: Path to backup file
            project_name: Optional project name (uses backup's project name if not provided)
            force: If True, overwrite existing project
            
        Returns:
            Restored Project object
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise ValueError(f"Backup file not found: {backup_path}")
        
        # Validate backup
        validation = self.validate_backup(backup_path)
        if not validation.success:
            raise ValueError(f"Invalid backup: {', '.join(validation.errors)}")
        
        # Extract and load manifest
        manifest = self._extract_manifest(backup_file)
        target_project_name = project_name or manifest.project_name
        
        # Check if project already exists
        existing_project = self.get_project(target_project_name)
        if existing_project and not force:
            raise ValueError(
                f"Project '{target_project_name}' already exists. "
                f"Use --force to overwrite."
            )
        
        # Create safety backup if overwriting
        if existing_project and force:
            safety_backup_name = f"{target_project_name}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
            backup_dir = self.fs.base_path / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_project(target_project_name, str(backup_dir))
        
        # Extract backup to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract archive
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_path)
            
            # Verify checksums
            if not self._verify_checksums(temp_path, manifest):
                raise ValueError("Checksum verification failed")
            
            # Remove existing project if force
            if existing_project and force:
                self._remove_project_resources(target_project_name)
            
            # Move resources to final locations
            self._restore_resources(temp_path, target_project_name, manifest)
        
        # Return restored project
        return self.get_project(target_project_name)
    
    def list_backups(self) -> List[Backup]:
        """List all available backups"""
        backup_dir = self.fs.base_path / "backups"
        if not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in backup_dir.glob("*.tar.gz"):
            try:
                manifest = self._extract_manifest(backup_file)
                backup_size = backup_file.stat().st_size
                
                backup = Backup(
                    name=backup_file.name,
                    path=backup_file,
                    project_name=manifest.project_name,
                    created_at=manifest.created_at,
                    size=backup_size,
                    format="tar.gz",
                    manifest=manifest
                )
                backups.append(backup)
            except Exception:
                # Skip invalid backup files
                continue
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups
    
    def get_backup(self, backup_name: str) -> Optional[Backup]:
        """Get backup by name"""
        backup_path = self.fs.base_path / "backups" / backup_name
        if not backup_path.exists():
            return None
        
        try:
            manifest = self._extract_manifest(backup_path)
            backup_size = backup_path.stat().st_size
            
            return Backup(
                name=backup_name,
                path=backup_path,
                project_name=manifest.project_name,
                created_at=manifest.created_at,
                size=backup_size,
                format="tar.gz",
                manifest=manifest
            )
        except Exception:
            return None
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup"""
        backup_path = self.fs.base_path / "backups" / backup_name
        if not backup_path.exists():
            raise ValueError(f"Backup '{backup_name}' not found")
        
        backup_path.unlink()
        return True
    
    def validate_backup(self, backup_path: str) -> ValidationResult:
        """Validate backup integrity"""
        errors = []
        warnings = []
        
        backup_file = Path(backup_path)
        
        # Check file exists
        if not backup_file.exists():
            errors.append(f"Backup file not found: {backup_path}")
            return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        # Check file format
        if not backup_file.name.endswith('.tar.gz'):
            errors.append("Invalid backup format (must be .tar.gz)")
        
        try:
            # Try to open as tar.gz
            with tarfile.open(backup_file, 'r:gz') as tar:
                # Check manifest exists
                manifest_found = False
                for member in tar.getmembers():
                    if member.name == 'manifest.json':
                        manifest_found = True
                        break
                
                if not manifest_found:
                    errors.append("Manifest file not found in backup")
                else:
                    # Extract and validate manifest
                    manifest_file = tar.extractfile('manifest.json')
                    if manifest_file:
                        manifest_data = json.load(manifest_file)
                        
                        # Check required fields
                        required_fields = ['version', 'project_name', 'created_at', 
                                         'nexus_version', 'resources', 'checksums']
                        for field in required_fields:
                            if field not in manifest_data:
                                errors.append(f"Missing required field in manifest: {field}")
        
        except tarfile.TarError as e:
            errors.append(f"Invalid tar.gz archive: {e}")
        except json.JSONDecodeError as e:
            errors.append(f"Invalid manifest JSON: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_backup_manifest(self, backup_path: str) -> BackupManifest:
        """Get backup manifest"""
        return self._extract_manifest(Path(backup_path))
    
    # Private helper methods for backup/restore
    
    def _collect_project_resources(self, project_name: str) -> List[Path]:
        """Collect all files for a project"""
        resources = []
        base_path = self.fs.base_path
        
        # Project directory
        project_dir = base_path / "projects" / project_name
        if project_dir.exists():
            resources.extend(self._collect_files(project_dir))
        
        # Agents
        agents_dir = base_path / "agents" / "generated_agents" / project_name
        if agents_dir.exists():
            resources.extend(self._collect_files(agents_dir))
        
        # Prompts
        prompts_dir = base_path / "prompts" / "generated_agents_prompts" / project_name
        if prompts_dir.exists():
            resources.extend(self._collect_files(prompts_dir))
        
        # Tools
        tools_dir = base_path / "tools" / "generated_tools" / project_name
        if tools_dir.exists():
            resources.extend(self._collect_files(tools_dir))
        
        return resources
    
    def _collect_files(self, directory: Path) -> List[Path]:
        """Recursively collect all files in a directory"""
        files = []
        for item in directory.rglob('*'):
            if item.is_file():
                files.append(item)
        return files
    
    def _calculate_checksums(self, files: List[Path]) -> Dict[str, str]:
        """Calculate SHA-256 checksums for files"""
        checksums = {}
        base_path = self.fs.base_path
        
        for file_path in files:
            relative_path = file_path.relative_to(base_path)
            checksum = self._calculate_file_checksum(file_path)
            checksums[str(relative_path)] = checksum
        
        return checksums
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum for a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _categorize_resources(self, files: List[Path]) -> Dict[str, List[str]]:
        """Categorize files by resource type"""
        base_path = self.fs.base_path
        categories = {
            'project': [],
            'agents': [],
            'prompts': [],
            'tools': []
        }
        
        for file_path in files:
            relative_path = str(file_path.relative_to(base_path))
            
            if relative_path.startswith('projects/'):
                categories['project'].append(relative_path)
            elif relative_path.startswith('agents/'):
                categories['agents'].append(relative_path)
            elif relative_path.startswith('prompts/'):
                categories['prompts'].append(relative_path)
            elif relative_path.startswith('tools/'):
                categories['tools'].append(relative_path)
        
        return categories
    
    def _get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        return file_path.stat().st_size
    
    def _create_archive(self, backup_path: Path, files: List[Path], 
                       manifest: BackupManifest):
        """Create tar.gz archive with files and manifest"""
        base_path = self.fs.base_path
        
        with tarfile.open(backup_path, 'w:gz') as tar:
            # Add manifest
            manifest_json = json.dumps(manifest.to_dict(), indent=2)
            manifest_bytes = manifest_json.encode('utf-8')
            
            import io
            manifest_file = io.BytesIO(manifest_bytes)
            tarinfo = tarfile.TarInfo(name='manifest.json')
            tarinfo.size = len(manifest_bytes)
            tar.addfile(tarinfo, manifest_file)
            
            # Add all files
            for file_path in files:
                arcname = str(file_path.relative_to(base_path))
                tar.add(file_path, arcname=arcname)
    
    def _extract_manifest(self, backup_path: Path) -> BackupManifest:
        """Extract manifest from backup"""
        with tarfile.open(backup_path, 'r:gz') as tar:
            manifest_file = tar.extractfile('manifest.json')
            if not manifest_file:
                raise ValueError("Manifest not found in backup")
            
            manifest_data = json.load(manifest_file)
            return BackupManifest.from_dict(manifest_data)
    
    def _verify_checksums(self, temp_path: Path, manifest: BackupManifest) -> bool:
        """Verify checksums of extracted files"""
        for relative_path, expected_checksum in manifest.checksums.items():
            file_path = temp_path / relative_path
            if not file_path.exists():
                return False
            
            actual_checksum = self._calculate_file_checksum(file_path)
            if actual_checksum != expected_checksum:
                return False
        
        return True
    
    def _remove_project_resources(self, project_name: str):
        """Remove all resources for a project"""
        base_path = self.fs.base_path
        
        # Remove project directory
        project_dir = base_path / "projects" / project_name
        if project_dir.exists():
            self.fs.delete_directory(str(project_dir.relative_to(base_path)))
        
        # Remove agents
        agents_dir = base_path / "agents" / "generated_agents" / project_name
        if agents_dir.exists():
            self.fs.delete_directory(str(agents_dir.relative_to(base_path)))
        
        # Remove prompts
        prompts_dir = base_path / "prompts" / "generated_agents_prompts" / project_name
        if prompts_dir.exists():
            self.fs.delete_directory(str(prompts_dir.relative_to(base_path)))
        
        # Remove tools
        tools_dir = base_path / "tools" / "generated_tools" / project_name
        if tools_dir.exists():
            self.fs.delete_directory(str(tools_dir.relative_to(base_path)))
    
    def _restore_resources(self, temp_path: Path, project_name: str, 
                          manifest: BackupManifest):
        """Restore resources from temporary directory to final locations
        
        This method handles renaming the project if the target name differs from
        the backup's original project name. It correctly maps all resource paths:
        - projects/<old_name>/ -> projects/<new_name>/
        - agents/generated_agents/<old_name>/ -> agents/generated_agents/<new_name>/
        - prompts/generated_agents_prompts/<old_name>/ -> prompts/generated_agents_prompts/<new_name>/
        - tools/generated_tools/<old_name>/ -> tools/generated_tools/<new_name>/
        """
        base_path = self.fs.base_path
        original_project_name = manifest.project_name
        
        for resource_type, paths in manifest.resources.items():
            for relative_path in paths:
                source = temp_path / relative_path
                
                # If project name changed, update the path
                if project_name != original_project_name:
                    # Replace old project name with new project name in the path
                    path_str = str(relative_path)
                    
                    # Handle different resource types
                    if path_str.startswith(f'projects/{original_project_name}/'):
                        path_str = path_str.replace(
                            f'projects/{original_project_name}/',
                            f'projects/{project_name}/',
                            1
                        )
                    elif path_str.startswith(f'agents/generated_agents/{original_project_name}/'):
                        path_str = path_str.replace(
                            f'agents/generated_agents/{original_project_name}/',
                            f'agents/generated_agents/{project_name}/',
                            1
                        )
                    elif path_str.startswith(f'prompts/generated_agents_prompts/{original_project_name}/'):
                        path_str = path_str.replace(
                            f'prompts/generated_agents_prompts/{original_project_name}/',
                            f'prompts/generated_agents_prompts/{project_name}/',
                            1
                        )
                    elif path_str.startswith(f'tools/generated_tools/{original_project_name}/'):
                        path_str = path_str.replace(
                            f'tools/generated_tools/{original_project_name}/',
                            f'tools/generated_tools/{project_name}/',
                            1
                        )
                    
                    target = base_path / path_str
                else:
                    target = base_path / relative_path
                
                # Create parent directory if needed
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                if source.exists():
                    shutil.copy2(source, target)
                else:
                    # Log warning but continue
                    import logging
                    logging.warning(f"Source file not found during restore: {source}")
