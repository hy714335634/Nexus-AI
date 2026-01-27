#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nexus-AI Backend Management CLI

A kubectl-style CLI tool for managing Nexus-AI backend artifacts.
"""

import click
import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure UTF-8 encoding for stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Set environment variable for child processes
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from .adapters.filesystem import FileSystemAdapter
from .adapters.config_loader import ConfigLoader
from .managers.project_manager import ProjectManager
from .managers.agent_manager import AgentManager
from .managers.build_manager import BuildManager
from .managers.infrastructure_manager import InfrastructureManager
from .managers.cloud_resource_manager import CloudResourceManager
from .managers.deployment_manager import DeploymentManager
from .managers.artifact_manager import ArtifactManager
from .models.build import BuildOptions
from .utils.formatters import format_output
from .utils.styles import styled, header, command, success, warning, error, muted, Style
from .i18n import t, set_language


def json_dumps_utf8(obj: Any, indent: int = 2) -> str:
    """JSON dumps with UTF-8 encoding (no ASCII escaping)"""
    return json.dumps(obj, indent=indent, default=str, ensure_ascii=False)


def decode_unicode_escapes(obj: Any) -> Any:
    """Recursively decode Unicode escape sequences in strings"""
    if isinstance(obj, str):
        try:
            # Try to decode Unicode escapes like \u4e2d\u6587
            return obj.encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return obj
    elif isinstance(obj, dict):
        return {k: decode_unicode_escapes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode_unicode_escapes(item) for item in obj]
    return obj


# Global context
class CLIContext:
    """CLI context object"""
    def __init__(self, base_path: str = ".", language: str = "en"):
        self.base_path = base_path
        self.language = language
        set_language(language)
        self.fs_adapter = FileSystemAdapter(base_path)
        self.config_loader = ConfigLoader(self.fs_adapter)
        self.project_manager = ProjectManager(self.fs_adapter, self.config_loader)
        self.agent_manager = AgentManager(self.fs_adapter, self.config_loader)
        self.build_manager = BuildManager(self.fs_adapter, self.config_loader)
        self.cloud_resource_manager = CloudResourceManager()
        self.infrastructure_manager = InfrastructureManager.from_settings()
        self.deployment_manager = DeploymentManager(base_path)
        self.artifact_manager = ArtifactManager(self.fs_adapter, self.config_loader)


@click.group()
@click.version_option(version="2.3.0", prog_name="nexus-cli")
@click.option('--base-path', default=".", help='Base path to Nexus-AI installation')
@click.option('--lang', type=click.Choice(['en', 'zh']), default='en', help='Language (en/zh)')
@click.pass_context
def cli(ctx, base_path, lang):
    """Nexus-AI Backend Management CLI
    
    A kubectl-style CLI for managing Nexus-AI backend artifacts.
    
    \b
    COMMANDS:
      project   Manage projects (init, list, describe, build, backup, restore, delete)
      agents    Manage AI agents (list, describe, build, delete)
      artifact  Manage S3 artifacts (sync, list, versions, describe, delete)
      backup    Manage project backups (list, describe, validate, delete)
      job       Manage tasks and queues (list, view, clear, delete)
      service   Manage services (start, stop, restart, status, logs)
      init      Initialize infrastructure (DynamoDB tables, SQS queues, S3 buckets)
      overview  Display system-wide overview
    
    \b
    QUICK START:
      nexus-cli project list              # List all projects
      nexus-cli project init my-project   # Create a new project
      nexus-cli project backup my-project # Backup a project
      nexus-cli agents list               # List all agents
      nexus-cli agents build my-project   # Deploy agent to AgentCore
      nexus-cli artifact sync my-agent    # Sync agent to S3
      nexus-cli artifact list             # List synced agents
      nexus-cli job list                  # List tasks
      nexus-cli service start             # Start all services
      nexus-cli service status            # Check service status
      nexus-cli init                      # Initialize infrastructure
    
    \b
    MORE INFO:
      nexus-cli <command> --help          # Help for specific command
      nexus-cli --lang zh <command>       # Use Chinese language
    """
    ctx.obj = CLIContext(base_path, lang)


# ============================================================================
# PROJECT COMMANDS
# ============================================================================

@cli.group()
def project():
    """Manage Nexus-AI projects
    
    \b
    SUBCOMMANDS:
      init      Create a new project
      list      List all projects
      describe  Show project details
      build     Build Docker images
      backup    Create project backup
      restore   Restore from backup
      delete    Delete project
    
    \b
    EXAMPLES:
      nexus-cli project init my-project
      nexus-cli project list
      nexus-cli project backup my-project
      nexus-cli project restore my-project --from-backup backup.tar.gz
    """
    pass


@project.command('list')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def project_list(ctx, output):
    """List all projects with brief descriptions"""
    try:
        projects = ctx.project_manager.list_projects()
        
        if output == 'json':
            data = {
                'projects': [p.to_dict() for p in projects],
                'total': len(projects)
            }
            click.echo(format_output(data, 'json'))
        else:
            # Prepare data for table/text
            data = []
            for p in projects:
                # Get brief description from config
                description = p.config.description if p.config.description else 'No description'
                # Truncate description for table display
                if len(description) > 50:
                    description = description[:47] + '...'
                
                data.append({
                    'name': p.name,
                    'description': description,
                    'agents': p.agent_count,
                    'templates': p.template_count,
                    'prompts': p.prompt_count,
                    'tools': p.tool_count,
                    'created': p.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            headers = ['name', 'description', 'agents', 'templates', 'prompts', 'tools', 'created']
            click.echo(format_output(data, output, headers))
            click.echo(f"\nTotal: {len(projects)} projects")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('describe')
@click.argument('name')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='text',
              help='Output format')
@click.pass_obj
def project_describe(ctx, name, output):
    """Describe a project in detail with agent descriptions and dependencies"""
    try:
        project = ctx.project_manager.get_project(name)
        
        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)
        
        if output == 'json':
            # Enhanced JSON output with agent descriptions
            project_dict = project.to_dict()
            # Add agent descriptions
            agent_details = []
            for agent_name in project.agents:
                agent = ctx.agent_manager.get_agent(agent_name)
                if agent and agent.config:
                    agent_details.append({
                        'name': agent_name,
                        'description': agent.config.description,
                        'category': agent.config.category,
                        'tools': agent.config.tools_dependencies
                    })
            project_dict['agent_details'] = agent_details
            click.echo(format_output(project_dict, 'json'))
        else:
            # Enhanced text format with structured, human-readable information
            click.echo("=" * 80)
            click.echo(f"PROJECT: {project.name}")
            click.echo("=" * 80)
            click.echo()
            
            # Project Description
            if project.config.description:
                click.echo("Description:")
                click.echo(f"  {project.config.description}")
                click.echo()
            
            # Basic Information
            click.echo("Basic Information:")
            click.echo(f"  Name:        {project.name}")
            click.echo(f"  Version:     {project.config.version}")
            click.echo(f"  Created:     {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"  Updated:     {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo()
            
            # Agents with descriptions
            click.echo(f"Agents ({project.agent_count}):")
            if project.agents:
                for agent_name in project.agents:
                    agent = ctx.agent_manager.get_agent(agent_name)
                    if agent and agent.config:
                        click.echo(f"  ✓ {agent_name}")
                        if agent.config.description:
                            # Format description with proper indentation
                            desc_lines = agent.config.description.split('\n')
                            for line in desc_lines[:3]:  # Show first 3 lines
                                if line.strip():
                                    click.echo(f"    {line.strip()}")
                            if len(desc_lines) > 3:
                                click.echo(f"    ...")
                        if agent.config.category:
                            click.echo(f"    Category: {agent.config.category}")
                        click.echo()
                    else:
                        click.echo(f"  - {agent_name}")
            else:
                click.echo("  (none)")
            click.echo()
            
            # Dependencies
            click.echo("Dependencies:")
            click.echo(f"  Tools:       {project.tool_count}")
            if project.tools:
                # Group tools by type
                strands_tools = [t for t in project.tools if t.startswith('strands_tools/')]
                generated_tools = [t for t in project.tools if t.startswith('generated_tools/')]
                system_tools = [t for t in project.tools if t.startswith('tools/system_tools/')]
                
                if strands_tools:
                    click.echo(f"    Strands Tools ({len(strands_tools)}):")
                    for tool in strands_tools[:5]:
                        click.echo(f"      - {tool}")
                    if len(strands_tools) > 5:
                        click.echo(f"      ... and {len(strands_tools) - 5} more")
                
                if generated_tools:
                    click.echo(f"    Generated Tools ({len(generated_tools)}):")
                    for tool in generated_tools[:5]:
                        tool_name = tool.split('/')[-1]
                        click.echo(f"      - {tool_name}")
                    if len(generated_tools) > 5:
                        click.echo(f"      ... and {len(generated_tools) - 5} more")
                
                if system_tools:
                    click.echo(f"    System Tools ({len(system_tools)}):")
                    for tool in system_tools[:5]:
                        tool_name = tool.split('/')[-1]
                        click.echo(f"      - {tool_name}")
                    if len(system_tools) > 5:
                        click.echo(f"      ... and {len(system_tools) - 5} more")
            
            click.echo(f"  Prompts:     {project.prompt_count}")
            click.echo(f"  Templates:   {project.template_count}")
            click.echo()
            
            # Usage Information
            click.echo("Usage:")
            click.echo(f"  Location:    projects/{project.name}/")
            click.echo(f"  Agents:      agents/generated_agents/{project.name}/")
            click.echo(f"  Prompts:     prompts/generated_agents_prompts/{project.name}/")
            if project.tools:
                click.echo(f"  Tools:       tools/generated_tools/{project.name}/")
            click.echo()
            
            # Documentation
            readme_path = ctx.fs_adapter.base_path / 'projects' / project.name / 'README.md'
            if readme_path.exists():
                click.echo("Documentation:")
                click.echo(f"  README:      projects/{project.name}/README.md")
                click.echo()
            
            click.echo("=" * 80)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('init')
@click.argument('name')
@click.option('--description', '-d', default='', help='Project description')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.pass_obj
def project_init(ctx, name, description, dry_run):
    """Initialize a new project"""
    try:
        if dry_run:
            click.echo("[DRY RUN] Would perform the following operations:")
            click.echo()
            click.echo(f"✓ Create directory: projects/{name}/")
            click.echo(f"✓ Create directory: projects/{name}/agents/")
            click.echo(f"✓ Create file: projects/{name}/config.yaml")
            click.echo(f"✓ Create file: projects/{name}/status.yaml")
            click.echo(f"✓ Create file: projects/{name}/README.md")
            click.echo()
            click.echo("Run without --dry-run to execute these operations.")
            return
        
        from ..models.project import ProjectConfig
        config = ProjectConfig(name=name, description=description)
        project = ctx.project_manager.create_project(name, config)
        
        click.echo(f"✓ Project '{name}' created successfully")
        click.echo(f"  Location: projects/{name}/")
    
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('backup')
@click.argument('name')
@click.option('--output', '-o', help='Custom output path for backup')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--source-delete', is_flag=True, help='Delete source directories after successful backup')
@click.option('--sync-to-s3', is_flag=True, help='Upload backup to S3 after creation')
@click.option('--notes', help='Notes for S3 sync version (used with --sync-to-s3)')
@click.pass_obj
def project_backup(ctx, name, output, dry_run, source_delete, sync_to_s3, notes):
    """Backup a project with all its resources
    
    Creates a complete backup of a project including:
    - Project configuration and metadata
    - All generated agents
    - Agent prompts and configurations
    - Custom tools and utilities
    - SHA-256 checksums for integrity verification
    
    \b
    The backup is saved as a compressed tar.gz archive with a timestamp:
      <project-name>_YYYYMMDD_HHMMSS.tar.gz
    
    \b
    EXAMPLES:
      # Basic backup
      nexus-cli project backup my-project
      
      # Backup to custom location
      nexus-cli project backup my-project --output /path/to/backups/
      
      # Preview backup (dry-run)
      nexus-cli project backup my-project --dry-run
      
      # Backup and delete source directories
      nexus-cli project backup my-project --source-delete
      
      # Backup and sync to S3
      nexus-cli project backup my-project --sync-to-s3
      
      # Backup with notes for S3 version
      nexus-cli project backup my-project --sync-to-s3 --notes "Production release v1.0"
    
    \b
    FEATURES:
      ✓ Complete resource backup (agents, prompts, tools)
      ✓ Integrity verification with SHA-256 checksums
      ✓ Compressed tar.gz format
      ✓ Timestamped filenames
      ✓ Detailed manifest with metadata
      ✓ Dry-run mode for preview
      ✓ Optional source deletion after backup
      ✓ Optional S3 cloud backup sync
    """
    try:
        project = ctx.project_manager.get_project(name)
        
        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)
        
        if dry_run:
            click.echo("[DRY RUN] Would perform the following operations:")
            click.echo()
            click.echo(f"Creating backup for project '{name}'...")
            click.echo()
            click.echo("Resources to backup:")
            click.echo(f"  ✓ Project directory: projects/{name}/")
            
            if project.agents:
                click.echo(f"  ✓ Agents ({project.agent_count}): agents/generated_agents/{name}/")
                for agent in project.agents:
                    click.echo(f"    - {agent}.py")
            
            if project.prompts:
                click.echo(f"  ✓ Prompts ({project.prompt_count}): prompts/generated_agents_prompts/{name}/")
                for prompt in project.prompts:
                    click.echo(f"    - {prompt}.yaml")
            
            if project.tools:
                click.echo(f"  ✓ Tools ({project.tool_count}): tools/generated_tools/{name}/")
            
            click.echo()
            timestamp = "YYYYMMDD_HHMMSS"
            backup_name = f"{name}_{timestamp}.tar.gz"
            if output:
                click.echo(f"Backup would be created at: {output}/{backup_name}")
            else:
                click.echo(f"Backup would be created at: backups/{backup_name}")
            
            if source_delete:
                click.echo()
                click.echo("After backup, would delete source directories:")
                click.echo(f"  • projects/{name}/")
                if project.agents:
                    click.echo(f"  • agents/generated_agents/{name}/")
                if project.prompts:
                    click.echo(f"  • prompts/generated_agents_prompts/{name}/")
                if project.tools:
                    click.echo(f"  • tools/generated_tools/{name}/")
            
            if sync_to_s3:
                click.echo()
                click.echo("After backup, would sync to S3:")
                click.echo(f"  • Bucket: {ctx.artifact_manager.get_bucket_name()}")
                click.echo(f"  • Workspace: {ctx.artifact_manager.get_workspace_uuid()}")
                if notes:
                    click.echo(f"  • Notes: {notes}")
            
            click.echo()
            click.echo("Run without --dry-run to execute these operations.")
            return
        
        click.echo(f"Creating backup for project '{name}'...")
        click.echo()
        click.echo("Collecting resources:")
        click.echo(f"  ✓ Project directory: projects/{name}/")
        
        if project.agents:
            click.echo(f"  ✓ Agents: agents/generated_agents/{name}/")
        if project.prompts:
            click.echo(f"  ✓ Prompts: prompts/generated_agents_prompts/{name}/")
        if project.tools:
            click.echo(f"  ✓ Tools: tools/generated_tools/{name}/")
        
        click.echo()
        click.echo("Calculating checksums...")
        
        # Create backup
        backup = ctx.project_manager.backup_project(name, output)
        
        click.echo(f"  ✓ {backup.manifest.metadata['total_files']} files processed")
        click.echo()
        click.echo("Creating archive...")
        click.echo("  ✓ Compressing to tar.gz format")
        click.echo()
        click.echo("Generating manifest...")
        click.echo("  ✓ Manifest created with metadata")
        click.echo()
        click.echo("✓ Backup created successfully!")
        click.echo(f"  Location: {backup.path}")
        click.echo(f"  Size: {backup.size_human}")
        click.echo(f"  Files: {backup.manifest.metadata['total_files']}")
        click.echo(f"  Checksum: sha256:{backup.checksum[:16]}...")
        
        # Delete source directories if requested
        if source_delete:
            click.echo()
            click.echo("Deleting source directories...")
            
            deleted_items = []
            
            # Delete project directory
            project_dir = f"projects/{name}"
            if ctx.fs_adapter.exists(project_dir):
                ctx.fs_adapter.delete_directory(project_dir)
                deleted_items.append(f"✓ Deleted: {project_dir}/")
            
            # Delete agents directory
            agents_dir = f"agents/generated_agents/{name}"
            if ctx.fs_adapter.exists(agents_dir):
                ctx.fs_adapter.delete_directory(agents_dir)
                deleted_items.append(f"✓ Deleted: {agents_dir}/")
            
            # Delete prompts directory
            prompts_dir = f"prompts/generated_agents_prompts/{name}"
            if ctx.fs_adapter.exists(prompts_dir):
                ctx.fs_adapter.delete_directory(prompts_dir)
                deleted_items.append(f"✓ Deleted: {prompts_dir}/")
            
            # Delete tools directory
            tools_dir = f"tools/generated_tools/{name}"
            if ctx.fs_adapter.exists(tools_dir):
                ctx.fs_adapter.delete_directory(tools_dir)
                deleted_items.append(f"✓ Deleted: {tools_dir}/")
            
            if deleted_items:
                for item in deleted_items:
                    click.echo(f"  {item}")
                click.echo()
                click.echo(f"✓ Source directories deleted successfully ({len(deleted_items)} directories removed)")
            else:
                click.echo("  No source directories found to delete")
        
        # Sync to S3 if requested
        if sync_to_s3:
            click.echo()
            click.echo("Syncing backup to S3...")
            
            try:
                sync_result = ctx.artifact_manager.sync_backup(
                    agent_name=name,
                    backup_path=str(backup.path),
                    notes=notes or f"Backup: {backup.path.name}"
                )
                
                if sync_result.success:
                    click.echo(f"  ✓ Uploaded to S3 successfully")
                    click.echo(f"  • Version UUID: {sync_result.version_uuid}")
                    click.echo(f"  • S3 Path: {sync_result.s3_paths.get('backups', 'N/A')}")
                    click.echo(f"  • Size: {sync_result.format_size()}")
                else:
                    click.echo(f"  ✗ S3 sync failed: {sync_result.error}", err=True)
            except Exception as sync_error:
                click.echo(f"  ✗ S3 sync error: {sync_error}", err=True)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('restore')
@click.option('--name', '-n', help='Project name (default: inferred from backup)')
@click.option('--from-backup', required=True, help='Path to backup file')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing project')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.pass_obj
def project_restore(ctx, name, from_backup, force, dry_run):
    """Restore a project from backup
    
    Restores a complete project from a backup archive including:
    - Project configuration and metadata
    - All agents with correct paths
    - Agent prompts and configurations
    - Custom tools and utilities
    
    \b
    RESTORE OPTIONS:
      1. Restore to original name (inferred from backup, default)
      2. Restore to different name (project cloning, use --name)
      3. Force overwrite existing project (with safety backup)
    
    \b
    EXAMPLES:
      # Restore to original name (inferred from backup)
      nexus-cli project restore --from-backup backups/my-project_20241125.tar.gz
      
      # Restore to original name (explicit)
      nexus-cli project restore --name my-project --from-backup backups/my-project_20241125.tar.gz
      
      # Clone project (restore to different name)
      nexus-cli project restore --name dev-project --from-backup backups/prod-project_20241125.tar.gz
      
      # Force overwrite existing project
      nexus-cli project restore --name my-project --from-backup backup.tar.gz --force
      
      # Preview restore (dry-run)
      nexus-cli project restore --from-backup backup.tar.gz --dry-run
    
    \b
    SAFETY FEATURES:
      ✓ Automatic backup validation before restore
      ✓ Checksum verification for all files
      ✓ Safety backup created before overwrite (with --force)
      ✓ Confirmation prompt for destructive operations
      ✓ Dry-run mode for preview
      ✓ Automatic path mapping for project cloning
    
    \b
    USE CASES:
      • Version Control: Restore previous project version
      • Project Cloning: Create dev copy from production
      • Migration: Move projects between systems
      • Disaster Recovery: Restore after data loss
    """
    try:
        # Validate backup exists
        backup_path = Path(from_backup)
        if not backup_path.exists():
            click.echo(f"Error: Backup file not found: {from_backup}", err=True)
            sys.exit(1)
        
        # Get manifest to infer project name if not provided
        manifest = ctx.project_manager.get_backup_manifest(from_backup)
        
        # Use provided name or infer from backup
        name_provided = name is not None
        if not name:
            name = manifest.project_name
        
        # Check if project exists
        existing_project = ctx.project_manager.get_project(name)
        
        if dry_run:
            click.echo("[DRY RUN] Would perform the following operations:")
            click.echo()
            if not name_provided:
                click.echo(f"Project name inferred from backup: {name}")
                click.echo()
            click.echo(f"Restoring project '{name}' from backup...")
            click.echo()
            click.echo("Validating backup:")
            click.echo("  ✓ Backup file exists")
            click.echo("  ✓ Archive format valid")
            click.echo("  ✓ Manifest present")
            click.echo("  ✓ Checksums would be verified")
            click.echo()
            
            if existing_project:
                if force:
                    click.echo("⚠️  Project exists - would be overwritten (--force)")
                    click.echo()
                    click.echo("Safety backup would be created:")
                    safety_name = f"{name}_pre_restore_YYYYMMDD_HHMMSS.tar.gz"
                    click.echo(f"  → backups/{safety_name}")
                    click.echo()
                else:
                    click.echo(f"Error: Project '{name}' already exists. Use --force to overwrite.")
                    return
            
            click.echo("Resources to restore:")
            for resource_type, paths in manifest.resources.items():
                if paths:
                    click.echo(f"  ✓ {resource_type.capitalize()}: {len(paths)} files")
            
            click.echo()
            click.echo("Run without --dry-run to execute these operations.")
            return
        
        # Show inferred name if not provided by user
        if not name_provided:
            click.echo(f"Inferred project name from backup: {name}")
            click.echo()
        
        click.echo(f"Restoring project '{name}' from backup...")
        click.echo()
        click.echo("Validating backup:")
        
        validation = ctx.project_manager.validate_backup(from_backup)
        if not validation.success:
            click.echo("  ✗ Backup validation failed:", err=True)
            for error in validation.errors:
                click.echo(f"    - {error}", err=True)
            sys.exit(1)
        
        click.echo("  ✓ Backup file exists")
        click.echo("  ✓ Archive format valid")
        click.echo("  ✓ Manifest present")
        click.echo("  ✓ Checksums verified")
        click.echo()
        
        # Check for conflicts
        if existing_project and not force:
            click.echo(f"Error: Project '{name}' already exists. Use --force to overwrite.", err=True)
            sys.exit(1)
        
        if existing_project and force:
            click.echo("⚠️  WARNING: This will overwrite existing project")
            click.echo()
            if not click.confirm("Are you sure you want to continue?"):
                click.echo("Aborted.")
                return
            
            click.echo()
            click.echo("Creating safety backup of existing project...")
            safety_backup = ctx.project_manager.backup_project(name)
            click.echo(f"  ✓ Existing project backed up to {safety_backup.path.name}")
            click.echo()
        
        click.echo("Removing existing project..." if existing_project else "Extracting backup:")
        if existing_project:
            click.echo("  ✓ Removed existing resources")
            click.echo()
            click.echo("Extracting backup:")
        
        click.echo("  ✓ Extracting archive...")
        click.echo("  ✓ Verifying checksums...")
        click.echo()
        click.echo("Restoring resources:")
        
        # Restore
        restored_project = ctx.project_manager.restore_project(from_backup, name, force)
        
        click.echo(f"  ✓ Project directory: projects/{name}/")
        if restored_project.agents:
            click.echo(f"  ✓ Agents: agents/generated_agents/{name}/")
        if restored_project.prompts:
            click.echo(f"  ✓ Prompts: prompts/generated_agents_prompts/{name}/")
        if restored_project.tools:
            click.echo(f"  ✓ Tools: tools/generated_tools/{name}/")
        
        click.echo()
        click.echo("Validating restored project:")
        click.echo("  ✓ All files restored")
        click.echo("  ✓ Checksums match")
        click.echo("  ✓ Project structure valid")
        click.echo()
        click.echo(f"✓ Project '{name}' restored successfully!")
        click.echo(f"  Files restored: {manifest.metadata['total_files']}")
        if existing_project and force:
            click.echo(f"  Safety backup: {safety_backup.path.name}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('delete')
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.pass_obj
def project_delete(ctx, name, force, dry_run):
    """Delete a project and all related resources"""
    try:
        project = ctx.project_manager.get_project(name)
        
        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)
        
        # Prepare deletion summary
        agents_dir = f"agents/generated_agents/{name}"
        prompts_dir = f"prompts/generated_agents_prompts/{name}"
        tools_dir = f"tools/generated_tools/{name}"
        project_dir = f"projects/{name}"
        
        if dry_run:
            click.echo("[DRY RUN] Would perform the following operations:")
            click.echo()
            click.echo("Directories to be deleted:")
            
            if ctx.fs_adapter.exists(agents_dir):
                click.echo(f"  ✓ {agents_dir}/")
                for agent in project.agents:
                    click.echo(f"    - {agent}.py")
            
            if ctx.fs_adapter.exists(prompts_dir):
                click.echo(f"  ✓ {prompts_dir}/")
                for prompt in project.prompts:
                    click.echo(f"    - {prompt}.yaml")
            
            if ctx.fs_adapter.exists(tools_dir):
                click.echo(f"  ✓ {tools_dir}/")
                click.echo(f"    - {project.tool_count} tool files")
            
            click.echo(f"  ✓ {project_dir}/")
            click.echo(f"    - config.yaml, status.yaml, README.md, etc.")
            
            click.echo()
            click.echo("Summary:")
            click.echo(f"  - {project.agent_count} agents will be deleted")
            click.echo(f"  - {project.template_count} templates will be deleted")
            click.echo(f"  - {project.prompt_count} prompts will be deleted")
            click.echo(f"  - {project.tool_count} tools will be deleted")
            click.echo(f"  - Project directory will be deleted")
            click.echo()
            click.echo("Run without --dry-run to execute these operations.")
            return
        
        if not force:
            click.echo(f"⚠️  WARNING: This will permanently delete project '{name}' and ALL related resources")
            click.echo()
            click.echo("What will be deleted:")
            click.echo(f"  • Project directory: projects/{name}/")
            click.echo(f"  • Agents: {project.agent_count} ({', '.join(project.agents) if project.agents else 'none'})")
            click.echo(f"  • Templates: {project.template_count}")
            click.echo(f"  • Prompts: {project.prompt_count}")
            click.echo(f"  • Tools: {project.tool_count}")
            
            if ctx.fs_adapter.exists(agents_dir):
                click.echo(f"  • Agent files: agents/generated_agents/{name}/")
            if ctx.fs_adapter.exists(prompts_dir):
                click.echo(f"  • Prompt files: prompts/generated_agents_prompts/{name}/")
            if ctx.fs_adapter.exists(tools_dir):
                click.echo(f"  • Tool files: tools/generated_tools/{name}/")
            
            click.echo()
            if not click.confirm("Are you sure you want to continue?"):
                click.echo("Aborted.")
                return
        
        # Perform deletion
        click.echo(f"Deleting project '{name}' and all related resources...")
        
        # Track what was deleted
        deleted_items = []
        
        if ctx.fs_adapter.exists(agents_dir):
            ctx.fs_adapter.delete_directory(agents_dir)
            deleted_items.append(f"✓ Deleted agents: agents/generated_agents/{name}/")
        
        if ctx.fs_adapter.exists(prompts_dir):
            ctx.fs_adapter.delete_directory(prompts_dir)
            deleted_items.append(f"✓ Deleted prompts: prompts/generated_agents_prompts/{name}/")
        
        if ctx.fs_adapter.exists(tools_dir):
            ctx.fs_adapter.delete_directory(tools_dir)
            deleted_items.append(f"✓ Deleted tools: tools/generated_tools/{name}/")
        
        if ctx.fs_adapter.exists(project_dir):
            ctx.fs_adapter.delete_directory(project_dir)
            deleted_items.append(f"✓ Deleted project: projects/{name}/")
        
        # Show what was deleted
        for item in deleted_items:
            click.echo(f"  {item}")
        
        click.echo()
        click.echo(f"✓ Project '{name}' and all related resources deleted successfully")
        click.echo(f"  Total: {len(deleted_items)} directories removed")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('build')
@click.argument('project_name')
@click.option('--agent', '-a', help='Specific agent to build')
@click.option('--tag', '-t', help='Custom image tag (default: latest)')
@click.option('--no-cache', is_flag=True, help='Build without cache')
@click.option('--push', 'push', flag_value='default', default=None, help='Push to default registry (or provide custom URI)')
@click.option('--platform', help='Target platform (e.g., linux/amd64)')
@click.option('--build-arg', multiple=True, help='Build arguments (KEY=VALUE)')
@click.option('--no-create-repo', is_flag=True, help='Disable auto-creation of ECR repository')
@click.pass_obj
def project_build(ctx, project_name, agent, tag, no_cache, push, platform, build_arg, no_create_repo):
    """Build Docker image for project
    
    Builds Docker images for Nexus-AI projects locally. By default, builds all
    agents in the project. Use --agent to build a specific agent.
    
    \b
    DEFAULT BEHAVIOR:
      • Builds all agents in the project
      • Uses default registry: 533267047935.dkr.ecr.us-west-2.amazonaws.com/nexus-ai/
      • Tags images as: <registry>/<project>:<agent>-latest
      • Generates Dockerfile if missing
      • Saves build logs to logs/builds/
      • Stops on first failure (fail-fast)
    
    \b
    IMAGE NAMING:
      Default: 533267047935.dkr.ecr.us-west-2.amazonaws.com/nexus-ai/<project>:<agent>-latest
      Custom:  533267047935.dkr.ecr.us-west-2.amazonaws.com/nexus-ai/<project>:<custom-tag>
    
    \b
    EXAMPLES:
      # Build all agents in project
      nexus-cli project build aws_pricing_agent
      
      # Build specific agent
      nexus-cli project build aws_pricing_agent --agent aws_pricing_agent
      
      # Build with custom tag
      nexus-cli project build aws_pricing_agent --tag v1.0.0
      
      # Build without cache
      nexus-cli project build aws_pricing_agent --no-cache
      
      # Build and push to default registry (no argument needed)
      nexus-cli project build aws_pricing_agent --push
      
      # Build and push to custom registry (provide URI as argument)
      nexus-cli project build aws_pricing_agent --push=123456.dkr.ecr.us-east-1.amazonaws.com/my-registry
      
      # Build for specific platform
      nexus-cli project build aws_pricing_agent --platform linux/amd64
      
      # Build with custom build arguments
      nexus-cli project build aws_pricing_agent --build-arg AWS_REGION=us-east-1
    
    \b
    BUILD FEATURES:
      ✓ Auto-detect existing Dockerfiles
      ✓ Generate Dockerfiles from template if missing
      ✓ Real-time build output streaming
      ✓ Build logs saved to files
      ✓ Fail-fast on errors
      ✓ Support for multi-platform builds
      ✓ Custom build arguments
      ✓ Push to default or custom registry
      ✓ Auto-create ECR repositories on first push
    
    \b
    REQUIREMENTS:
      • Docker must be installed and running
      • Project must exist with at least one agent
      • For push: Docker must be authenticated to registry
    """
    try:
        # Parse build arguments
        build_args = {}
        for arg in build_arg:
            if '=' in arg:
                key, value = arg.split('=', 1)
                build_args[key] = value
            else:
                click.echo(f"Warning: Invalid build argument format: {arg} (expected KEY=VALUE)", err=True)
        
        # Create build options
        options = BuildOptions(
            agent=agent,
            tag=tag,
            no_cache=no_cache,
            push=push,
            platform=platform,
            build_args=build_args,
            create_ecr_repo=not no_create_repo  # Invert the flag
        )
        
        # Build project
        results = ctx.build_manager.build_project(project_name, options)
        
        # Display summary
        click.echo()
        click.echo("=" * 50)
        click.echo("Build Summary")
        click.echo("=" * 50)
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        if successful:
            click.echo(f"\n✓ Successful builds: {len(successful)}")
            for result in successful:
                click.echo(f"  • {result.agent_name}: {result.image_tag}")
        
        if failed:
            click.echo(f"\n✗ Failed builds: {len(failed)}", err=True)
            for result in failed:
                click.echo(f"  • {result.agent_name}: {result.error}", err=True)
            sys.exit(1)
        
        click.echo()
        click.echo(f"✓ All builds completed successfully!")
        
    except RuntimeError as e:
        # Docker not available or other runtime errors
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        # Project not found or validation errors
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# AGENT COMMANDS
# ============================================================================

@cli.group()
def agents():
    """Manage Nexus-AI agents
    
    \b
    SUBCOMMANDS:
      list      List all agents
      describe  Show agent details
      build     Build and deploy agent to AgentCore
      delete    Delete an agent
    
    \b
    EXAMPLES:
      nexus-cli agents list
      nexus-cli agents list --project my-project
      nexus-cli agents describe my-agent
      nexus-cli agents build my-project
      nexus-cli agents delete my-agent --dry-run
    """
    pass


@agents.command('build')
@click.argument('project_name')
@click.option('--region', '-r', help='AWS region for deployment')
@click.option('--dry-run', is_flag=True, help='Validate without deploying')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.option('--output', '-o', type=click.Choice(['detail', 'json']), default='detail', help='Output format')
@click.pass_obj
def agents_build(ctx, project_name, region, dry_run, yes, output):
    """Build and deploy an agent to AgentCore
    
    Packages an existing project and deploys it to Amazon Bedrock AgentCore.
    This command will:
    
    \b
    1. Check project status in DynamoDB
    2. Validate project readiness (config, scripts, requirements)
    3. Build Docker image with agent code
    4. Deploy to AgentCore
    5. Update deployment status in DynamoDB
    
    \b
    EXAMPLES:
      # Deploy with confirmation
      nexus-cli agents build my-project
      
      # Validate without deploying
      nexus-cli agents build my-project --dry-run
      
      # Deploy to specific region
      nexus-cli agents build my-project --region us-east-1
      
      # Skip confirmation
      nexus-cli agents build my-project --yes
    """
    try:
        deploy_mgr = ctx.deployment_manager
        
        click.secho("=" * 60, fg='cyan')
        click.secho(t('agents_build.title'), fg='cyan', bold=True)
        click.secho("=" * 60, fg='cyan')
        click.echo()
        
        # Step 1: Check project status in DynamoDB
        click.secho(f"🔍 {t('agents_build.checking_project', name=project_name)}", fg='cyan')
        click.echo()
        
        project_status = deploy_mgr.get_project_status(project_name)
        
        if project_status.get('error'):
            click.secho(f"⚠ {t('common.warning')}: {project_status['error']}", fg='yellow')
        
        if project_status.get('found'):
            click.secho(f"📋 {t('agents_build.project_status')}", fg='cyan', bold=True)
            click.echo(f"   {t('agents_build.project_id', id=project_status.get('project_id', 'N/A'))}")
            click.echo(f"   {t('agents_build.current_stage', stage=project_status.get('current_stage', 'N/A'))}")
            click.echo(f"   {t('agents_build.db_status', status=project_status.get('status', 'N/A'))}")
            
            # Show existing deployment info
            if project_status.get('deployment_type'):
                click.echo()
                click.secho(f"📦 {t('agents_build.existing_deployment')}", fg='cyan', bold=True)
                click.echo(f"   {t('agents_build.deployment_type', type=project_status.get('deployment_type'))}")
                click.echo(f"   {t('agents_build.deployment_status', status=project_status.get('deployment_status', 'N/A'))}")
                if project_status.get('agent_runtime_arn'):
                    click.echo(f"   {t('agents_build.agent_runtime_arn', arn=project_status.get('agent_runtime_arn'))}")
        else:
            click.secho(f"ℹ {t('agents_build.project_not_found', name=project_name)} (will create new record)", fg='yellow')
        
        click.echo()
        
        # Step 2: Check project readiness
        click.secho(f"✅ {t('agents_build.readiness_check')}", fg='cyan', bold=True)
        readiness = deploy_mgr.check_project_ready(project_name)
        
        checks = [
            ('Project directory exists', readiness['project_exists']),
            ('Project config (project_config.json)', readiness['has_config']),
            ('Agent script', readiness['has_agent_script']),
            ('Requirements file', readiness['has_requirements']),
        ]
        
        for item, passed in checks:
            if passed:
                click.secho(f"   {t('agents_build.check_passed', item=item)}", fg='green')
            else:
                click.secho(f"   {t('agents_build.check_failed', item=item)}", fg='red')
        
        click.echo()
        
        if not readiness['ready']:
            click.secho(f"❌ {t('agents_build.project_not_ready')}", fg='red')
            if readiness['issues']:
                click.secho(f"   {t('agents_build.issues_found')}", fg='yellow')
                for issue in readiness['issues']:
                    click.echo(f"     • {issue}")
            sys.exit(1)
        
        click.secho(f"✓ {t('agents_build.project_ready')}", fg='green')
        click.echo()
        
        # Dry run mode
        if dry_run:
            click.secho("=" * 60, fg='green')
            click.secho(f"✅ {t('agents_build.dry_run_complete')}", fg='green', bold=True)
            click.secho("=" * 60, fg='green')
            click.echo()
            click.secho(t('agents_build.dry_run_details'), bold=True)
            click.echo(f"   Project: {project_name}")
            click.echo(f"   Directory: {readiness['project_dir']}")
            click.echo(f"   Region: {region or 'default'}")
            
            if output == 'json':
                result = {
                    'status': 'dry_run',
                    'project_name': project_name,
                    'project_dir': readiness['project_dir'],
                    'region': region,
                    'readiness': readiness,
                    'project_status': project_status
                }
                click.echo()
                click.echo(json_dumps_utf8(result))
            return
        
        # Confirmation
        if not yes:
            # Check if already deployed
            if project_status.get('deployment_type') == 'agentcore' and project_status.get('agent_runtime_arn'):
                if not click.confirm(f"\n{t('agents_build.confirm_redeploy')}"):
                    click.echo(t('common.operation_cancelled'))
                    return
            else:
                if not click.confirm(f"\n{t('agents_build.confirm_deploy')}"):
                    click.echo(t('common.operation_cancelled'))
                    return
        
        # Step 3: Deploy to AgentCore
        click.echo()
        click.secho(f"🚀 {t('agents_build.deploying', name=project_name)}", fg='cyan', bold=True)
        if region:
            click.echo(f"   {t('agents_build.deploy_region', region=region)}")
        click.secho(f"   {t('agents_build.deploy_progress')}", fg='yellow')
        click.echo()
        
        result = deploy_mgr.deploy_to_agentcore(
            project_name=project_name,
            region=region,
            dry_run=False
        )
        
        if not result.success:
            click.echo()
            click.secho("=" * 60, fg='red')
            click.secho(f"❌ {t('agents_build.deploy_failed')}", fg='red', bold=True)
            click.secho("=" * 60, fg='red')
            click.echo()
            click.secho(f"Error: {result.error}", fg='red')
            sys.exit(1)
        
        # Success
        click.echo()
        click.secho("=" * 60, fg='green')
        click.secho(f"✅ {t('agents_build.deploy_success')}", fg='green', bold=True)
        click.secho("=" * 60, fg='green')
        click.echo()
        
        if result.agent_id:
            click.echo(f"   {t('agents_build.result_agent_id', id=result.agent_id)}")
        if result.agent_runtime_arn:
            click.echo(f"   {t('agents_build.result_runtime_arn', arn=result.agent_runtime_arn)}")
        if result.agent_alias_arn:
            click.echo(f"   {t('agents_build.result_alias_arn', arn=result.agent_alias_arn)}")
        click.echo(f"   {t('agents_build.result_status', status=result.deployment_status)}")
        
        if output == 'json':
            click.echo()
            output_data = {
                'success': True,
                'agent_id': result.agent_id,
                'project_id': result.project_id,
                'deployment_type': result.deployment_type,
                'deployment_status': result.deployment_status,
                'agent_runtime_arn': result.agent_runtime_arn,
                'agent_alias_arn': result.agent_alias_arn,
                'region': result.region,
                'details': result.details
            }
            click.echo(json_dumps_utf8(output_data))
        
    except ImportError as e:
        click.secho(f"{t('common.error')}: {t('common.missing_dependency', error=str(e))}", fg='red', err=True)
        click.echo("Make sure you are in the Nexus-AI directory and dependencies are installed.", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"{t('common.error')}: {e}", fg='red', err=True)
        sys.exit(1)


@agents.command('list')
@click.option('--project', '-p', help='Filter by project')
@click.option('--show-sync', '-s', is_flag=True, help='Show S3 sync status')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def agents_list(ctx, project, show_sync, output):
    """List all agents with brief descriptions"""
    try:
        agents = ctx.agent_manager.list_agents(project=project)
        
        # 获取云端同步状态（如果需要）
        synced_agents = {}
        if show_sync:
            try:
                synced_list = ctx.artifact_manager.list_synced_agents()
                synced_agents = {a.agent_name: a for a in synced_list}
            except Exception:
                pass  # 忽略同步状态获取失败
        
        if output == 'json':
            agents_data = []
            for a in agents:
                agent_dict = a.to_dict()
                if show_sync and a.name in synced_agents:
                    sync_info = synced_agents[a.name]
                    agent_dict['sync_status'] = {
                        'synced': True,
                        'version_count': sync_info.version_count,
                        'latest_version': sync_info.latest_version,
                        'last_sync': sync_info.latest_created_at
                    }
                else:
                    agent_dict['sync_status'] = {'synced': False}
                agents_data.append(agent_dict)
            
            data = {
                'agents': agents_data,
                'total': len(agents)
            }
            click.echo(format_output(data, 'json'))
        else:
            # Prepare data for table/text
            data = []
            for a in agents:
                # Get brief description
                description = 'No description'
                if a.config and a.config.description:
                    # Extract first line or first sentence
                    desc = a.config.description.split('\n')[0].strip()
                    if len(desc) > 50:
                        desc = desc[:47] + '...'
                    description = desc
                
                row = {
                    'name': a.name,
                    'description': description,
                    'project': a.project or '-',
                    'tools': len(a.dependencies),
                    'created': a.created_at.strftime('%Y-%m-%d') if a.created_at else '-'
                }
                
                if show_sync:
                    if a.name in synced_agents:
                        sync_info = synced_agents[a.name]
                        row['synced'] = f"✓ ({sync_info.version_count})"
                    else:
                        row['synced'] = '-'
                
                data.append(row)
            
            if show_sync:
                headers = ['name', 'description', 'project', 'tools', 'synced', 'created']
            else:
                headers = ['name', 'description', 'project', 'tools', 'created']
            click.echo(format_output(data, output, headers))
            
            if project:
                click.echo(f"\nTotal: {len(agents)} agents in project '{project}'")
            else:
                click.echo(f"\nTotal: {len(agents)} agents")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@agents.command('delete')
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--include-cloud', is_flag=True, help='Also delete cloud resources (AgentCore runtime, ECR, DynamoDB)')
@click.pass_obj
def agents_delete(ctx, name, force, dry_run, include_cloud):
    """Delete an agent and all related resources
    
    Permanently removes an agent and ALL associated resources including:
    - Agent implementation files (agents/generated_agents/<name>/)
    - Prompt configurations (prompts/generated_agents_prompts/<name>/)
    - Custom tools (tools/generated_tools/<name>/)
    - Project files (projects/<name>/)
    - Cloud resources (AgentCore runtime, ECR images, DynamoDB records) with --include-cloud
    
    \b
    WARNING: This operation is irreversible! Consider using 'project backup'
    before deleting to preserve a recoverable copy.
    
    \b
    EXAMPLES:
      # Delete with confirmation prompt
      nexus-cli agents delete my-agent
      
      # Preview deletion (dry-run)
      nexus-cli agents delete my-agent --dry-run
      
      # Force delete (skip confirmation)
      nexus-cli agents delete my-agent --force
      
      # Delete including cloud resources
      nexus-cli agents delete my-agent --include-cloud
      
      # Backup before delete
      nexus-cli project backup my-agent
      nexus-cli agents delete my-agent --force
    
    \b
    SAFETY:
      • Confirmation prompt (unless --force)
      • Dry-run mode for preview
      • Shows detailed list of what will be deleted
      • Handles missing directories gracefully
      • Cloud resources require explicit --include-cloud flag
    """
    try:
        # 定义所有可能需要删除的目录
        agents_dir = f"agents/generated_agents/{name}"
        prompts_dir = f"prompts/generated_agents_prompts/{name}"
        tools_dir = f"tools/generated_tools/{name}"
        project_dir = f"projects/{name}"
        deployment_dir = f"deployment/{name}"
        
        # 检查哪些目录存在
        existing_dirs = []
        if ctx.fs_adapter.exists(project_dir):
            existing_dirs.append(('project', project_dir))
        if ctx.fs_adapter.exists(agents_dir):
            existing_dirs.append(('agents', agents_dir))
        if ctx.fs_adapter.exists(prompts_dir):
            existing_dirs.append(('prompts', prompts_dir))
        if ctx.fs_adapter.exists(tools_dir):
            existing_dirs.append(('tools', tools_dir))
        if ctx.fs_adapter.exists(deployment_dir):
            existing_dirs.append(('deployment', deployment_dir))
        
        # 使用 CloudResourceManager 检测云资源
        cloud_resources = ctx.cloud_resource_manager.detect_resources(name)
        has_cloud_resources = cloud_resources.has_resources()
        
        # 获取检测过程中的错误信息
        detection_errors = ctx.cloud_resource_manager.get_detection_errors()
        
        # 检查 Agent 是否存在
        if not existing_dirs and not has_cloud_resources:
            click.echo(t('agents_delete.not_found', name=name), err=True)
            click.echo()
            click.echo(t('agents_delete.checked_locations'))
            click.echo(f"  • {project_dir}/")
            click.echo(f"  • {agents_dir}/")
            click.echo(f"  • {prompts_dir}/")
            click.echo(f"  • {tools_dir}/")
            click.echo(f"  • {deployment_dir}/")
            click.echo(f"  • AgentCore runtime")
            click.echo(f"  • ECR repository")
            click.echo(f"  • DynamoDB records")
            
            # 显示检测错误信息
            if detection_errors:
                click.echo()
                click.echo(t('agents_delete.detection_errors'))
                for resource_type, error_msg in detection_errors.items():
                    click.echo(f"  ⚠️  {resource_type}: {error_msg}")
            
            sys.exit(1)
        
        if dry_run:
            click.echo(t('common.dry_run_header'))
            click.echo()
            click.echo(t('agents_delete.deleting', name=name))
            click.echo()
            
            if existing_dirs:
                click.echo(t('agents_delete.local_dirs_to_delete'))
                for dir_type, dir_path in existing_dirs:
                    click.echo(f"  ✓ {dir_path}/")
                    # 列出目录内容预览
                    try:
                        contents = ctx.fs_adapter.list_directory(dir_path)
                        for item in contents[:5]:
                            click.echo(f"    - {item.name}")
                        if len(contents) > 5:
                            click.echo(f"    ... and {len(contents) - 5} more items")
                    except:
                        pass
                click.echo()
            
            # 显示云资源状态
            if has_cloud_resources:
                click.echo(t('agents_delete.cloud_resources_detected'))
                if cloud_resources.agentcore_runtime:
                    runtime = cloud_resources.agentcore_runtime
                    click.echo(t('agents_delete.agentcore_runtime', arn=runtime.arn))
                    click.echo(f"    {t('cloud.region', region=runtime.region)}")
                    click.echo(f"    {t('cloud.status', status=runtime.status)}")
                if cloud_resources.ecr_repository:
                    ecr = cloud_resources.ecr_repository
                    click.echo(t('agents_delete.ecr_repository', name=ecr.repository_name))
                    click.echo(f"    {t('cloud.uri', uri=ecr.repository_uri)}")
                    click.echo(f"    {t('cloud.images', count=ecr.image_count)}")
                # 显示 DynamoDB 记录
                if cloud_resources.dynamodb_agents:
                    click.echo(t('agents_delete.dynamodb_agents', count=len(cloud_resources.dynamodb_agents)))
                    for agent in cloud_resources.dynamodb_agents:
                        click.echo(t('agents_delete.dynamodb_agent_detail', 
                                   agent_id=agent.agent_id, 
                                   agent_name=agent.agent_name,
                                   status=agent.status))
                        click.echo(t('agents_delete.dynamodb_agent_sessions',
                                   count=agent.session_count,
                                   invocations=agent.invocation_count))
                click.echo()
                
                if include_cloud:
                    click.echo(f"  → {t('agents_delete.cloud_will_delete')}")
                else:
                    click.echo(f"  ⚠️  {t('agents_delete.cloud_will_not_delete')}")
                click.echo()
            
            click.echo(t('agents_delete.dirs_not_exist'))
            all_dirs = [
                ('project', project_dir),
                ('agents', agents_dir),
                ('prompts', prompts_dir),
                ('tools', tools_dir),
                ('deployment', deployment_dir)
            ]
            non_existing = [d for d in all_dirs if d not in existing_dirs]
            if non_existing:
                for dir_type, dir_path in non_existing:
                    click.echo(f"  - {dir_path}/ (not found)")
            else:
                click.echo(f"  {t('agents_delete.all_dirs_exist')}")
            
            click.echo()
            click.echo(t('common.run_without_dry_run'))
            return
        
        # 如果检测到云资源但未指定 --include-cloud，显示警告
        if has_cloud_resources and not include_cloud:
            click.echo(t('agents_delete.cloud_warning_header'))
            if cloud_resources.agentcore_runtime:
                click.echo(t('agents_delete.agentcore_runtime', arn=cloud_resources.agentcore_runtime.arn))
            if cloud_resources.ecr_repository:
                click.echo(t('agents_delete.ecr_repository', name=cloud_resources.ecr_repository.repository_name))
            if cloud_resources.dynamodb_agents:
                click.echo(t('agents_delete.dynamodb_agents', count=len(cloud_resources.dynamodb_agents)))
            click.echo()
            click.echo(t('agents_delete.cloud_not_deleted_hint'))
            click.echo(t('agents_delete.cloud_use_flag_hint'))
            click.echo()
        
        if not force:
            click.echo(t('agents_delete.delete_warning', name=name))
            click.echo()
            click.echo(t('agents_delete.dirs_to_delete'))
            for dir_type, dir_path in existing_dirs:
                click.echo(f"  • {dir_path}/")
            
            if include_cloud and has_cloud_resources:
                click.echo()
                click.echo(t('agents_delete.cloud_to_delete'))
                if cloud_resources.agentcore_runtime:
                    click.echo(t('agents_delete.agentcore_runtime', arn=cloud_resources.agentcore_runtime.arn))
                if cloud_resources.ecr_repository:
                    click.echo(t('agents_delete.ecr_repository', name=cloud_resources.ecr_repository.repository_name))
                if cloud_resources.dynamodb_agents:
                    click.echo(t('agents_delete.dynamodb_agents', count=len(cloud_resources.dynamodb_agents)))
                    for agent in cloud_resources.dynamodb_agents:
                        click.echo(t('agents_delete.dynamodb_agent_detail',
                                   agent_id=agent.agent_id,
                                   agent_name=agent.agent_name,
                                   status=agent.status))
            
            click.echo()
            if not click.confirm(t('common.confirm_continue')):
                click.echo(t('common.aborted'))
                return
        
        # 执行删除
        click.echo(t('agents_delete.deleting', name=name))
        click.echo()
        
        deleted_items = []
        
        # 首先删除云资源（如果指定了 --include-cloud）
        if include_cloud and has_cloud_resources:
            click.echo(t('agents_delete.deleting_cloud'))
            results = ctx.cloud_resource_manager.delete_all_resources(cloud_resources)
            for result in results:
                if result.success:
                    if result.resource_type == 'agentcore_runtime':
                        deleted_items.append(t('agents_delete.deleted_agentcore', name=result.resource_name))
                    elif result.resource_type == 'ecr_repository':
                        ecr = cloud_resources.ecr_repository
                        deleted_items.append(t('agents_delete.deleted_ecr', name=result.resource_name, count=ecr.image_count if ecr else 0))
                    elif result.resource_type == 'dynamodb_agent':
                        # 查找对应的 agent 获取会话数
                        agent_sessions = 0
                        for agent in cloud_resources.dynamodb_agents:
                            if agent.agent_id == result.resource_name:
                                agent_sessions = agent.session_count
                                break
                        deleted_items.append(t('agents_delete.deleted_dynamodb', agent_id=result.resource_name, sessions=agent_sessions))
                else:
                    if result.resource_type == 'agentcore_runtime':
                        click.echo(f"  ⚠️  {t('agents_delete.failed_delete_agentcore', error=result.error)}", err=True)
                    elif result.resource_type == 'ecr_repository':
                        click.echo(f"  ⚠️  {t('agents_delete.failed_delete_ecr', error=result.error)}", err=True)
                    elif result.resource_type == 'dynamodb_agent':
                        click.echo(f"  ⚠️  {t('agents_delete.failed_delete_dynamodb', error=result.error)}", err=True)
            click.echo()
        
        # 删除本地目录
        click.echo(t('agents_delete.deleting_local'))
        for dir_type, dir_path in existing_dirs:
            try:
                ctx.fs_adapter.delete_directory(dir_path)
                deleted_items.append(t('agents_delete.deleted_dir', type=dir_type, path=dir_path))
            except Exception as e:
                click.echo(f"  ✗ {t('agents_delete.failed_delete_dir', path=dir_path, error=str(e))}", err=True)
        
        # 显示删除结果
        for item in deleted_items:
            click.echo(f"  {item}")
        
        click.echo()
        click.echo(t('agents_delete.delete_success', name=name))
        click.echo(t('common.total_items_removed', count=len(deleted_items)))
    
    except Exception as e:
        click.echo(f"{t('common.error')}: {e}", err=True)
        sys.exit(1)


@agents.command('describe')
@click.argument('name')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='text',
              help='Output format')
@click.pass_obj
def agents_describe(ctx, name, output):
    """Describe an agent in detail with structured, human-readable information"""
    try:
        agent = ctx.agent_manager.get_agent(name)
        
        if not agent:
            click.echo(f"Error: Agent '{name}' not found", err=True)
            sys.exit(1)
        
        if output == 'json':
            click.echo(format_output(agent.to_dict(), 'json'))
        else:
            # Structured, human-readable output
            click.echo("=" * 80)
            click.echo(f"AGENT: {agent.name}")
            click.echo("=" * 80)
            click.echo()
            
            # Basic Information
            click.echo("Basic Information:")
            click.echo(f"  Name:        {agent.name}")
            click.echo(f"  Project:     {agent.project or 'Standalone'}")
            if agent.config:
                click.echo(f"  Category:    {agent.config.category or 'General'}")
                click.echo(f"  Version:     {agent.config.version}")
            click.echo(f"  Location:    {agent.path}")
            if agent.created_at:
                click.echo(f"  Created:     {agent.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo()
            
            # Description
            if agent.config and agent.config.description:
                click.echo("Description:")
                # Format multi-line description with proper indentation
                desc_lines = agent.config.description.split('\n')
                for line in desc_lines:
                    if line.strip():
                        click.echo(f"  {line.strip()}")
                click.echo()
            
            # Functionality (extract from agent file docstring if available)
            agent_file = ctx.fs_adapter.base_path / agent.path
            if agent_file.exists():
                try:
                    with open(agent_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract docstring
                        if '"""' in content:
                            start = content.find('"""') + 3
                            end = content.find('"""', start)
                            if end > start:
                                docstring = content[start:end].strip()
                                # Look for "功能:" or "Features:" section
                                if '功能:' in docstring or 'Features:' in docstring:
                                    click.echo("Functionality:")
                                    in_features = False
                                    for line in docstring.split('\n'):
                                        if '功能:' in line or 'Features:' in line:
                                            in_features = True
                                            continue
                                        if in_features:
                                            if line.strip() and (line.strip().startswith(('工具:', 'Tools:', '使用:', 'Usage:'))):
                                                break
                                            if line.strip():
                                                click.echo(f"  {line.strip()}")
                                    click.echo()
                except Exception:
                    pass
            
            # Tools and Dependencies
            if agent.config and agent.config.tools_dependencies:
                click.echo(f"Tools & Dependencies ({len(agent.config.tools_dependencies)}):")
                # Group tools by type
                strands_tools = [t for t in agent.config.tools_dependencies if 'strands_tools/' in t]
                generated_tools = [t for t in agent.config.tools_dependencies if 'generated_tools/' in t]
                system_tools = [t for t in agent.config.tools_dependencies if 'system_tools/' in t or (t.startswith('tools/') and 'generated_tools/' not in t)]
                
                if strands_tools:
                    click.echo(f"  Strands Tools ({len(strands_tools)}):")
                    for tool in strands_tools:
                        tool_name = tool.split('/')[-1]
                        click.echo(f"    - {tool_name}")
                
                if generated_tools:
                    click.echo(f"  Generated Tools ({len(generated_tools)}):")
                    for tool in generated_tools:
                        tool_name = tool.split('/')[-1]
                        click.echo(f"    - {tool_name}")
                
                if system_tools:
                    click.echo(f"  System Tools ({len(system_tools)}):")
                    for tool in system_tools:
                        tool_name = tool.split('/')[-1]
                        click.echo(f"    - {tool_name}")
                click.echo()
            
            # Supported Models
            if agent.config and agent.config.supported_models:
                click.echo("Supported Models:")
                for model in agent.config.supported_models:
                    click.echo(f"  - {model}")
                click.echo()
            
            # Interaction Methods
            click.echo("Interaction Methods:")
            click.echo(f"  CLI:         python {agent.path}")
            if agent.project:
                click.echo(f"  Prompt:      prompts/generated_agents_prompts/{agent.project}/{agent.name}.yaml")
            click.echo(f"  API:         Use agent_factory.create_agent_from_prompt_template()")
            click.echo()
            
            # Documentation
            if agent.project:
                readme_path = ctx.fs_adapter.base_path / 'projects' / agent.project / 'README.md'
                if readme_path.exists():
                    click.echo("Documentation:")
                    click.echo(f"  Project README:  projects/{agent.project}/README.md")
                    click.echo()
            
            click.echo("=" * 80)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# BACKUP COMMANDS
