# Nexus-AI CLI

A kubectl-style CLI tool for managing Nexus-AI backend artifacts.

## Installation

The CLI is already integrated into the Nexus-AI project. No additional installation needed.

## Usage

From the Nexus-AI root directory:

```bash
./nexus-cli [command] [options]
```

Or using Python:

```bash
python -m nexus_utils.cli.main [command] [options]
```

## Quick Start

### List all projects
```bash
./nexus-cli project list
```

### Describe a project
```bash
./nexus-cli project describe aws_pricing_agent
```

### List all agents
```bash
./nexus-cli agents list
```

### System overview
```bash
./nexus-cli overview
```

## Available Commands

### Project Commands
- `project list` - List all projects
- `project describe <name>` - Show detailed project information
- `project init <name>` - Initialize a new project
- `project delete <name>` - Delete a project

### Agent Commands
- `agents list` - List all agents
- `agents describe <name>` - Show detailed agent information

### Global Commands
- `overview` - Display system-wide overview

## Output Formats

All list and describe commands support multiple output formats:

- `--output table` (default) - Human-readable table format
- `--output json` - JSON format for programmatic use
- `--output text` - Plain text format for scripting

Example:
```bash
./nexus-cli project list --output json
```

## Dry-Run Mode

Modification commands support dry-run mode to preview changes:

```bash
./nexus-cli project init my_project --dry-run
./nexus-cli project delete old_project --dry-run
```

## Examples

### Create a new project
```bash
./nexus-cli project init my_agent --description "My custom agent"
```

### List projects with JSON output
```bash
./nexus-cli project list --output json
```

### List agents for a specific project
```bash
./nexus-cli agents list --project aws_pricing_agent
```

### Get system overview
```bash
./nexus-cli overview
```

## Help

Get help for any command:

```bash
./nexus-cli --help
./nexus-cli project --help
./nexus-cli agents --help
```

## Dependencies

The CLI requires the following Python packages:
- click >= 8.1.7
- pyyaml >= 6.0.1
- tabulate >= 0.9.0

These should already be installed as part of the Nexus-AI project dependencies.
