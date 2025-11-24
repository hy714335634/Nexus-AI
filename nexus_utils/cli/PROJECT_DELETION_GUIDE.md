# Project Deletion Guide

## Overview

The `nexus-cli project delete` command now performs a **complete cleanup** of all project-related resources, including:

- ✅ Project directory (`projects/<name>/`)
- ✅ Generated agents (`agents/generated_agents/<name>/`)
- ✅ Prompts (`prompts/generated_agents_prompts/<name>/`)
- ✅ Tools (`tools/generated_tools/<name>/`)

## Usage

### Basic Deletion (with confirmation)

```bash
nexus-cli project delete <project-name>
```

**Example:**
```bash
$ nexus-cli project delete aws_pricing_agent

⚠️  WARNING: This will permanently delete project 'aws_pricing_agent' and ALL related resources

What will be deleted:
  • Project directory: projects/aws_pricing_agent/
  • Agents: 1 (aws_pricing_agent)
  • Templates: 1
  • Prompts: 1
  • Tools: 12
  • Agent files: agents/generated_agents/aws_pricing_agent/
  • Prompt files: prompts/generated_agents_prompts/aws_pricing_agent/
  • Tool files: tools/generated_tools/aws_pricing_agent/

Are you sure you want to continue? [y/N]: y

Deleting project 'aws_pricing_agent' and all related resources...
  ✓ Deleted agents: agents/generated_agents/aws_pricing_agent/
  ✓ Deleted prompts: prompts/generated_agents_prompts/aws_pricing_agent/
  ✓ Deleted tools: tools/generated_tools/aws_pricing_agent/
  ✓ Deleted project: projects/aws_pricing_agent/

✓ Project 'aws_pricing_agent' and all related resources deleted successfully
  Total: 4 directories removed
```

### Dry-Run Mode (Preview)

Preview what will be deleted without actually deleting:

```bash
nexus-cli project delete <project-name> --dry-run
```

**Example:**
```bash
$ nexus-cli project delete aws_pricing_agent --dry-run

[DRY RUN] Would perform the following operations:

Directories to be deleted:
  ✓ agents/generated_agents/aws_pricing_agent/
    - aws_pricing_agent.py
  ✓ prompts/generated_agents_prompts/aws_pricing_agent/
    - aws_pricing_agent.yaml
  ✓ tools/generated_tools/aws_pricing_agent/
    - 12 tool files
  ✓ projects/aws_pricing_agent/
    - config.yaml, status.yaml, README.md, etc.

Summary:
  - 1 agents will be deleted
  - 1 templates will be deleted
  - 1 prompts will be deleted
  - 12 tools will be deleted
  - Project directory will be deleted

Run without --dry-run to execute these operations.
```

### Force Delete (Skip Confirmation)

Delete without confirmation prompt:

```bash
nexus-cli project delete <project-name> --force
```

**Example:**
```bash
$ nexus-cli project delete old_test_project --force

Deleting project 'old_test_project' and all related resources...
  ✓ Deleted agents: agents/generated_agents/old_test_project/
  ✓ Deleted prompts: prompts/generated_agents_prompts/old_test_project/
  ✓ Deleted tools: tools/generated_tools/old_test_project/
  ✓ Deleted project: projects/old_test_project/

✓ Project 'old_test_project' and all related resources deleted successfully
  Total: 4 directories removed
```

## What Gets Deleted

### 1. Project Directory
```
projects/<project-name>/
├── config.yaml
├── status.yaml
├── README.md
├── requirements.txt
├── project_config.json
├── workflow_summary_report.md
└── agents/
    └── <agent-name>/
        └── *.json files
```

### 2. Generated Agents
```
agents/generated_agents/<project-name>/
└── <agent-name>.py
```

### 3. Prompts
```
prompts/generated_agents_prompts/<project-name>/
└── <agent-name>.yaml
```

### 4. Tools
```
tools/generated_tools/<project-name>/
├── <category>/
│   └── <tool-name>.py
└── __init__.py
```

## What Does NOT Get Deleted

The following are **protected** and will NOT be deleted:

❌ System agents (`agents/system_agents/`)  
❌ Template agents (`agents/template_agents/`)  
❌ System prompts (`prompts/system_agents_prompts/`)  
❌ Template prompts (`prompts/template_prompts/`)  
❌ System tools (`tools/system_tools/`)  
❌ Template tools (`tools/template_tools/`)  