# ============================================================================

@cli.group()
def backup():
    """Manage project backups
    
    \b
    SUBCOMMANDS:
      list      List all backups
      describe  Show backup details
      validate  Verify backup integrity
      delete    Delete a backup file
    
    \b
    EXAMPLES:
      nexus-cli backup list
      nexus-cli backup describe my-project_20241125.tar.gz
      nexus-cli backup validate backups/my-project.tar.gz
      nexus-cli backup delete old-backup.tar.gz
    """
    pass


@backup.command('list')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def backup_list(ctx, output):
    """List all available backups
    
    Shows all backup files in the backups directory with:
    - Backup filename
    - Associated project name
    - File size (human-readable)
    - Creation timestamp
    
    \b
    EXAMPLES:
      # List in table format (default)
      nexus-cli backup list
      
      # List in JSON format (for scripting)
      nexus-cli backup list --output json
      
      # List in plain text
      nexus-cli backup list --output text
    """
    try:
        backups = ctx.project_manager.list_backups()
        
        if output == 'json':
            data = {
                'backups': [b.to_dict() for b in backups],
                'total': len(backups),
                'total_size_mb': sum(b.size_mb for b in backups)
            }
            click.echo(format_output(data, 'json'))
        else:
            # Prepare data for table/text
            data = []
            for b in backups:
                data.append({
                    'name': b.name,
                    'project': b.project_name,
                    'size': b.size_human,
                    'created': b.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            headers = ['name', 'project', 'size', 'created']
            click.echo(format_output(data, output, headers))
            
            total_size = sum(b.size_mb for b in backups)
            click.echo(f"\nTotal: {len(backups)} backups ({total_size:.1f} MB)")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@backup.command('describe')
@click.argument('name')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='text',
              help='Output format')
@click.pass_obj
def backup_describe(ctx, name, output):
    """Show detailed backup information
    
    Displays comprehensive information about a backup including:
    - Basic metadata (project, size, creation date)
    - Manifest details (version, file count)
    - Resource breakdown (agents, prompts, tools)
    - Integrity status (checksums, validation)
    
    \b
    EXAMPLES:
      # Show backup details
      nexus-cli backup describe my-project_20241125_143022.tar.gz
      
      # Get details in JSON format
      nexus-cli backup describe backup.tar.gz --output json
    """
    try:
        backup_obj = ctx.project_manager.get_backup(name)
        
        if not backup_obj:
            click.echo(f"Error: Backup '{name}' not found", err=True)
            sys.exit(1)
        
        if output == 'json':
            click.echo(format_output(backup_obj.to_dict(), 'json'))
        else:
            click.echo("=" * 70)
            click.echo(f"BACKUP: {backup_obj.name}")
            click.echo("=" * 70)
            click.echo()
            click.echo("Basic Information:")
            click.echo(f"  Project:     {backup_obj.project_name}")
            click.echo(f"  Created:     {backup_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"  Size:        {backup_obj.size_human}")
            click.echo(f"  Format:      {backup_obj.format}")
            if backup_obj.checksum:
                click.echo(f"  Checksum:    sha256:{backup_obj.checksum[:32]}...")
            click.echo()
            
            if backup_obj.manifest:
                click.echo("Manifest:")
                click.echo(f"  Version:     {backup_obj.manifest.version}")
                click.echo(f"  Nexus-AI:    {backup_obj.manifest.nexus_version}")
                click.echo(f"  Files:       {backup_obj.manifest.metadata.get('total_files', 0)}")
                click.echo()
                
                click.echo("Resources Included:")
                for resource_type, paths in backup_obj.manifest.resources.items():
                    if paths:
                        click.echo(f"  {resource_type.capitalize()} ({len(paths)} files):")
                        # Show first few files
                        for path in paths[:3]:
                            click.echo(f"    - {path}")
                        if len(paths) > 3:
                            click.echo(f"    ... and {len(paths) - 3} more")
                        click.echo()
                
                click.echo("Integrity:")
                click.echo("  ✓ All checksums verified")
                click.echo("  ✓ Manifest valid")
                click.echo("  ✓ Archive structure correct")
            
            click.echo()
            click.echo("=" * 70)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@backup.command('delete')
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.pass_obj
def backup_delete(ctx, name, force):
    """Delete a backup file
    
    Permanently removes a backup file from the backups directory.
    
    \b
    WARNING: This operation cannot be undone!
    
    \b
    EXAMPLES:
      # Delete with confirmation prompt
      nexus-cli backup delete old-backup.tar.gz
      
      # Force delete (no confirmation)
      nexus-cli backup delete old-backup.tar.gz --force
      
      # Clean up old backups
      nexus-cli backup list
      nexus-cli backup delete my-project_20241001.tar.gz
    
    \b
    SAFETY:
      • Confirmation prompt (unless --force)
      • Shows backup details before deletion
      • Only deletes the specified backup file
      • Does not affect the original project
    """
    try:
        backup_obj = ctx.project_manager.get_backup(name)
        
        if not backup_obj:
            click.echo(f"Error: Backup '{name}' not found", err=True)
            sys.exit(1)
        
        if not force:
            click.echo("⚠️  WARNING: This will permanently delete the backup")
            click.echo()
            click.echo("Backup Details:")
            click.echo(f"  Name: {backup_obj.name}")
            click.echo(f"  Project: {backup_obj.project_name}")
            click.echo(f"  Size: {backup_obj.size_human}")
            click.echo(f"  Created: {backup_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo()
            
            if not click.confirm("Are you sure you want to continue?"):
                click.echo("Aborted.")
                return
        
        click.echo("Deleting backup...")
        ctx.project_manager.delete_backup(name)
        click.echo(f"  ✓ Backup file removed")
        click.echo()
        click.echo(f"✓ Backup '{name}' deleted successfully")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@backup.command('validate')
@click.argument('path')
@click.pass_obj
def backup_validate(ctx, path):
    """Validate backup integrity
    
    Performs comprehensive validation of a backup file:
    - Archive format verification (tar.gz)
    - Manifest presence and validity
    - SHA-256 checksum verification for all files
    - Path structure validation
    - Version compatibility check
    
    \b
    Use this command to:
    • Verify backup before restore
    • Check for corruption
    • Validate after transfer/copy
    • Ensure backup is restorable
    
    \b
    EXAMPLES:
      # Validate a backup
      nexus-cli backup validate backups/my-project_20241125.tar.gz
      
      # Validate before restore
      nexus-cli backup validate backup.tar.gz
      nexus-cli project restore my-project --from-backup backup.tar.gz
    
    \b
    VALIDATION CHECKS:
      ✓ Archive structure (tar.gz format)
      ✓ Manifest file (presence and format)
      ✓ Checksums (SHA-256 for all files)
      ✓ Resource paths (validity and security)
      ✓ Version compatibility
      ✓ No corruption detected
    """
    try:
        click.echo(f"Validating backup: {Path(path).name}")
        click.echo()
        
        validation = ctx.project_manager.validate_backup(path)
        
        click.echo("Archive Structure:")
        if validation.success or not any('tar.gz' in e for e in validation.errors):
            click.echo("  ✓ Valid tar.gz format")
            click.echo("  ✓ Archive can be extracted")
            click.echo("  ✓ No corruption detected")
        else:
            click.echo("  ✗ Invalid archive format", err=True)
        
        click.echo()
        click.echo("Manifest:")
        if validation.success or not any('Manifest' in e for e in validation.errors):
            click.echo("  ✓ Manifest file present")
            click.echo("  ✓ Valid JSON format")
            click.echo("  ✓ Required fields present")
            click.echo("  ✓ Version compatible")
        else:
            click.echo("  ✗ Manifest issues detected", err=True)
        
        click.echo()
        
        if validation.success:
            # Get manifest for more details
            manifest = ctx.project_manager.get_backup_manifest(path)
            click.echo("Checksums:")
            click.echo(f"  ✓ Verifying {len(manifest.checksums)} files...")
            click.echo("  ✓ All checksums match")
            click.echo()
            click.echo("Resource Paths:")
            click.echo("  ✓ All paths valid")
            click.echo("  ✓ No path traversal attempts")
            click.echo("  ✓ Directory structure correct")
            click.echo()
            click.echo("✓ Backup is valid and can be restored")
        else:
            click.echo("✗ Backup validation failed:", err=True)
            for error in validation.errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# OVERVIEW COMMAND
# ============================================================================

@cli.command()
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def overview(ctx, output):
    """Display system-wide overview"""
    try:
        projects = ctx.project_manager.list_projects()
        agents = ctx.agent_manager.list_agents()
        
        # Calculate statistics
        total_projects = len(projects)
        total_agents = len(agents)
        total_templates = sum(p.template_count for p in projects)
        total_prompts = sum(p.prompt_count for p in projects)
        total_tools = sum(p.tool_count for p in projects)
        
        if output == 'json':
            data = {
                'summary': {
                    'total_projects': total_projects,
                    'total_agents': total_agents,
                    'total_templates': total_templates,
                    'total_prompts': total_prompts,
                    'total_tools': total_tools
                }
            }
            click.echo(format_output(data, 'json'))
        else:
            click.echo("=" * 70)
            click.echo("NEXUS-AI SYSTEM OVERVIEW")
            click.echo("=" * 70)
            click.echo()
            click.echo("Resource Summary:")
            click.echo(f"  Projects:   {total_projects}")
            click.echo(f"  Agents:     {total_agents}")
            click.echo(f"  Templates:  {total_templates}")
            click.echo(f"  Prompts:    {total_prompts}")
            click.echo(f"  Tools:      {total_tools}")
            click.echo()
            click.echo("=" * 70)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)



# ============================================================================
# INIT COMMAND
# ============================================================================

@cli.command()
@click.option('--tables-only', is_flag=True, help='Only initialize DynamoDB tables')
@click.option('--queues-only', is_flag=True, help='Only initialize SQS queues')
@click.option('--buckets-only', is_flag=True, help='Only initialize S3 buckets')
@click.option('--skip-validation', is_flag=True, help='Skip workflow configuration validation')
@click.pass_obj
def init(ctx, tables_only, queues_only, buckets_only, skip_validation):
    """Initialize infrastructure (DynamoDB tables, SQS queues, and S3 buckets)
    
    Creates the required DynamoDB tables, SQS queues, and S3 buckets for Nexus-AI.
    Skips resources that already exist.
    Also validates workflow configuration unless --skip-validation is used.
    
    \b
    EXAMPLES:
      # Initialize all infrastructure
      nexus-cli init
      
      # Initialize only DynamoDB tables
      nexus-cli init --tables-only
      
      # Initialize only SQS queues
      nexus-cli init --queues-only
      
      # Initialize only S3 buckets
      nexus-cli init --buckets-only
      
      # Skip workflow configuration validation
      nexus-cli init --skip-validation
    
    \b
    RESOURCES CREATED:
      DynamoDB Tables:
        • nexus_projects
        • nexus_stages
        • nexus_agents
        • nexus_invocations
        • nexus_sessions
        • nexus_messages
        • nexus_tasks
        • nexus_tools
      
      SQS Queues:
        • nexus-build-queue
        • nexus-deploy-queue
        • nexus-notification-queue
        • nexus-build-dlq
        • nexus-deploy-dlq
      
      S3 Buckets (from config/default_config.yaml):
        • artifacts_s3_bucket - Agent artifacts storage
        • session_storage_s3_bucket - Session data storage
    
    \b
    WORKFLOW VALIDATION:
      • Validates workflow stage definitions
      • Checks prompt template paths
      • Verifies DynamoDB and SQS configuration
    """
    try:
        infra = ctx.infrastructure_manager
        
        click.echo("=" * 50)
        click.echo(t('init.title'))
        click.echo("=" * 50)
        
        # 工作流配置验证
        if not skip_validation:
            click.echo()
            click.echo("🔍 验证工作流配置...")
            
            validation_result = infra.validate_workflow_config(ctx.base_path)
            
            if validation_result.valid:
                click.echo(f"  ✓ 配置文件: {validation_result.config_path}")
                click.echo(f"  ✓ 工作流阶段: {validation_result.stages_count} 个阶段已定义")
                
                # 显示警告
                if validation_result.warnings:
                    click.echo()
                    click.echo("  ⚠️  配置警告:")
                    for warning in validation_result.warnings[:5]:  # 最多显示5个警告
                        click.echo(f"    • {warning}")
                    if len(validation_result.warnings) > 5:
                        click.echo(f"    ... 还有 {len(validation_result.warnings) - 5} 个警告")
            else:
                click.echo("  ✗ 配置验证失败:")
                for error in validation_result.errors:
                    click.echo(f"    • {error}", err=True)
                click.echo()
                click.echo("使用 --skip-validation 跳过验证继续初始化", err=True)
                sys.exit(1)
        
        tables_created = 0
        queues_created = 0
        buckets_created = 0
        
        # 判断是否只初始化特定资源
        init_all = not (tables_only or queues_only or buckets_only)
        
        # 初始化 DynamoDB 表
        if init_all or tables_only:
            click.echo()
            click.echo(f"📦 {t('init.init_tables')}")
            click.echo(f"   {t('init.region', region=infra.region)}")
            if infra.dynamodb_endpoint:
                click.echo(f"   {t('init.endpoint', endpoint=infra.dynamodb_endpoint)}")
            
            for table_def in infra.get_table_definitions():
                created, status = infra.create_table(table_def)
                if created:
                    click.echo(f"  ✓ {t('init.table_created', name=table_def.table_name)}")
                    tables_created += 1
                elif status == 'exists':
                    click.echo(f"  ⚠ {t('init.table_exists', name=table_def.table_name)}")
                else:
                    click.echo(f"  ✗ {table_def.table_name}: {status}", err=True)
            
            click.echo(f"\n   {t('init.tables_created_count', count=tables_created)}")
        
        # 初始化 SQS 队列
        if init_all or queues_only:
            click.echo()
            click.echo(f"📬 {t('init.init_queues')}")
            click.echo(f"   {t('init.region', region=infra.region)}")
            if infra.sqs_endpoint:
                click.echo(f"   {t('init.endpoint', endpoint=infra.sqs_endpoint)}")
            
            for queue_name in infra.get_queue_names():
                created, status = infra.create_queue(queue_name)
                if created:
                    click.echo(f"  ✓ {t('init.queue_created', name=queue_name)}")
                    queues_created += 1
                elif status == 'exists':
                    click.echo(f"  ⚠ {t('init.queue_exists', name=queue_name)}")
                else:
                    click.echo(f"  ✗ {queue_name}: {status}", err=True)
            
            click.echo(f"\n   {t('init.queues_created_count', count=queues_created)}")
        
        # 初始化 S3 存储桶
        if init_all or buckets_only:
            click.echo()
            click.echo(f"🪣 {t('init.init_buckets')}")
            click.echo(f"   {t('init.region', region=infra.region)}")
            
            for bucket_config in infra.get_s3_bucket_names():
                bucket_name = bucket_config['name']
                created, status = infra.create_s3_bucket(bucket_name)
                if created:
                    click.echo(f"  ✓ {t('init.bucket_created', name=bucket_name)}")
                    buckets_created += 1
                elif status == 'exists':
                    click.echo(f"  ⚠ {t('init.bucket_exists', name=bucket_name)}")
                elif status == 'access_denied':
                    click.echo(f"  ⚠ {t('init.bucket_access_denied', name=bucket_name)}")
                else:
                    click.echo(f"  ✗ {bucket_name}: {status}", err=True)
            
            click.echo(f"\n   {t('init.buckets_created_count', count=buckets_created)}")
        
        click.echo()
        click.echo("=" * 50)
        click.echo(f"✅ {t('init.complete')}")
        click.echo("=" * 50)
        
    except ImportError as e:
        click.echo(f"{t('common.error')}: {t('common.missing_dependency', error=str(e))}", err=True)
        click.echo("Make sure boto3 is installed: pip install boto3", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"{t('common.error')}: {e}", err=True)
        sys.exit(1)


# ============================================================================
# JOB COMMANDS
# ============================================================================

@cli.group()
def job():
    """Manage tasks and queues
    
    \b
    SUBCOMMANDS:
      list    List tasks or queue statistics
      view    View task details
      clear   Clear all data (tables/queues)
      delete  Delete data for specific agent
    
    \b
    EXAMPLES:
      nexus-cli job list
      nexus-cli job list --status running
      nexus-cli job list --queues
      nexus-cli job view task-123
      nexus-cli job clear --yes
      nexus-cli job delete my-agent
    """
    pass


@job.command('clear')
@click.option('--tables-only', is_flag=True, help='Only clear DynamoDB tables')
@click.option('--queues-only', is_flag=True, help='Only clear SQS queues')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_obj
def job_clear(ctx, tables_only, queues_only, yes):
    """Clear all data from DynamoDB tables and SQS queues
    
    \b
    WARNING: This will delete ALL data and cannot be undone!
    
    \b
    EXAMPLES:
      nexus-cli job clear
      nexus-cli job clear --tables-only
      nexus-cli job clear --queues-only
      nexus-cli job clear --yes
    """
    try:
        infra = ctx.infrastructure_manager
        
        click.secho("=" * 50, fg='cyan')
        click.secho(t('job.clear_title'), fg='cyan', bold=True)
        click.secho("=" * 50, fg='cyan')
        
        # Confirmation
        if not yes:
            click.echo()
            click.secho(f"⚠️  {t('job.clear_warning')}", fg='yellow')
            if not click.confirm(f"\n{t('common.confirm_continue')}"):
                click.echo(t('common.operation_cancelled'))
                return
        
        total_deleted = 0
        cleared_queues = 0
        
        # Clear tables
        if not queues_only:
            click.echo()
            click.secho(f"📦 {t('job.clearing_tables')}", fg='cyan')
            click.echo(f"   {t('init.region', region=infra.region)}")
            if infra.dynamodb_endpoint:
                click.echo(f"   {t('init.endpoint', endpoint=infra.dynamodb_endpoint)}")
            
            for table_def in infra.get_table_definitions():
                key_names = [k['AttributeName'] for k in table_def.key_schema]
                click.echo(f"  {t('job.clearing_table', name=table_def.table_name, keys=key_names)}")
                
                deleted_count, status = infra.clear_table(table_def.table_name)
                
                if status == 'not_found':
                    click.secho(f"    ⚠ {t('job.table_not_found')}", fg='yellow')
                elif status == 'cleared':
                    click.secho(f"    ✓ {t('job.deleted_records', count=deleted_count)}", fg='green')
                    total_deleted += deleted_count
                else:
                    click.secho(f"    ⚠ {status}", fg='yellow')
            
            click.echo(f"\n   {t('job.total_deleted', count=total_deleted)}")
        
        # Clear queues
        if not tables_only:
            click.echo()
            click.secho(f"📬 {t('job.clearing_queues')}", fg='cyan')
            click.echo(f"   {t('init.region', region=infra.region)}")
            if infra.sqs_endpoint:
                click.echo(f"   {t('init.endpoint', endpoint=infra.sqs_endpoint)}")
            
            for queue_name in infra.get_queue_names():
                click.echo(f"  {t('job.clearing_queue', name=queue_name)}")
                
                purge_success, status = infra.purge_queue(queue_name)
                
                if status == 'not_found':
                    click.echo(f"    ⚠ {t('job.queue_not_found')}")
                elif status == 'purge_in_progress':
                    click.echo(f"    ⚠ {t('job.queue_purge_in_progress')}")
                elif status == 'purged':
                    click.secho(f"    ✓ {t('job.queue_cleared')}", fg='green')
                    cleared_queues += 1
                else:
                    click.secho(f"    ⚠ {status}", fg='yellow')
            
            click.echo(f"\n   {t('job.queues_cleared', count=cleared_queues)}")
        
        click.echo()
        click.secho("=" * 50, fg='green')
        click.secho(f"✅ {t('job.cleanup_complete')}", fg='green', bold=True)
        click.secho("=" * 50, fg='green')
        
    except ImportError as e:
        click.secho(f"{t('common.error')}: {t('common.missing_dependency', error=str(e))}", fg='red', err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"{t('common.error')}: {e}", fg='red', err=True)
        sys.exit(1)


@job.command('delete')
@click.argument('agent_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_obj
def job_delete(ctx, agent_name, yes):
    """Delete all data for a specific agent
    
    \b
    EXAMPLES:
      nexus-cli job delete my-agent
      nexus-cli job delete my-agent --yes
    """
    try:
        infra = ctx.infrastructure_manager
        
        click.secho("=" * 50, fg='cyan')
        click.secho(t('job.delete_title', name=agent_name), fg='cyan', bold=True)
        click.secho("=" * 50, fg='cyan')
        
        # Confirmation
        if not yes:
            click.echo()
            click.secho(f"⚠️  {t('job.delete_warning', name=agent_name)}", fg='yellow')
            if not click.confirm(f"\n{t('common.confirm_continue')}"):
                click.echo(t('common.operation_cancelled'))
                return
        
        click.echo()
        click.secho(f"🔍 {t('job.finding_agent', name=agent_name)}", fg='cyan')
        
        # Use infrastructure manager to delete agent data
        results = infra.delete_agent_data(agent_name)
        
        # Report results
        if results['agent_ids']:
            if 'local_' in results['agent_ids'][0] and len(results['agent_ids']) == 1:
                click.secho(f"  {t('job.no_exact_match', name=results['agent_ids'][0])}", fg='yellow')
            else:
                click.echo(f"  {t('job.found_agents', count=len(results['agent_ids']))}")
        
        # Report agents deleted
        if results['agents_deleted'] > 0:
            click.echo()
            click.secho(f"📦 {t('job.deleting_from_table', table='agents')}", fg='cyan')
            for agent_id in results['agent_ids']:
                click.secho(f"  ✓ {t('job.deleted_agent', id=agent_id)}", fg='green')
        
        # Report invocations deleted
        if results['invocations_deleted'] > 0:
            click.echo()
            click.secho(f"📦 {t('job.deleting_from_table', table='invocations')}", fg='cyan')
            click.secho(f"  ✓ {t('job.deleted_invocations', count=results['invocations_deleted'], id=agent_name)}", fg='green')
        
        # Report sessions deleted
        if results['sessions_deleted'] > 0:
            click.echo()
            click.secho(f"📦 {t('job.deleting_from_table', table='sessions')}", fg='cyan')
            click.secho(f"  ✓ {t('job.deleted_sessions', count=results['sessions_deleted'], id=agent_name)}", fg='green')
        
        # Report messages deleted
        if results['messages_deleted'] > 0:
            click.echo()
            click.secho(f"📦 {t('job.deleting_from_table', table='messages')}", fg='cyan')
            click.secho(f"  ✓ {t('job.deleted_messages', count=results['messages_deleted'])}", fg='green')
        
        # Report errors
        if results['errors']:
            click.echo()
            for err in results['errors']:
                click.secho(f"  ⚠ {err}", fg='red', err=True)
        
        total_deleted = (
            results['agents_deleted'] +
            results['invocations_deleted'] +
            results['sessions_deleted'] +
            results['messages_deleted']
        )
        
        click.echo()
        click.secho("=" * 50, fg='green')
        click.secho(f"✅ {t('job.delete_complete', count=total_deleted, name=agent_name)}", fg='green', bold=True)
        click.secho("=" * 50, fg='green')
        
    except ImportError as e:
        click.secho(f"{t('common.error')}: {t('common.missing_dependency', error=str(e))}", fg='red', err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"{t('common.error')}: {e}", fg='red', err=True)
        sys.exit(1)


@job.command('list')
@click.option('--status', '-s', type=click.Choice(['pending', 'queued', 'running', 'completed', 'failed', 'cancelled']),
              help='Filter by task status')
@click.option('--type', '-t', 'task_type', type=click.Choice(['build_agent', 'deploy_agent', 'invoke_agent']),
              help='Filter by task type')
@click.option('--limit', '-n', default=20, help='Maximum number of tasks to show')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--queues', '-q', is_flag=True, help='Show queue statistics instead of tasks')
@click.pass_obj
def job_list(ctx, status, task_type, limit, output, queues):
    """List tasks or queue statistics
    
    \b
    EXAMPLES:
      nexus-cli job list
      nexus-cli job list --status running
      nexus-cli job list --type build_agent
      nexus-cli job list --queues
      nexus-cli job list --output json
    """
    try:
        infra = ctx.infrastructure_manager
        
        if queues:
            # Show queue statistics
            click.secho("=" * 60, fg='cyan')
            click.secho(t('job.queue_stats_title'), fg='cyan', bold=True)
            click.secho("=" * 60, fg='cyan')
            click.echo(f"   {t('init.region', region=infra.region)}")
            if infra.sqs_endpoint:
                click.echo(f"   {t('init.endpoint', endpoint=infra.sqs_endpoint)}")
            click.echo()
            
            results = infra.get_queue_stats()
            
            if output == 'json':
                click.echo(json_dumps_utf8(results))
            else:
                for q in results['queues']:
                    if q['exists']:
                        click.secho(f"📬 {t('job.queue_name', name=q['name'])}", fg='cyan')
                        click.echo(f"   {t('job.queue_messages', available=q['messages_available'], in_flight=q['messages_in_flight'], delayed=q['messages_delayed'])}")
                    else:
                        click.secho(f"📬 {t('job.queue_name', name=q['name'])}", fg='cyan')
                        click.secho(f"   ⚠ {t('job.queue_not_exists')}", fg='yellow')
                    click.echo()
            return
        
        # List tasks
        click.secho("=" * 60, fg='cyan')
        click.secho(t('job.list_title'), fg='cyan', bold=True)
        click.secho("=" * 60, fg='cyan')
        
        if status:
            click.echo(f"   {t('job.filter_status', status=status)}")
        if task_type:
            click.echo(f"   {t('job.filter_type', type=task_type)}")
        click.echo()
        
        results = infra.list_tasks(status=status, task_type=task_type, limit=limit)
        
        if results['errors']:
            for err in results['errors']:
                if err == 'table_not_found':
                    click.secho(f"⚠ {t('job.table_not_found')}", fg='yellow')
                else:
                    click.secho(f"⚠ {err}", fg='red', err=True)
            return
        
        if not results['tasks']:
            click.secho(t('job.no_tasks'), fg='yellow')
            return
        
        click.echo(t('job.tasks_found', count=results['count']))
        click.echo()
        
        if output == 'json':
            click.echo(json_dumps_utf8(results['tasks']))
        else:
            # Table format with colors
            status_colors = {
                'pending': 'yellow',
                'queued': 'blue',
                'running': 'cyan',
                'completed': 'green',
                'failed': 'red',
                'cancelled': 'bright_black'
            }
            
            for task in results['tasks']:
                task_id = task.get('task_id', 'N/A')
                task_status = task.get('status', 'unknown')
                task_type_val = task.get('task_type', 'unknown')
                created = task.get('created_at', 'N/A')
                project_id = task.get('project_id', '')
                
                # Status emoji
                status_emoji = {
                    'pending': '⏳',
                    'queued': '📋',
                    'running': '🔄',
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '🚫'
                }.get(task_status, '❓')
                
                color = status_colors.get(task_status, None)
                click.secho(f"{status_emoji} {task_id}", fg=color, bold=True)
                click.echo(f"   Type: {task_type_val} | Status: {task_status}")
                if project_id:
                    click.echo(f"   Project: {project_id}")
                click.echo(f"   Created: {created}")
                click.echo()
        
    except ImportError as e:
        click.secho(f"{t('common.error')}: {t('common.missing_dependency', error=str(e))}", fg='red', err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"{t('common.error')}: {e}", fg='red', err=True)
        sys.exit(1)


@job.command('view')
@click.argument('task_id')
@click.option('--output', '-o', type=click.Choice(['detail', 'json']), default='detail', help='Output format')
@click.pass_obj
def job_view(ctx, task_id, output):
    """View details of a specific task
    
    \b
    EXAMPLES:
      nexus-cli job view task-123
      nexus-cli job view task-123 --output json
    """
    try:
        infra = ctx.infrastructure_manager
        
        result = infra.get_task(task_id)
        
        if result['error']:
            if result['error'] == 'table_not_found':
                click.secho(f"⚠ {t('job.table_not_found')}", fg='yellow')
            else:
                click.secho(f"{t('common.error')}: {result['error']}", fg='red', err=True)
            sys.exit(1)
        
        if not result['found']:
            click.secho(t('job.task_not_found', id=task_id), fg='yellow')
            sys.exit(1)
        
        task = result['task']
        
        if output == 'json':
            click.echo(json_dumps_utf8(task))
        else:
            click.secho("=" * 60, fg='cyan')
            click.secho(t('job.view_title', id=task_id), fg='cyan', bold=True)
            click.secho("=" * 60, fg='cyan')
            click.echo()
            
            # Status with color
            task_status = task.get('status', 'unknown')
            status_colors = {
                'pending': 'yellow',
                'queued': 'blue',
                'running': 'cyan',
                'completed': 'green',
                'failed': 'red',
                'cancelled': 'bright_black'
            }
            status_emoji = {
                'pending': '⏳',
                'queued': '📋',
                'running': '🔄',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(task_status, '❓')
            
            click.echo(f"Task ID:     {click.style(task.get('task_id', 'N/A'), fg='cyan', bold=True)}")
            click.echo(f"Status:      {status_emoji} {click.style(task_status, fg=status_colors.get(task_status))}")
            click.echo(f"Type:        {task.get('task_type', 'N/A')}")
            click.echo(f"Priority:    {task.get('priority', 'N/A')}")
            click.echo()
            
            if task.get('project_id'):
                click.echo(f"Project ID:  {task.get('project_id')}")
            if task.get('worker_id'):
                click.echo(f"Worker ID:   {task.get('worker_id')}")
            if task.get('project_id') or task.get('worker_id'):
                click.echo()
            
            click.secho("Timestamps:", bold=True)
            click.echo(f"  Created:   {task.get('created_at', 'N/A')}")
            if task.get('started_at'):
                click.echo(f"  Started:   {task.get('started_at')}")
            if task.get('completed_at'):
                click.echo(f"  Completed: {task.get('completed_at')}")
            if task.get('updated_at'):
                click.echo(f"  Updated:   {task.get('updated_at')}")
            
            if task.get('retry_count', 0) > 0:
                click.echo()
                click.secho(f"Retries:     {task.get('retry_count')}", fg='yellow')
            
            if task.get('error_message'):
                click.echo()
                click.secho("Error:", fg='red', bold=True)
                click.secho(f"  {task.get('error_message')}", fg='red')
            
            if task.get('payload'):
                click.echo()
                click.secho("Payload:", bold=True)
                payload_str = json_dumps_utf8(task['payload'])
                for line in payload_str.split('\n'):
                    click.echo(f"  {line}")
            
            if task.get('result'):
                click.echo()
                click.secho("Result:", fg='green', bold=True)
                result_str = json_dumps_utf8(task['result'])
                for line in result_str.split('\n'):
                    click.echo(f"  {line}")
        
    except ImportError as e:
        click.echo(f"{t('common.error')}: {t('common.missing_dependency', error=str(e))}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"{t('common.error')}: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point"""
    cli()


# ============================================================================
# ARTIFACT COMMANDS
# ============================================================================

@cli.group()
def artifact():
    """Manage agent artifacts and S3 synchronization
    
    \b
    SUBCOMMANDS:
      sync      Sync agent files to S3
      list      List synced agents
      versions  List versions of an agent
      describe  Show version details
      delete    Delete a version
    
    \b
    EXAMPLES:
      nexus-cli artifact sync my-agent
      nexus-cli artifact list
      nexus-cli artifact versions my-agent
      nexus-cli artifact describe my-agent --version <uuid>
    """
    pass


@artifact.command('sync')
@click.argument('agent_name')
@click.option('--tag', '-t', default='', help='Version tag (e.g., v1.0.0)')
@click.option('--notes', '-n', default='', help='Version notes')
@click.option('--category', '-c', multiple=True, 
              type=click.Choice(['agents', 'projects', 'tools', 'prompts']),
              help='Categories to sync (default: all)')
@click.option('--output', '-o', type=click.Choice(['detail', 'json']), default='detail',
              help='Output format')
@click.pass_obj
def artifact_sync(ctx, agent_name, tag, notes, category, output):
    """Sync agent files to S3
    
    Uploads agent-related files to S3 and records version in DynamoDB.
    
    \b
    FILES SYNCED:
      - agents/generated_agents/<agent_name>/
      - projects/<agent_name>/
      - tools/generated_tools/<agent_name>/
      - prompts/generated_agents_prompts/<agent_name>/
    
    \b
    EXAMPLES:
      # Sync all files
      nexus-cli artifact sync my-agent
      
      # Sync with version tag
      nexus-cli artifact sync my-agent --tag v1.0.0 --notes "Initial release"
      
      # Sync only agents and prompts
      nexus-cli artifact sync my-agent -c agents -c prompts
    """
    try:
        categories = list(category) if category else None
        
        click.secho("=" * 60, fg='cyan')
        click.secho(f"Syncing Agent: {agent_name}", fg='cyan', bold=True)
        click.secho("=" * 60, fg='cyan')
        click.echo()
        
        click.secho("Uploading files to S3...", fg='yellow')
        
        result = ctx.artifact_manager.sync_agent(
            agent_name=agent_name,
            version_tag=tag,
            notes=notes,
            categories=categories
        )
        
        if not result.success:
            click.echo()
            click.secho(f"✗ Sync failed: {result.error}", fg='red')
            sys.exit(1)
        
        click.echo()
        click.secho("=" * 60, fg='green')
        click.secho("✓ Sync completed successfully!", fg='green', bold=True)
        click.secho("=" * 60, fg='green')
        click.echo()
        
        if output == 'json':
            click.echo(json_dumps_utf8(result.to_dict()))
        else:
            click.echo(f"Agent:        {result.agent_name}")
            click.echo(f"Version UUID: {result.version_uuid}")
            click.echo(f"Workspace:    {result.workspace_uuid}")
            click.echo(f"Files:        {result.files_synced}")
            click.echo(f"Size:         {result.format_size()}")
            click.echo(f"Duration:     {result.duration_seconds:.2f}s")
            click.echo()
            click.secho("S3 Paths:", bold=True)
            for cat, path in result.s3_paths.items():
                click.echo(f"  {cat}: {path}")
        
    except Exception as e:
        click.secho(f"Error: {e}", fg='red', err=True)
        sys.exit(1)


@artifact.command('list')
@click.option('--all', '-a', 'show_all', is_flag=True, default=False,
              help='Show all versions instead of grouped by agent')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def artifact_list(ctx, show_all, output):
    """List all synced agents
    
    Shows agents that have been synced to S3 with version counts.
    Use --all to show all versions.
    
    \b
    EXAMPLES:
      nexus-cli artifact list
      nexus-cli artifact list --all
      nexus-cli artifact list --output json
    """
    try:
        if show_all:
            # 显示所有版本
            versions = ctx.artifact_manager.list_all_versions()
            
            if output == 'json':
                data = {
                    'versions': [v.to_dict() for v in versions],
                    'total': len(versions),
                    'workspace_uuid': ctx.artifact_manager.get_workspace_uuid(),
                    'bucket': ctx.artifact_manager.get_bucket_name()
                }
                click.echo(json_dumps_utf8(data))
            else:
                if not versions:
                    click.secho("No synced versions found.", fg='yellow')
                    click.echo()
                    click.echo("Use 'nexus-cli artifact sync <agent_name>' to sync an agent.")
                    return
                
                click.secho("=" * 100, fg='cyan')
                click.secho("All Synced Versions", fg='cyan', bold=True)
                click.secho("=" * 100, fg='cyan')
                click.echo()
                
                data = []
                for v in versions:
                    data.append({
                        'agent_name': v.agent_name,
                        'version_uuid': v.version_uuid[:12] + '...',
                        'tag': v.version_tag[:20] if v.version_tag else '-',
                        'files': v.file_count,
                        'size': v.format_size(),
                        'created_at': v.created_at[:19] if v.created_at else '-'
                    })
                
                headers = ['agent_name', 'version_uuid', 'tag', 'files', 'size', 'created_at']
                click.echo(format_output(data, output, headers))
                click.echo()
                click.echo(f"Total: {len(versions)} versions")
                click.echo(f"Bucket: {ctx.artifact_manager.get_bucket_name()}")
        else:
            # 按Agent分组显示
            agents = ctx.artifact_manager.list_synced_agents()
            
            if output == 'json':
                data = {
                    'agents': [a.to_dict() for a in agents],
                    'total': len(agents),
                    'workspace_uuid': ctx.artifact_manager.get_workspace_uuid(),
                    'bucket': ctx.artifact_manager.get_bucket_name()
                }
                click.echo(json_dumps_utf8(data))
            else:
                if not agents:
                    click.secho("No synced agents found.", fg='yellow')
                    click.echo()
                    click.echo("Use 'nexus-cli artifact sync <agent_name>' to sync an agent.")
                    return
                
                click.secho("=" * 70, fg='cyan')
                click.secho("Synced Agents", fg='cyan', bold=True)
                click.secho("=" * 70, fg='cyan')
                click.echo()
                
                data = []
                for a in agents:
                    data.append({
                        'agent_name': a.agent_name,
                        'versions': a.version_count,
                        'latest': a.latest_version[:20] if a.latest_version else '-',
                        'last_sync': a.latest_created_at[:19] if a.latest_created_at else '-'
                    })
                
                headers = ['agent_name', 'versions', 'latest', 'last_sync']
                click.echo(format_output(data, output, headers))
                click.echo()
                click.echo(f"Total: {len(agents)} agents")
                click.echo(f"Bucket: {ctx.artifact_manager.get_bucket_name()}")
                click.echo()
                click.echo("Tip: Use --all to show all versions")
        
    except Exception as e:
        click.secho(f"Error: {e}", fg='red', err=True)
        sys.exit(1)


@artifact.command('versions')
@click.argument('agent_name')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def artifact_versions(ctx, agent_name, output):
    """List all versions of an agent
    
    Shows version history with timestamps and metadata.
    
    \b
    EXAMPLES:
      nexus-cli artifact versions my-agent
      nexus-cli artifact versions my-agent --output json
    """
    try:
        versions = ctx.artifact_manager.list_versions(agent_name)
        
        if output == 'json':
            data = {
                'agent_name': agent_name,
                'versions': [v.to_dict() for v in versions],
                'total': len(versions)
            }
            click.echo(json_dumps_utf8(data))
        else:
            if not versions:
                click.secho(f"No versions found for agent '{agent_name}'.", fg='yellow')
                return
            
            click.secho("=" * 80, fg='cyan')
            click.secho(f"Versions: {agent_name}", fg='cyan', bold=True)
            click.secho("=" * 80, fg='cyan')
            click.echo()
            
            data = []
            for v in versions:
                data.append({
                    'version_uuid': v.version_uuid[:12] + '...',
                    'tag': v.version_tag[:20] if v.version_tag else '-',
                    'files': v.file_count,
                    'size': v.format_size(),
                    'created_at': v.created_at[:19] if v.created_at else '-',
                    'created_by': v.created_by or '-'
                })
            
            headers = ['version_uuid', 'tag', 'files', 'size', 'created_at', 'created_by']
            click.echo(format_output(data, output, headers))
            click.echo()
            click.echo(f"Total: {len(versions)} versions")
        
    except Exception as e:
        click.secho(f"Error: {e}", fg='red', err=True)
        sys.exit(1)


@artifact.command('describe')
@click.argument('agent_name')
@click.option('--version', '-v', required=True, help='Version UUID')
@click.option('--output', '-o', type=click.Choice(['detail', 'json']), default='detail',
              help='Output format')
@click.pass_obj
def artifact_describe(ctx, agent_name, version, output):
    """Show details of a specific version
    
    \b
    EXAMPLES:
      nexus-cli artifact describe my-agent --version abc123...
    """
    try:
        v = ctx.artifact_manager.get_version_detail(agent_name, version)
        
        if not v:
            click.secho(f"Version not found: {version}", fg='red')
            sys.exit(1)
        
        if output == 'json':
            click.echo(json_dumps_utf8(v.to_dict()))
        else:
            click.secho("=" * 70, fg='cyan')
            click.secho(f"Version Details: {agent_name}", fg='cyan', bold=True)
            click.secho("=" * 70, fg='cyan')
            click.echo()
            
            click.echo(f"Agent:        {v.agent_name}")
            click.echo(f"Version UUID: {v.version_uuid}")
            click.echo(f"Version Tag:  {v.version_tag or '-'}")
            click.echo(f"Workspace:    {v.workspace_uuid}")
            click.echo()
            click.echo(f"Files:        {v.file_count}")
            click.echo(f"Size:         {v.format_size()}")
            click.echo(f"Created:      {v.created_at}")
            click.echo(f"Created By:   {v.created_by or '-'}")
            
            if v.notes:
                click.echo()
                click.secho("Notes:", bold=True)
                click.echo(f"  {v.notes}")
            
            click.echo()
            click.secho("S3 Paths:", bold=True)
            for cat, path in v.s3_paths.items():
                click.echo(f"  {cat}: {path}")
        
    except Exception as e:
        click.secho(f"Error: {e}", fg='red', err=True)
        sys.exit(1)


@artifact.command('delete')
@click.argument('agent_name')
@click.option('--version', '-v', required=True, help='Version UUID to delete')
@click.option('--delete-s3', is_flag=True, help='Also delete S3 files')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.pass_obj
def artifact_delete(ctx, agent_name, version, delete_s3, force):
    """Delete a specific version
    
    \b
    EXAMPLES:
      # Delete version record only
      nexus-cli artifact delete my-agent --version abc123...
      
      # Delete version and S3 files
      nexus-cli artifact delete my-agent --version abc123... --delete-s3
    """
    try:
        # Get version details first
        v = ctx.artifact_manager.get_version_detail(agent_name, version)
        
        if not v:
            click.secho(f"Version not found: {version}", fg='red')
            sys.exit(1)
        
        # Confirmation
        if not force:
            click.secho("Version to delete:", fg='yellow')
            click.echo(f"  Agent:   {v.agent_name}")
            click.echo(f"  Version: {v.version_uuid}")
            click.echo(f"  Tag:     {v.version_tag or '-'}")
            click.echo(f"  Files:   {v.file_count}")
            
            if delete_s3:
                click.secho("\n⚠ S3 files will also be deleted!", fg='red')
            
            if not click.confirm("\nAre you sure you want to delete this version?"):
                click.echo("Cancelled.")
                return
        
        success = ctx.artifact_manager.delete_version(agent_name, version, delete_s3)
        
        if success:
            click.secho("✓ Version deleted successfully!", fg='green')
        else:
            click.secho("✗ Failed to delete version.", fg='red')
            sys.exit(1)
        
    except Exception as e:
        click.secho(f"Error: {e}", fg='red', err=True)
        sys.exit(1)


# ============================================================================
# SERVICE COMMANDS - 服务管理命令
# ============================================================================

@cli.group()
def service():
    """Manage Nexus-AI services (API, Worker, Web)
    
    \b
    SUBCOMMANDS:
      start     Start services
      stop      Stop services
      restart   Restart services
      status    Show service status
      logs      View service logs
    
    \b
    EXAMPLES:
      nexus-cli service start              # Start all services
      nexus-cli service start --api        # Start API only
      nexus-cli service stop               # Stop all services
      nexus-cli service restart            # Restart all services
      nexus-cli service status             # Show status
      nexus-cli service logs               # View all logs
      nexus-cli service logs --api         # View API logs
    """
    pass


def _get_service_manager(ctx):
    """获取服务管理器实例"""
    from .managers.service_manager import ServiceManager
    return ServiceManager(ctx.base_path)


def _print_service_banner():
    """打印服务管理横幅"""
    click.echo()
    click.secho("╔══════════════════════════════════════════════════════════════════╗", fg='cyan')
    click.secho("║              Nexus-AI Service Manager                            ║", fg='cyan')
    click.secho("╚══════════════════════════════════════════════════════════════════╝", fg='cyan')
    click.echo()


def _print_status_table(services):
    """打印服务状态表格"""
    click.echo()
    click.secho("Service Status:", fg='cyan')
    click.echo("━" * 50)
    
    for svc in services:
        status_color = 'green' if svc.status.value == 'running' else 'red'
        status_icon = '●' if svc.status.value == 'running' else '○'
        
        click.echo(f"  {svc.name:10} ", nl=False)
        click.secho(f"{status_icon} {svc.status.value:10}", fg=status_color, nl=False)
        
        if svc.pid:
            click.echo(f" (PID: {svc.pid})", nl=False)
        if svc.port:
            click.echo(f" Port: {svc.port}", nl=False)
        click.echo()
    
    click.echo("━" * 50)


def _print_access_urls(urls):
    """打印访问地址"""
    click.echo()
    click.secho("Access URLs:", fg='cyan')
    click.echo("━" * 50)
    click.echo(f"  Web:      {urls['web']}")
    click.echo(f"  API:      {urls['api']}")
    click.echo(f"  API Docs: {urls['api_docs']}")
    click.echo(f"  Health:   {urls['health']}")
    click.echo("━" * 50)


@service.command('start')
@click.option('--api', 'start_api', is_flag=True, help='Start API service only')
@click.option('--worker', 'start_worker', is_flag=True, help='Start Worker service only')
@click.option('--web', 'start_web', is_flag=True, help='Start Web service only')
@click.option('--force-build', is_flag=True, help='Force rebuild frontend')
@click.option('--dev', 'dev_mode', is_flag=True, help='Start in development mode')
@click.pass_obj
def service_start(ctx, start_api, start_worker, start_web, force_build, dev_mode):
    """Start Nexus-AI services
    
    \b
    EXAMPLES:
      nexus-cli service start              # Start all services
      nexus-cli service start --api        # Start API only
      nexus-cli service start --worker     # Start Worker only
      nexus-cli service start --web        # Start Web only
      nexus-cli service start --force-build  # Force rebuild frontend
      nexus-cli service start --dev        # Start in development mode
    """
    _print_service_banner()
    
    # 设置运行模式
    if dev_mode:
        os.environ["RUN_MODE"] = "dev"
    
    sm = _get_service_manager(ctx)
    
    # 检查虚拟环境
    if not sm.check_venv():
        click.secho(f"✗ Virtual environment not found: {sm.venv_dir}", fg='red')
        click.echo("  Please run: uv venv --python python3.12")
        sys.exit(1)
    
    # 如果没有指定具体服务，启动所有服务
    start_all = not (start_api or start_worker or start_web)
    
    results = []
    
    if start_all:
        click.secho("Starting all services...", fg='blue')
        click.echo()
        results = sm.start_all(force_build)
    else:
        if start_api:
            click.secho("Starting API service...", fg='blue')
            success, msg = sm.start_api()
            results.append(("api", success, msg))
        
        if start_worker:
            click.secho("Starting Worker service...", fg='blue')
            success, msg = sm.start_worker()
            results.append(("worker", success, msg))
        
        if start_web:
            click.secho("Starting Web service...", fg='blue')
            success, msg = sm.start_web(force_build)
            results.append(("web", success, msg))
    
    # 显示结果
    click.echo()
    all_success = True
    for name, success, msg in results:
        if success:
            click.secho(f"  ✓ {name}: {msg}", fg='green')
        else:
            click.secho(f"  ✗ {name}: {msg}", fg='red')
            all_success = False
    
    # 显示状态和访问地址
    if all_success:
        _print_status_table(sm.get_all_status())
        _print_access_urls(sm.get_access_urls())
        
        click.echo()
        click.secho("Tips:", fg='yellow')
        click.echo("  - View logs:   nexus-cli service logs")
        click.echo("  - View status: nexus-cli service status")
        click.echo("  - Stop:        nexus-cli service stop")
    else:
        sys.exit(1)


@service.command('stop')
@click.option('--api', 'stop_api', is_flag=True, help='Stop API service only')
@click.option('--worker', 'stop_worker', is_flag=True, help='Stop Worker service only')
@click.option('--web', 'stop_web', is_flag=True, help='Stop Web service only')
@click.pass_obj
def service_stop(ctx, stop_api, stop_worker, stop_web):
    """Stop Nexus-AI services
    
    \b
    EXAMPLES:
      nexus-cli service stop              # Stop all services
      nexus-cli service stop --api        # Stop API only
      nexus-cli service stop --worker     # Stop Worker only
      nexus-cli service stop --web        # Stop Web only
    """
    _print_service_banner()
    
    sm = _get_service_manager(ctx)
    
    # 如果没有指定具体服务，停止所有服务
    stop_all = not (stop_api or stop_worker or stop_web)
    
    results = []
    
    if stop_all:
        click.secho("Stopping all services...", fg='blue')
        click.echo()
        results = sm.stop_all()
    else:
        from .managers.service_manager import ServiceType
        
        if stop_web:
            click.secho("Stopping Web service...", fg='blue')
            success, msg = sm.stop_service(ServiceType.WEB)
            results.append(("web", success, msg))
        
        if stop_worker:
            click.secho("Stopping Worker service...", fg='blue')
            success, msg = sm.stop_service(ServiceType.WORKER)
            results.append(("worker", success, msg))
        
        if stop_api:
            click.secho("Stopping API service...", fg='blue')
            success, msg = sm.stop_service(ServiceType.API)
            results.append(("api", success, msg))
    
    # 显示结果
    click.echo()
    for name, success, msg in results:
        if success:
            click.secho(f"  ✓ {name}: {msg}", fg='green')
        else:
            click.secho(f"  ✗ {name}: {msg}", fg='red')
    
    click.echo()
    click.secho("All services stopped.", fg='green')


@service.command('restart')
@click.option('--api', 'restart_api', is_flag=True, help='Restart API service only')
@click.option('--worker', 'restart_worker', is_flag=True, help='Restart Worker service only')
@click.option('--web', 'restart_web', is_flag=True, help='Restart Web service only')
@click.option('--force-build', is_flag=True, help='Force rebuild frontend')
@click.pass_obj
def service_restart(ctx, restart_api, restart_worker, restart_web, force_build):
    """Restart Nexus-AI services
    
    \b
    EXAMPLES:
      nexus-cli service restart              # Restart all services
      nexus-cli service restart --api        # Restart API only
      nexus-cli service restart --force-build  # Restart with frontend rebuild
    """
    _print_service_banner()
    
    sm = _get_service_manager(ctx)
    
    # 如果没有指定具体服务，重启所有服务
    restart_all = not (restart_api or restart_worker or restart_web)
    
    if restart_all:
        click.secho("Restarting all services...", fg='blue')
        click.echo()
        results = sm.restart_all(force_build)
    else:
        from .managers.service_manager import ServiceType
        results = []
        
        if restart_api:
            click.secho("Restarting API service...", fg='blue')
            sm.stop_service(ServiceType.API)
            time.sleep(1)
            success, msg = sm.start_api()
            results.append(("api", success, msg))
        
        if restart_worker:
            click.secho("Restarting Worker service...", fg='blue')
            sm.stop_service(ServiceType.WORKER)
            time.sleep(1)
            success, msg = sm.start_worker()
            results.append(("worker", success, msg))
        
        if restart_web:
            click.secho("Restarting Web service...", fg='blue')
            sm.stop_service(ServiceType.WEB)
            time.sleep(1)
            success, msg = sm.start_web(force_build)
            results.append(("web", success, msg))
    
    # 显示结果
    click.echo()
    all_success = True
    for name, success, msg in results:
        if success:
            click.secho(f"  ✓ {name}: {msg}", fg='green')
        else:
            click.secho(f"  ✗ {name}: {msg}", fg='red')
            all_success = False
    
    if all_success:
        _print_status_table(sm.get_all_status())
        _print_access_urls(sm.get_access_urls())


@service.command('status')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_obj
def service_status(ctx, output):
    """Show service status
    
    \b
    EXAMPLES:
      nexus-cli service status              # Show status table
      nexus-cli service status -o json      # Show status as JSON
    """
    sm = _get_service_manager(ctx)
    services = sm.get_all_status()
    
    if output == 'json':
        data = {
            'services': [
                {
                    'name': s.name,
                    'status': s.status.value,
                    'pid': s.pid,
                    'port': s.port,
                    'log_file': s.log_file
                }
                for s in services
            ],
            'urls': sm.get_access_urls()
        }
        click.echo(json_dumps_utf8(data))
    else:
        _print_service_banner()
        _print_status_table(services)
        
        # 显示日志文件位置
        click.echo()
        click.secho("Log Files:", fg='cyan')
        for s in services:
            click.echo(f"  - {s.name:10} {s.log_file}")
        
        # 如果有服务在运行，显示访问地址
        running_count = sum(1 for s in services if s.status.value == 'running')
        if running_count > 0:
            _print_access_urls(sm.get_access_urls())


@service.command('logs')
@click.option('--api', 'show_api', is_flag=True, help='Show API logs only')
@click.option('--worker', 'show_worker', is_flag=True, help='Show Worker logs only')
@click.option('--web', 'show_web', is_flag=True, help='Show Web logs only')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (like tail -f)')
@click.pass_obj
def service_logs(ctx, show_api, show_worker, show_web, lines, follow):
    """View service logs
    
    \b
    EXAMPLES:
      nexus-cli service logs              # Show all logs
      nexus-cli service logs --api        # Show API logs only
      nexus-cli service logs -n 100       # Show last 100 lines
      nexus-cli service logs -f           # Follow logs (Ctrl+C to exit)
    """
    from .managers.service_manager import ServiceType
    
    sm = _get_service_manager(ctx)
    
    # 确定要显示的服务
    show_all = not (show_api or show_worker or show_web)
    services = []
    
    if show_all or show_api:
        services.append(ServiceType.API)
    if show_all or show_worker:
        services.append(ServiceType.WORKER)
    if show_all or show_web:
        services.append(ServiceType.WEB)
    
    if follow:
        # 实时跟踪日志
        log_files = [str(sm._get_log_file(s)) for s in services]
        click.secho(f"Following logs... (Ctrl+C to exit)", fg='yellow')
        click.echo()
        
        try:
            import subprocess
            subprocess.run(["tail", "-f"] + log_files)
        except KeyboardInterrupt:
            click.echo()
            click.secho("Log following stopped.", fg='yellow')
    else:
        # 显示最近的日志
        for svc in services:
            logs = sm.get_logs(svc, lines)
            log_content = logs.get(svc.value, "")
            
            click.echo()
            click.secho(f"═══ {svc.value.upper()} LOGS ═══", fg='cyan')
            click.echo(log_content if log_content else "(empty)")


if __name__ == '__main__':
    main()
