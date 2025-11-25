# Nexus-AI CLI Help Documentation

> Complete reference for all CLI commands and options

## Table of Contents

- [Main CLI](#main-cli)
- [Project Commands](#project-commands)
- [Backup Commands](#backup-commands)
- [Agent Commands](#agent-commands)
- [System Commands](#system-commands)

---

## Main CLI

### Usage
```bash
nexus-cli [OPTIONS] COMMAND [ARGS]...
```

### Description
Nexus-AI Backend Management CLI - A kubectl-style CLI tool for managing Nexus-AI backend artifacts including Projects, Agents, Templates, Prompts, and Tools.

### Core Commands
- `project` - Manage projects (init, list, describe, backup, restore, delete)
- `agents` - Manage AI agents (list, describe)
- `backup` - Manage backups (list, describe, validate, delete)
- `overview` - Display system-wide overview

### Quick Start
```bash
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
```

### Backup & Restore Features
- Complete project backups with all resources (agents, prompts, tools)
- SHA-256 checksums for integrity verification
- Automatic safety backups before overwrite
- Project cloning by restoring to different name
- Dry-run mode for preview
- Detailed validation and error reporting

### Options
- `--version` - Show the version and exit
- `--base-path TEXT` - Base path to Nexus-AI installation
- `--help` - Show help message and exit

---

## Project Commands

### nexus-cli project

Manage Nexus-AI projects

#### Subcommands
- `init` - Create a new project
- `list` - List all projects
- `describe` - Show detailed project information
- `backup` - Create a backup of a project
- `restore` - Restore a project from backup
- `delete` - Delete a project and all resources

---

### nexus-cli project init

**Usage:** `nexus-cli project init [OPTIONS] NAME`

**Description:** Initialize a new project

**Arguments:**
- `NAME` - Project name (required)

**Options:**
- `-d, --description TEXT` - Project description
- `--dry-run` - Show what would be done without executing
- `--help` - Show help message

**Examples:**
```bash
# Create a new project
nexus-cli project init my-project

# Create with description
nexus-cli project init my-project --description "My AI project"

# Preview creation (dry-run)
nexus-cli project init my-project --dry-run
```

---

### nexus-cli project list

**Usage:** `nexus-cli project list [OPTIONS]`

**Description:** List all projects

**Options:**
- `-o, --output [json|table|text]` - Output format (default: table)
- `--help` - Show help message

**Examples:**
```bash
# List in table format (default)
nexus-cli project list

# List in JSON format
nexus-cli project list --output json

# List in plain text
nexus-cli project list --output text
```

---

### nexus-cli project describe

**Usage:** `nexus-cli project describe [OPTIONS] NAME`

**Description:** Describe a project in detail

**Arguments:**
- `NAME` - Project name (required)

**Options:**
- `-o, --output [json|table|text]` - Output format (default: text)
- `--help` - Show help message

**Examples:**
```bash
# Show project details
nexus-cli project describe my-project

# Get details in JSON format
nexus-cli project describe my-project --output json
```

---

### nexus-cli project backup

**Usage:** `nexus-cli project backup [OPTIONS] NAME`

**Description:** Backup a project with all its resources

Creates a complete backup of a project including:
- Project configuration and metadata
- All generated agents
- Agent prompts and configurations
- Custom tools and utilities
- SHA-256 checksums for integrity verification

The backup is saved as a compressed tar.gz archive with a timestamp:
`<project-name>_YYYYMMDD_HHMMSS.tar.gz`

**Arguments:**
- `NAME` - Project name (required)

**Options:**
- `-o, --output TEXT` - Custom output path for backup
- `--dry-run` - Show what would be done without executing
- `--help` - Show help message

**Features:**
- ✓ Complete resource backup (agents, prompts, tools)
- ✓ Integrity verification with SHA-256 checksums
- ✓ Compressed tar.gz format
- ✓ Timestamped filenames
- ✓ Detailed manifest with metadata
- ✓ Dry-run mode for preview

**Examples:**
```bash
# Basic backup
nexus-cli project backup my-project

# Backup to custom location
nexus-cli project backup my-project --output /path/to/backups/

# Preview backup (dry-run)
nexus-cli project backup my-project --dry-run
```

---

### nexus-cli project restore

**Usage:** `nexus-cli project restore [OPTIONS] NAME`

**Description:** Restore a project from backup

Restores a complete project from a backup archive including:
- Project configuration and metadata
- All agents with correct paths
- Agent prompts and configurations
- Custom tools and utilities

**Restore Options:**
1. Restore to original name (same as backup)
2. Restore to different name (project cloning)
3. Force overwrite existing project (with safety backup)

**Arguments:**
- `NAME` - Project name to restore to (required)

**Options:**
- `--from-backup TEXT` - Path to backup file (required)
- `-f, --force` - Overwrite existing project
- `--dry-run` - Show what would be done without executing
- `--help` - Show help message

**Safety Features:**
- ✓ Automatic backup validation before restore
- ✓ Checksum verification for all files
- ✓ Safety backup created before overwrite (with --force)
- ✓ Confirmation prompt for destructive operations
- ✓ Dry-run mode for preview
- ✓ Automatic path mapping for project cloning

**Use Cases:**
- Version Control: Restore previous project version
- Project Cloning: Create dev copy from production
- Migration: Move projects between systems
- Disaster Recovery: Restore after data loss

**Examples:**
```bash
# Restore to original name
nexus-cli project restore my-project --from-backup backups/my-project_20241125.tar.gz

# Clone project (restore to different name)
nexus-cli project restore dev-project --from-backup backups/prod-project_20241125.tar.gz

# Force overwrite existing project
nexus-cli project restore my-project --from-backup backup.tar.gz --force

# Preview restore (dry-run)
nexus-cli project restore my-project --from-backup backup.tar.gz --dry-run
```

---

### nexus-cli project delete

**Usage:** `nexus-cli project delete [OPTIONS] NAME`

**Description:** Delete a project and all related resources

**Arguments:**
- `NAME` - Project name (required)

**Options:**
- `-f, --force` - Skip confirmation
- `--dry-run` - Show what would be done without executing
- `--help` - Show help message

**Examples:**
```bash
# Delete with confirmation
nexus-cli project delete my-project

# Force delete (no confirmation)
nexus-cli project delete my-project --force

# Preview deletion (dry-run)
nexus-cli project delete my-project --dry-run
```

---

## Backup Commands

### nexus-cli backup

Manage project backups

#### Subcommands
- `list` - List all available backups
- `describe` - Show detailed backup information
- `validate` - Verify backup integrity
- `delete` - Delete a backup file

#### Backup Features
- Complete project snapshots with all resources
- SHA-256 checksums for integrity verification
- Compressed tar.gz format for efficient storage
- Detailed manifests with metadata
- Automatic validation and error detection
- Support for project cloning via restore

#### Backup Structure
Each backup contains:
- `manifest.json` - Metadata and checksums
- `projects/<name>/` - Project configuration
- `agents/generated_agents/<name>/` - Agent implementations
- `prompts/generated_agents_prompts/<name>/` - Agent prompts
- `tools/generated_tools/<name>/` - Custom tools

---

### nexus-cli backup list

**Usage:** `nexus-cli backup list [OPTIONS]`

**Description:** List all available backups

Shows all backup files in the backups directory with:
- Backup filename
- Associated project name
- File size (human-readable)
- Creation timestamp

**Options:**
- `-o, --output [json|table|text]` - Output format (default: table)
- `--help` - Show help message

**Examples:**
```bash
# List in table format (default)
nexus-cli backup list

# List in JSON format (for scripting)
nexus-cli backup list --output json

# List in plain text
nexus-cli backup list --output text
```

---

### nexus-cli backup describe

**Usage:** `nexus-cli backup describe [OPTIONS] NAME`

**Description:** Show detailed backup information

Displays comprehensive information about a backup including:
- Basic metadata (project, size, creation date)
- Manifest details (version, file count)
- Resource breakdown (agents, prompts, tools)
- Integrity status (checksums, validation)

**Arguments:**
- `NAME` - Backup filename (required)

**Options:**
- `-o, --output [json|table|text]` - Output format (default: text)
- `--help` - Show help message

**Examples:**
```bash
# Show backup details
nexus-cli backup describe my-project_20241125_143022.tar.gz

# Get details in JSON format
nexus-cli backup describe backup.tar.gz --output json
```

---

### nexus-cli backup validate

**Usage:** `nexus-cli backup validate [OPTIONS] PATH`

**Description:** Validate backup integrity

Performs comprehensive validation of a backup file:
- Archive format verification (tar.gz)
- Manifest presence and validity
- SHA-256 checksum verification for all files
- Path structure validation
- Version compatibility check

**Use this command to:**
- Verify backup before restore
- Check for corruption
- Validate after transfer/copy
- Ensure backup is restorable

**Arguments:**
- `PATH` - Path to backup file (required)

**Options:**
- `--help` - Show help message

**Validation Checks:**
- ✓ Archive structure (tar.gz format)
- ✓ Manifest file (presence and format)
- ✓ Checksums (SHA-256 for all files)
- ✓ Resource paths (validity and security)
- ✓ Version compatibility
- ✓ No corruption detected

**Examples:**
```bash
# Validate a backup
nexus-cli backup validate backups/my-project_20241125.tar.gz

# Validate before restore
nexus-cli backup validate backup.tar.gz
nexus-cli project restore my-project --from-backup backup.tar.gz
```

---

### nexus-cli backup delete

**Usage:** `nexus-cli backup delete [OPTIONS] NAME`

**Description:** Delete a backup file

Permanently removes a backup file from the backups directory.

**WARNING:** This operation cannot be undone!

**Arguments:**
- `NAME` - Backup filename (required)

**Options:**
- `-f, --force` - Skip confirmation
- `--help` - Show help message

**Safety:**
- Confirmation prompt (unless --force)
- Shows backup details before deletion
- Only deletes the specified backup file
- Does not affect the original project

**Examples:**
```bash
# Delete with confirmation prompt
nexus-cli backup delete old-backup.tar.gz

# Force delete (no confirmation)
nexus-cli backup delete old-backup.tar.gz --force

# Clean up old backups
nexus-cli backup list
nexus-cli backup delete my-project_20241001.tar.gz
```

---

## Agent Commands

### nexus-cli agents list

**Usage:** `nexus-cli agents list [OPTIONS]`

**Description:** List all agents

**Options:**
- `-p, --project TEXT` - Filter by project
- `-o, --output [json|table|text]` - Output format (default: table)
- `--help` - Show help message

**Examples:**
```bash
# List all agents
nexus-cli agents list

# Filter by project
nexus-cli agents list --project my-project

# List in JSON format
nexus-cli agents list --output json
```

---

### nexus-cli agents describe

**Usage:** `nexus-cli agents describe [OPTIONS] NAME`

**Description:** Describe an agent in detail

**Arguments:**
- `NAME` - Agent name (required)

**Options:**
- `-o, --output [json|table|text]` - Output format (default: text)
- `--help` - Show help message

**Examples:**
```bash
# Show agent details
nexus-cli agents describe my-agent

# Get details in JSON format
nexus-cli agents describe my-agent --output json
```

---

## System Commands

### nexus-cli overview

**Usage:** `nexus-cli overview [OPTIONS]`

**Description:** Display system-wide overview

Shows summary of all resources:
- Total projects
- Total agents
- Total templates
- Total prompts
- Total tools

**Options:**
- `-o, --output [json|table|text]` - Output format (default: table)
- `--help` - Show help message

**Examples:**
```bash
# Show system overview
nexus-cli overview

# Get overview in JSON format
nexus-cli overview --output json
```

---

## Common Workflows

### Daily Backup
```bash
# Backup a project
nexus-cli project backup production-agent

# List backups
nexus-cli backup list

# Validate backup
nexus-cli backup validate backups/production-agent_*.tar.gz
```

### Project Cloning
```bash
# Backup production project
nexus-cli project backup production-agent

# Create development copy
nexus-cli project restore dev-agent --from-backup backups/production-agent_*.tar.gz
```

### Disaster Recovery
```bash
# Validate backup
nexus-cli backup validate backups/critical-project_*.tar.gz

# Restore project
nexus-cli project restore critical-project --from-backup backups/critical-project_*.tar.gz
```

### Migration
```bash
# On source machine
nexus-cli project backup my-project --output /shared/backups/

# On target machine
nexus-cli project restore my-project --from-backup /shared/backups/my-project_*.tar.gz
```

---

## Tips & Best Practices

### Output Formats
All list commands support multiple output formats:
- `table` - Human-readable table (default)
- `json` - Machine-readable JSON (for scripting)
- `text` - Plain text (simple output)

### Dry-Run Mode
Use `--dry-run` to preview operations without executing:
```bash
nexus-cli project backup my-project --dry-run
nexus-cli project restore my-project --from-backup backup.tar.gz --dry-run
nexus-cli project delete my-project --dry-run
```

### Force Operations
Use `--force` to skip confirmation prompts:
```bash
nexus-cli project delete my-project --force
nexus-cli backup delete old-backup.tar.gz --force
nexus-cli project restore my-project --from-backup backup.tar.gz --force
```

### Scripting
Use JSON output for scripting:
```bash
# Get all projects as JSON
nexus-cli project list --output json

# Get all backups as JSON
nexus-cli backup list --output json

# Get project details as JSON
nexus-cli project describe my-project --output json
```

---

## Getting Help

For any command, use `--help` to see detailed information:

```bash
# General help
nexus-cli --help

# Command-specific help
nexus-cli project --help
nexus-cli backup --help
nexus-cli agents --help

# Subcommand help
nexus-cli project backup --help
nexus-cli project restore --help
nexus-cli backup validate --help
```

---

**Version:** 2.1.0  
**Documentation:** See README.md for comprehensive guide  
**Support:** For issues and questions, see TROUBLESHOOTING.md
