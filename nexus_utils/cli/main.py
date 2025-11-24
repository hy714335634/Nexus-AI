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
@click.version_option(version="1.0.0")
@click.option('--base-path', default=".", help='Base path to Nexus-AI installation')
@click.pass_context
def cli(ctx, base_path):
    """Nexus-AI Backend Management CLI
    
    A kubectl-style CLI tool for managing Nexus-AI backend artifacts including
    Projects, Agents, Templates, Prompts, and Tools.
    """
    ctx.obj = CLIContext(base_path)


# ============================================================================
# PROJECT COMMANDS
# ============================================================================

@cli.group()
def project():
    """Manage Nexus-AI projects"""
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
