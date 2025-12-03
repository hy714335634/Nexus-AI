# Nexus-AI CLI

> A powerful kubectl-style command-line interface for managing Nexus-AI projects, agents, and resources.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [Commands](#commands)
  - [Project Management](#project-management)
  - [Agent Management](#agent-management)
  - [Backup & Restore](#backup--restore)
  - [System Overview](#system-overview)
- [Advanced Features](#advanced-features)
- [Examples](#examples)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The Nexus-AI CLI provides a unified interface to manage your AI agent projects, including:

- 🚀 **Project Management** - Create, list, update, and delete projects
- 🤖 **Agent Management** - View and manage AI agents
- 💾 **Backup & Restore** - Protect your work with comprehensive backup capabilities
- 📊 **System Overview** - Monitor your entire Nexus-AI ecosystem
- 🔄 **Multiple Output Formats** - JSON, table, or text output for any workflow

## Quick Start

### Basic Commands

```bash
# List all projects
./nexus-cli project list

# View project details
./nexus-cli project describe my_project

# Create a backup
./nexus-cli project backup my_project

# Get system overview
./nexus-cli overview
```

### Common Workflows

```bash
# Create a new project
./nexus-cli project init my_agent --description "My custom agent"

# Backup before making changes
./nexus-cli project backup my_agent

# List all backups
./nexus-cli backup list

# Restore if needed
./nexus-cli project restore my_agent --from-backup backups/my_agent_20241125.tar.gz
```

## Installation

The CLI is integrated into Nexus-AI. No additional installation required!

### Prerequisites

- Python 3.9+
- Nexus-AI project installed

### Verify Installation

```bash
./nexus-cli --version
./nexus-cli --help
```

## Core Concepts

### Project Structure

A Nexus-AI project consists of four main components:

```
my_project/
├── projects/my_project/          # Project configuration and metadata
├── agents/generated_agents/my_project/     # Agent implementations
├── prompts/generated_agents_prompts/my_project/  # Prompt configurations
└── tools/generated_tools/my_project/       # Tool implementations
```

### Resource Types

- **Projects** - Top-level containers for your AI applications
- **Agents** - AI agents with specific capabilities
- **Prompts** - Configuration files for agent behavior
- **Tools** - Utilities and functions agents can use

## Commands

### Project Management

#### List Projects

```bash
# Table format (default)
./nexus-cli project list

# JSON format
./nexus-cli project list --output json

# Text format
./nexus-cli project list --output text
```

#### Describe Project

```bash
# View detailed project information
./nexus-cli project describe my_project

# JSON output for scripting
./nexus-cli project describe my_project --output json
```

#### Create Project

```bash
# Basic creation
./nexus-cli project init my_project

# With description
./nexus-cli project init my_project --description "My AI agent project"

# Preview without creating (dry-run)
./nexus-cli project init my_project --dry-run
```

#### Delete Project

```bash
# Interactive deletion (with confirmation)
./nexus-cli project delete my_project

# Force deletion (skip confirmation)
./nexus-cli project delete my_project --force

# Preview deletion
./nexus-cli project delete my_project --dry-run
```

### Agent Management

#### List Agents

```bash
# List all agents
./nexus-cli agents list

# Filter by project
./nexus-cli agents list --project my_project

# JSON output
./nexus-cli agents list --output json
```

#### Describe Agent

```bash
# View agent details
./nexus-cli agents describe my_agent

# JSON output
./nexus-cli agents describe my_agent --output json
```

### Backup & Restore

Protect your projects with comprehensive backup and restore capabilities.

#### Create Backup

```bash
# Backup a project
./nexus-cli project backup my_project

# Backup to custom location
./nexus-cli project backup my_project --output /path/to/backups/

# Preview backup (dry-run)
./nexus-cli project backup my_project --dry-run
```

**What gets backed up:**
- ✅ Project configuration and metadata
- ✅ All generated agents
- ✅ All prompt configurations
- ✅ All tools
- ✅ SHA-256 checksums for integrity verification

#### List Backups

```bash
# List all backups
./nexus-cli backup list

# JSON format
./nexus-cli backup list --output json
```

#### View Backup Details

```bash
# Show backup information
./nexus-cli backup describe my_project_20241125_143022.tar.gz

# JSON output
./nexus-cli backup describe my_project_20241125_143022.tar.gz --output json
```

#### Validate Backup

```bash
# Verify backup integrity
./nexus-cli backup validate backups/my_project_20241125_143022.tar.gz
```

**Validation checks:**
- ✅ Archive format and structure
- ✅ Manifest presence and validity
- ✅ SHA-256 checksum verification
- ✅ Resource path integrity

#### Restore Project

```bash
# Restore to original name
./nexus-cli project restore my_project --from-backup backups/my_project_20241125.tar.gz

# Restore to different name (clone project)
./nexus-cli project restore my_project_copy --from-backup backups/my_project_20241125.tar.gz

# Force restore (overwrite existing)
./nexus-cli project restore my_project --from-backup backup.tar.gz --force

# Preview restore
./nexus-cli project restore my_project --from-backup backup.tar.gz --dry-run
```

**Safety features:**
- 🔒 Automatic safety backup before overwrite
- ✅ Checksum verification during restore
- ⚠️ Conflict detection
- 🔄 Support for project renaming

#### Delete Backup

```bash
# Delete with confirmation
./nexus-cli backup delete my_project_20241125_143022.tar.gz

# Force delete (skip confirmation)
./nexus-cli backup delete my_project_20241125_143022.tar.gz --force
```

### System Overview

```bash
# View system-wide statistics
./nexus-cli overview

# JSON format
./nexus-cli overview --output json
```

**Shows:**
- Total projects
- Total agents
- Total templates
- Total prompts
- Total tools

## Advanced Features

### Output Formats

All commands support multiple output formats:

| Format | Use Case | Example |
|--------|----------|---------|
| `table` | Human-readable (default) | `--output table` |
| `json` | Programmatic/scripting | `--output json` |
| `text` | Simple text output | `--output text` |

### Dry-Run Mode

Preview operations without executing them:

```bash
# Preview project creation
./nexus-cli project init test --dry-run

# Preview backup
./nexus-cli project backup my_project --dry-run

# Preview restore
./nexus-cli project restore my_project --from-backup backup.tar.gz --dry-run

# Preview deletion
./nexus-cli project delete old_project --dry-run
```

### Force Mode

Skip confirmations for automation:

```bash
# Force delete without confirmation
./nexus-cli project delete my_project --force

# Force restore (overwrite existing)
./nexus-cli project restore my_project --from-backup backup.tar.gz --force

# Force backup deletion
./nexus-cli backup delete old_backup.tar.gz --force
```

## Examples

### Complete Project Workflow

```bash
# 1. Create a new project
./nexus-cli project init my_agent --description "Customer support agent"

# 2. View project details
./nexus-cli project describe my_agent

# 3. Create a backup before making changes
./nexus-cli project backup my_agent

# 4. Make changes to your project...
# (develop agents, modify prompts, etc.)

# 5. Create another backup
./nexus-cli project backup my_agent

# 6. List all backups
./nexus-cli backup list

# 7. If something goes wrong, restore
./nexus-cli project restore my_agent --from-backup backups/my_agent_20241125.tar.gz --force
```

### Backup Management Workflow

```bash
# Create backups for all important projects
./nexus-cli project backup production_agent
./nexus-cli project backup staging_agent

# List and verify backups
./nexus-cli backup list
./nexus-cli backup validate backups/production_agent_20241125.tar.gz

# Clone a project using backup
./nexus-cli project backup production_agent
./nexus-cli project restore development_agent --from-backup backups/production_agent_20241125.tar.gz

# Clean up old backups
./nexus-cli backup delete old_backup_20241001.tar.gz --force
```

### Scripting with JSON Output

```bash
# Get project count
./nexus-cli project list --output json | jq '.total'

# Get all project names
./nexus-cli project list --output json | jq '.projects[].name'

# Check backup size
./nexus-cli backup list --output json | jq '.backups[] | select(.project_name=="my_project") | .size_mb'

# Get system statistics
./nexus-cli overview --output json | jq '.summary'
```

### Automation Examples

```bash
# Backup all projects (bash script)
for project in $(./nexus-cli project list --output json | jq -r '.projects[].name'); do
    echo "Backing up $project..."
    ./nexus-cli project backup "$project"
done

# Validate all backups
for backup in backups/*.tar.gz; do
    echo "Validating $backup..."
    ./nexus-cli backup validate "$backup"
done
```

## Testing

### Run Tests

```bash
# Run all tests
cd nexus_utils/cli
python run_tests.py

# Run only backup tests
python run_tests.py backup

# Run quick integration tests
./quick_test.sh
```

### Test Coverage

- ✅ 14 unit tests for backup/restore
- ✅ 15 integration tests
- ✅ Path mapping tests
- ✅ Error handling tests
- ✅ 100% test pass rate

## Troubleshooting

### Common Issues

#### Command Not Found

```bash
# Make sure you're in the Nexus-AI root directory
cd /path/to/Nexus-AI

# Make the CLI executable
chmod +x nexus-cli

# Or use Python directly
python -m nexus_utils.cli.main --help
```

#### Backup Creation Fails

```bash
# Check permissions
ls -la projects/my_project/

# Ensure backup directory exists and is writable
mkdir -p backups
chmod 755 backups
```

#### Restore Fails with Checksum Error

```bash
# Validate the backup first
./nexus-cli backup validate backups/my_project.tar.gz

# If corrupted, try an older backup
./nexus-cli backup list
./nexus-cli project restore my_project --from-backup backups/my_project_older.tar.gz
```

#### Project Already Exists

```bash
# Use --force to overwrite (creates safety backup)
./nexus-cli project restore my_project --from-backup backup.tar.gz --force

# Or delete first
./nexus-cli project delete my_project --force
./nexus-cli project restore my_project --from-backup backup.tar.gz
```

### Getting Help

```bash
# General help
./nexus-cli --help

# Command-specific help
./nexus-cli project --help
./nexus-cli backup --help
./nexus-cli agents --help

# Subcommand help
./nexus-cli project backup --help
./nexus-cli project restore --help
```

### Debug Mode

```bash
# Set Python path for debugging
export PYTHONPATH=/path/to/Nexus-AI:$PYTHONPATH

# Run with Python for better error messages
python -m nexus_utils.cli.main project list
```

## Additional Resources

### Documentation

- **[BACKUP_QUICKSTART.md](BACKUP_QUICKSTART.md)** - Quick start guide for backup/restore
- **[BACKUP_USAGE.md](BACKUP_USAGE.md)** - Comprehensive backup usage guide
- **[BACKUP_IMPLEMENTATION.md](BACKUP_IMPLEMENTATION.md)** - Technical implementation details
- **[RESTORE_LOGIC_FIX.md](RESTORE_LOGIC_FIX.md)** - Restore logic and path mapping
- **[BACKUP_TESTS_SUMMARY.md](BACKUP_TESTS_SUMMARY.md)** - Test documentation

### Architecture

```
nexus_utils/cli/
├── main.py                 # CLI entry point
├── managers/              # Business logic
│   ├── project_manager.py # Project & backup operations
│   ├── agent_manager.py   # Agent operations
│   └── base.py           # Base manager class
├── models/               # Data models
│   ├── project.py       # Project models
│   ├── backup.py        # Backup models
│   ├── agent.py         # Agent models
│   └── common.py        # Common models
├── adapters/            # External interfaces
│   ├── filesystem.py    # File operations
│   └── config_loader.py # Configuration
├── utils/              # Utilities
│   └── formatters.py   # Output formatting
└── tests/             # Test suite
    ├── test_backup_restore.py
    ├── test_project_manager.py
    └── test_cli_integration.py
```

### Dependencies

```
click >= 8.1.7          # CLI framework
pyyaml >= 6.0.1         # YAML parsing
tabulate >= 0.9.0       # Table formatting
```

## Contributing

When adding new features:

1. Update relevant manager classes
2. Add CLI commands in `main.py`
3. Write unit tests
4. Update this README
5. Run test suite: `python run_tests.py`

## Version

Current version: **1.0.0**

## License

Part of the Nexus-AI project.

---

**Need help?** Run `./nexus-cli --help` or check the documentation files listed above.

**Found a bug?** Please report it with details about your environment and the command that failed.

**Want a feature?** Suggestions are welcome! Describe your use case and we'll consider it.
