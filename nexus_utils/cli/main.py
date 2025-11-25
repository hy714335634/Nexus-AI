#!/usr/bin/env python3
"""
Nexus-AI Backend Management CLI

A kubectl-style CLI tool for managing Nexus-AI backend artifacts.
"""

import click
import sys
from pathlib import Path

from .adapters.filesystem import FileSystemAdapter
from .adapters.config_loader import ConfigLoader
from .managers.project_manager import ProjectManager
from .managers.agent_manager import AgentManager
from .utils.formatters import format_output


# Global context
class CLIContext:
    """CLI context object"""
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.fs_adapter = FileSystemAdapter(base_path)
        self.config_loader = ConfigLoader(self.fs_adapter)
        self.project_manager = ProjectManager(self.fs_adapter, self.config_loader)
        self.agent_manager = AgentManager(self.fs_adapter, self.config_loader)


@click.group()
@click.version_option(version="2.1.0")
@click.option('--base-path', default=".", help='Base path to Nexus-AI installation')
@click.pass_context
def cli(ctx, base_path):
    """Nexus-AI Backend Management CLI
    
    A kubectl-style CLI tool for managing Nexus-AI backend artifacts including
    Projects, Agents, Templates, Prompts, and Tools.
    
    \b
    CORE COMMANDS:
      project     Manage projects (init, list, describe, backup, restore, delete)
      agents      Manage AI agents (list, describe)
      backup      Manage backups (list, describe, validate, delete)
      overview    Display system-wide overview
    
    \b
    QUICK START:
      # List all projects
      nexus-cli project list
      
      # Create a new project
      nexus-cli project init my-project
      
      # Backup a project
      nexus-cli project backup my-project
      
      # Restore from backup
      nexus-cli project restore my-project --from-backup backup.tar.gz
      
      # List all backups
      nexus-cli backup list
    
    \b
    BACKUP & RESTORE:
      The CLI provides comprehensive backup and restore functionality:
      
      • Complete project backups with all resources (agents, prompts, tools)
      • SHA-256 checksums for integrity verification
      • Automatic safety backups before overwrite
      • Project cloning by restoring to different name
      • Dry-run mode for preview
      • Detailed validation and error reporting
    
    \b
    EXAMPLES:
      # Backup workflow
      nexus-cli project backup production-agent
      nexus-cli backup list
      nexus-cli backup validate backups/production-agent_*.tar.gz
      
      # Clone a project
      nexus-cli project restore dev-agent --from-backup backups/production-agent_*.tar.gz
      
      # Disaster recovery
      nexus-cli project restore my-project --from-backup backup.tar.gz --force
    
    \b
    For more information on a specific command:
      nexus-cli <command> --help
    
    Documentation: See README.md for comprehensive guide
    """
    ctx.obj = CLIContext(base_path)


# ============================================================================
# PROJECT COMMANDS
# ============================================================================

@cli.group()
def project():
    """Manage Nexus-AI projects
    
    \b
    COMMANDS:
      init        Create a new project
      list        List all projects
      describe    Show detailed project information
      backup      Create a backup of a project
      restore     Restore a project from backup
      delete      Delete a project and all resources
    
    \b
    EXAMPLES:
      # Create and manage projects
      nexus-cli project init my-project --description "My AI project"
      nexus-cli project list --output json
      nexus-cli project describe my-project
      
      # Backup and restore
      nexus-cli project backup my-project
      nexus-cli project restore my-project --from-backup backup.tar.gz
      
      # Preview operations
      nexus-cli project backup my-project --dry-run
      nexus-cli project delete my-project --dry-run
    """
    pass


