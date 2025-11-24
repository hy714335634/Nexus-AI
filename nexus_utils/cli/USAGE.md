# Nexus-AI CLI - Usage Guide

## Quick Start

The Nexus-AI CLI is a kubectl-style command-line tool for managing your Nexus-AI backend resources.

### Running the CLI

From the Nexus-AI root directory:

```bash
python3 -c "import sys; sys.path.insert(0, '.'); from nexus_utils.cli.main import main; main()" [command]
```

Or create an alias for convenience:

```bash
alias nexus-cli="python3 -c \"import sys; sys.path.insert(0, '.'); from nexus_utils.cli.main import main; main()\""
```

Then use it like:

```bash
nexus-cli project list
nexus-cli agents list
nexus-cli overview
```

## Commands Reference

### Project Commands

#### List all projects
```bash
nexus-cli project list
nexus-cli project list --output json
nexus-cli project list --output text
```

**Output includes:**
- Project name
- Status (pending, initialized, completed, failed)
- Agent count
- Template count
- Prompt count
- Tool count
- Creation date

#### Describe a project
```bash
nexus-cli project describe <project-name>
nexus-cli project describe aws_pricing_agent
nexus-cli project describe aws_pricing_agent --output json
```

**Shows:**
- Basic information (name, status, timestamps, progress)
- All resources (agents, templates, prompts, tools)
- Workflow stages and their status

#### Initialize a new project
```bash
nexus-cli project init <project-name>
nexus-cli project init my_agent --description "My custom agent"
nexus-cli project init test_project --dry-run
```

**Creates:**
- Project directory structure
- Configuration files (config.yaml, status.yaml)
- README.md file

#### Delete a project
```bash
nexus-cli project delete <project-name>
nexus-cli project delete old_project --force
nexus-cli project delete test_project --dry-run
```

**Options:**
- `--force, -f`: Skip confirmation prompt
- `--dry-run`: Preview what would be deleted

### Agent Commands

#### List all agents
```bash
nexus-cli agents list
nexus-cli agents list --project aws_pricing_agent
nexus-cli agents list --output json
```

**Output includes:**
- Agent name
- Associated project
- Number of tools
- Creation date

#### Describe an agent
```bash
nexus-cli agents describe <agent-name>
nexus-cli agents describe aws_pricing_agent
nexus-cli agents describe clinical_medicine_expert --output json
```

**Shows:**
- Agent name and path
- Associated project
- Configuration (description, category, version)
- Tool dependencies
- Supported models

### Global Commands

#### System overview
```bash
nexus-cli overview
nexus-cli overview --output json
```

**Shows:**
- Total counts (projects, agents, templates, prompts, tools)
- Project status distribution
- System health summary

## Output Formats

All list and describe commands support three output formats:

### Table Format (Default)
Human-readable, formatted tables:
```bash
nexus-cli project list
```

### JSON Format
Machine-readable, structured data:
```bash
nexus-cli project list --output json
```

Perfect for:
- Programmatic consumption
- Piping to jq or other tools
- Automation scripts

### Text Format
Simple, space-separated values:
```bash
nexus-cli project list --output text
```

Perfect for:
- Shell scripting
- Parsing with awk/cut
- Simple automation

## Examples

### Example 1: List all projects with their resource counts
```bash
$ nexus-cli project list

NAME                                 STATUS         AGENTS    TEMPLATES    PROMPTS    TOOLS  CREATED
tech_doc_multi_agent_system          initialized         1            3          3        5  2025-11-24 10:02
aws_network_topology_analyzer        initialized         1            1          1       10  2025-11-24 10:02
aws_pricing_agent                    pending             0            1          1        1  2025-11-11 14:17

Total: 26 projects
```

### Example 2: Get detailed information about a project
```bash
$ nexus-cli project describe aws_pricing_agent

======================================================================
PROJECT: aws_pricing_agent
======================================================================

Basic Information:
  Name:        aws_pricing_agent
  Status:      pending
  Created:     2025-11-11 14:17:26
  Updated:     2025-11-11 14:17:26
  Progress:    0%

Resources:
  Agents:      0
  Templates:   1
    - aws_pricing_agent
  Prompts:     1
    - aws_pricing_agent
  Tools:       1
    - aws_pricing_tool

======================================================================
```