## Safety Features

### 1. Confirmation Prompt
By default, the CLI asks for confirmation before deleting, showing:
- What will be deleted
- How many resources will be affected
- Full paths of directories to be removed

### 2. Dry-Run Mode
Use `--dry-run` to preview the deletion without making any changes:
```bash
nexus-cli project delete my_project --dry-run
```

### 3. Error Handling
- If project doesn't exist, shows error and exits
- If deletion fails, shows error message
- Tracks and reports what was successfully deleted

### 4. Detailed Output
Shows exactly what was deleted:
```
✓ Deleted agents: agents/generated_agents/project_name/
✓ Deleted prompts: prompts/generated_agents_prompts/project_name/
✓ Deleted tools: tools/generated_tools/project_name/
✓ Deleted project: projects/project_name/
```

## Best Practices

### 1. Always Use Dry-Run First
```bash
# Preview what will be deleted
nexus-cli project delete my_project --dry-run

# If everything looks good, proceed
nexus-cli project delete my_project
```

### 2. Check Project Details Before Deletion
```bash
# Review project contents
nexus-cli project describe my_project

# Then delete if needed
nexus-cli project delete my_project
```

### 3. Backup Important Projects
Before deleting, consider backing up:
```bash
# Backup project directory
tar -czf backup_my_project.tar.gz projects/my_project/

# Backup agents
tar -czf backup_agents.tar.gz agents/generated_agents/my_project/

# Then delete
nexus-cli project delete my_project
```

### 4. Use Force Only When Sure
Only use `--force` when you're absolutely certain:
```bash
# For automated scripts or when you're 100% sure
nexus-cli project delete temp_project --force
```

## Examples

### Example 1: Safe Deletion with Preview

```bash
# Step 1: Check what exists
$ nexus-cli project describe test_project

# Step 2: Preview deletion
$ nexus-cli project delete test_project --dry-run

# Step 3: Confirm and delete
$ nexus-cli project delete test_project
Are you sure? [y/N]: y
```

### Example 2: Batch Deletion with Dry-Run

```bash
# Preview multiple deletions
for project in old_test_1 old_test_2 old_test_3; do
    echo "=== Checking $project ==="
    nexus-cli project delete $project --dry-run
done

# If all look good, delete them
for project in old_test_1 old_test_2 old_test_3; do
    nexus-cli project delete $project --force
done
```

### Example 3: Conditional Deletion

```bash
# Delete only if project has no agents
agents=$(nexus-cli project describe my_project --output json | jq '.agent_count')
if [ "$agents" -eq 0 ]; then
    nexus-cli project delete my_project --force
else
    echo "Project has agents, skipping deletion"
fi
```

## Troubleshooting

### Project Not Found
```bash
$ nexus-cli project delete nonexistent_project
Error: Project 'nonexistent_project' not found
```

**Solution:** Check project name with `nexus-cli project list`

### Permission Denied
```bash
Error: Failed to delete directory projects/my_project/: Permission denied
```

**Solution:** Check file permissions:
```bash
ls -la projects/my_project/
chmod -R u+w projects/my_project/
```

### Partial Deletion
If deletion fails partway through, the CLI shows what was successfully deleted:
```
✓ Deleted agents: agents/generated_agents/my_project/
✓ Deleted prompts: prompts/generated_agents_prompts/my_project/
Error: Failed to delete tools/generated_tools/my_project/
```

**Solution:** Manually check and clean up remaining directories

## Recovery

### If You Deleted by Mistake

Unfortunately, deletion is **permanent**. However:

1. **Check backups** if you created them
2. **Regenerate the project** using the original requirements
3. **Restore from version control** if the project was committed

### Prevention

- Always use `--dry-run` first
- Create backups of important projects
- Use version control (git) for project files
- Consider archiving instead of deleting

## Related Commands

```bash
# List all projects
nexus-cli project list

# Describe project before deletion
nexus-cli project describe <name>

# Initialize new project
nexus-cli project init <name>
```

## Version History

- **v1.0.4** - Enhanced deletion to remove all related resources
- **v1.0.3** - Removed status display
- **v1.0.2** - Added tools_dependencies tracking
- **v1.0.1** - Added resource counts
- **v1.0.0** - Initial release

---

**Last Updated:** 2024-11-24  
**CLI Version:** 1.0.4