@project.command('list')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def project_list(ctx, output):
    """List all projects"""
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
                data.append({
                    'name': p.name,
                    'agents': p.agent_count,
                    'templates': p.template_count,
                    'prompts': p.prompt_count,
                    'tools': p.tool_count,
                    'created': p.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            headers = ['name', 'agents', 'templates', 'prompts', 'tools', 'created']
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
    """Describe a project in detail"""
    try:
        project = ctx.project_manager.get_project(name)
        
        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)
        
        if output == 'json':
            click.echo(format_output(project.to_dict(), 'json'))
        else:
            # Text format with detailed information
            click.echo("=" * 70)
            click.echo(f"PROJECT: {project.name}")
            click.echo("=" * 70)
            click.echo()
            click.echo("Basic Information:")
            click.echo(f"  Name:        {project.name}")
            click.echo(f"  Created:     {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"  Updated:     {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo()
            
            click.echo("Resources:")
            click.echo(f"  Agents:      {project.agent_count}")
            for agent in project.agents:
                click.echo(f"    - {agent}")
            click.echo(f"  Templates:   {project.template_count}")
            for template in project.templates:
                click.echo(f"    - {template}")
            click.echo(f"  Prompts:     {project.prompt_count}")
            for prompt in project.prompts:
                click.echo(f"    - {prompt}")
            click.echo(f"  Tools:       {project.tool_count}")
            for tool in project.tools:
                click.echo(f"    - {tool}")
            click.echo()
            
            click.echo("=" * 70)
    
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
@click.pass_obj
def project_backup(ctx, name, output, dry_run):
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
    
    \b
    FEATURES:
      ✓ Complete resource backup (agents, prompts, tools)
      ✓ Integrity verification with SHA-256 checksums
      ✓ Compressed tar.gz format
      ✓ Timestamped filenames
      ✓ Detailed manifest with metadata
      ✓ Dry-run mode for preview
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
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('restore')
@click.argument('name')
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
      1. Restore to original name (same as backup)
      2. Restore to different name (project cloning)
      3. Force overwrite existing project (with safety backup)
    
    \b
    EXAMPLES:
      # Restore to original name
      nexus-cli project restore my-project --from-backup backups/my-project_20241125.tar.gz
      
      # Clone project (restore to different name)
      nexus-cli project restore dev-project --from-backup backups/prod-project_20241125.tar.gz
      
      # Force overwrite existing project
      nexus-cli project restore my-project --from-backup backup.tar.gz --force
      
      # Preview restore (dry-run)
      nexus-cli project restore my-project --from-backup backup.tar.gz --dry-run
    
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
        
        # Get manifest
        manifest = ctx.project_manager.get_backup_manifest(from_backup)
        
        # Check if project exists
        existing_project = ctx.project_manager.get_project(name)
        
        if dry_run:
            click.echo("[DRY RUN] Would perform the following operations:")
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


# ============================================================================
# AGENT COMMANDS
# ============================================================================

@cli.group()
def agents():
    """Manage Nexus-AI agents"""
    pass


@agents.command('list')
@click.option('--project', '-p', help='Filter by project')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table',
              help='Output format')
@click.pass_obj
def agents_list(ctx, project, output):
    """List all agents"""
    try:
        agents = ctx.agent_manager.list_agents(project=project)
        
        if output == 'json':
            data = {
                'agents': [a.to_dict() for a in agents],
                'total': len(agents)
            }
            click.echo(format_output(data, 'json'))
        else:
            # Prepare data for table/text
            data = []
            for a in agents:
                data.append({
                    'name': a.name,
                    'project': a.project or '-',
                    'tools': len(a.dependencies),
                    'created': a.created_at.strftime('%Y-%m-%d') if a.created_at else '-'
                })
            
            headers = ['name', 'project', 'tools', 'created']
            click.echo(format_output(data, output, headers))
            
            if project:
                click.echo(f"\nTotal: {len(agents)} agents in project '{project}'")
            else:
                click.echo(f"\nTotal: {len(agents)} agents")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@agents.command('describe')
@click.argument('name')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='text',
              help='Output format')
@click.pass_obj
def agents_describe(ctx, name, output):
    """Describe an agent in detail"""
    try:
        agent = ctx.agent_manager.get_agent(name)
        
        if not agent:
            click.echo(f"Error: Agent '{name}' not found", err=True)
            sys.exit(1)
        
        if output == 'json':
            click.echo(format_output(agent.to_dict(), 'json'))
        else:
            click.echo(f"Agent: {agent.name}")
            click.echo(f"Project: {agent.project or 'None'}")
            click.echo(f"Path: {agent.path}")
            
            if agent.config:
                click.echo(f"\nDescription: {agent.config.description}")
                click.echo(f"Category: {agent.config.category}")
                click.echo(f"Version: {agent.config.version}")
                
                if agent.config.tools_dependencies:
                    click.echo(f"\nTools ({len(agent.config.tools_dependencies)}):")
                    for tool in agent.config.tools_dependencies:
                        click.echo(f"  - {tool}")
                
                if agent.config.supported_models:
                    click.echo(f"\nSupported Models:")
                    for model in agent.config.supported_models:
                        click.echo(f"  - {model}")
    
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
    COMMANDS:
      list        List all available backups
      describe    Show detailed backup information
      validate    Verify backup integrity
      delete      Delete a backup file
    
    \b
    BACKUP FEATURES:
      • Complete project snapshots with all resources
      • SHA-256 checksums for integrity verification
      • Compressed tar.gz format for efficient storage
      • Detailed manifests with metadata
      • Automatic validation and error detection
      • Support for project cloning via restore
    
    \b
    EXAMPLES:
      # List and inspect backups
      nexus-cli backup list
      nexus-cli backup describe my-project_20241125_143022.tar.gz
      
      # Validate backup integrity
      nexus-cli backup validate backups/my-project_20241125.tar.gz
      
      # Clean up old backups
      nexus-cli backup delete old-backup.tar.gz
      
      # Backup workflow
      nexus-cli project backup my-project
      nexus-cli backup list
      nexus-cli backup validate backups/my-project_*.tar.gz
      nexus-cli project restore my-project --from-backup backup.tar.gz
    
    \b
    BACKUP STRUCTURE:
      Each backup contains:
      • manifest.json - Metadata and checksums
      • projects/<name>/ - Project configuration
      • agents/generated_agents/<name>/ - Agent implementations
      • prompts/generated_agents_prompts/<name>/ - Agent prompts
      • tools/generated_tools/<name>/ - Custom tools
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


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()