### Example 3: List agents for a specific project
```bash
$ nexus-cli agents list --project tech_doc_multi_agent_system

NAME                        PROJECT                          TOOLS  CREATED
content_processor_agent     tech_doc_multi_agent_system          0  2025-11-24
document_reviewer_agent     tech_doc_multi_agent_system          0  2025-11-24
document_writer_agent       tech_doc_multi_agent_system          0  2025-11-24

Total: 3 agents in project 'tech_doc_multi_agent_system'
```

### Example 4: Get system overview
```bash
$ nexus-cli overview

======================================================================
NEXUS-AI SYSTEM OVERVIEW
======================================================================

Resource Summary:
  Projects:   26
  Agents:     25
  Templates:  34
  Prompts:    34
  Tools:      89

Project Status Distribution:
  Initialized   12 (46%)
  Pending       14 (54%)
======================================================================
```

### Example 5: Create a new project (dry-run)
```bash
$ nexus-cli project init my_test_project --dry-run

[DRY RUN] Would perform the following operations:

✓ Create directory: projects/my_test_project/
✓ Create directory: projects/my_test_project/agents/
✓ Create file: projects/my_test_project/config.yaml
✓ Create file: projects/my_test_project/status.yaml
✓ Create file: projects/my_test_project/README.md

Run without --dry-run to execute these operations.
```

### Example 6: Export project list to JSON
```bash
$ nexus-cli project list --output json > projects.json
$ cat projects.json | jq '.projects[] | select(.status == "completed")'
```

### Example 7: Count projects by status
```bash
$ nexus-cli project list --output json | jq '.projects | group_by(.status) | map({status: .[0].status, count: length})'
```

## Advanced Usage

### Filtering and Processing

#### Find projects with more than 5 tools
```bash
nexus-cli project list --output json | jq '.projects[] | select(.tool_count > 5)'
```

#### List all agents without a project
```bash
nexus-cli agents list --output json | jq '.agents[] | select(.project == null)'
```

#### Get total tool count across all projects
```bash
nexus-cli project list --output json | jq '[.projects[].tool_count] | add'
```

### Shell Scripting

#### Backup all projects
```bash
#!/bin/bash
for project in $(nexus-cli project list --output text | awk '{print $1}'); do
    echo "Backing up $project..."
    tar -czf "backup_${project}.tar.gz" "projects/$project"
done
```

#### Generate HTML report
```bash
#!/bin/bash
echo "<html><body><h1>Nexus-AI Projects</h1>" > report.html
nexus-cli project list --output json | jq -r '.projects[] | "<p><b>\(.name)</b>: \(.status) - \(.agent_count) agents, \(.tool_count) tools</p>"' >> report.html
echo "</body></html>" >> report.html
```

## Tips & Best Practices

1. **Use --dry-run first**: Always test destructive operations with `--dry-run` before executing
2. **JSON for automation**: Use `--output json` when scripting or automating
3. **Create aliases**: Set up shell aliases for frequently used commands
4. **Pipe to jq**: Combine with jq for powerful JSON processing
5. **Check overview regularly**: Use `nexus-cli overview` to monitor system health

## Troubleshooting

### Command not found
Make sure you're in the Nexus-AI root directory and using the full Python command.

### Permission denied
Ensure you have read/write permissions for the projects directory.

### Module not found
Make sure all dependencies are installed:
```bash
pip install click pyyaml tabulate
```

### Empty output
Check that you're in the correct directory with `ls projects/`

## Getting Help

Get help for any command:

```bash
nexus-cli --help
nexus-cli project --help
nexus-cli agents --help
nexus-cli project list --help
```

## What's Next?

The CLI currently supports:
- ✅ Project management (list, describe, init, delete)
- ✅ Agent management (list, describe)
- ✅ System overview

Coming soon:
- Template management
- Prompt management
- Tool management
- Report generation (JSON/HTML)
- Dependency analysis
- Batch operations

## Feedback

Found a bug or have a feature request? Please report it to the Nexus-AI development team.
