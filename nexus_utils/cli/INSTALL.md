# Nexus-AI CLI - Installation Guide

## Prerequisites

- Python 3.13+ (or Python 3.8+)
- Nexus-AI installation
- Required Python packages: click, pyyaml, tabulate

## Installation

The CLI is already integrated into your Nexus-AI installation. No separate installation needed!

## Setup

### Option 1: Create a Shell Alias (Recommended)

Add this to your `~/.bashrc` or `~/.zshrc`:

```bash
alias nexus-cli='python3 -c "import sys; sys.path.insert(0, \".\"); from nexus_utils.cli.main import main; main()"'
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

Now you can use:

```bash
nexus-cli project list
nexus-cli agents list
nexus-cli overview
```

### Option 2: Create a Wrapper Script

Create a file `~/bin/nexus-cli`:

```bash
#!/bin/bash
NEXUS_ROOT="/path/to/Nexus-AI"
cd "$NEXUS_ROOT"
python3 -c "import sys; sys.path.insert(0, '.'); from nexus_utils.cli.main import main; main()" "$@"
```

Make it executable:

```bash
chmod +x ~/bin/nexus-cli
```

Add `~/bin` to your PATH if not already:

```bash
export PATH="$HOME/bin:$PATH"
```

### Option 3: Direct Python Execution

From the Nexus-AI root directory:

```bash
python3 -c "import sys; sys.path.insert(0, '.'); from nexus_utils.cli.main import main; main()" [command]
```

## Verify Installation

Test that the CLI works:

```bash
nexus-cli --version
nexus-cli --help
nexus-cli project list
```

Expected output:
```
Usage: nexus-cli [OPTIONS] COMMAND [ARGS]...

  Nexus-AI Backend Management CLI
  ...
```

## Dependencies

The CLI requires these Python packages:

```bash
pip install click>=8.1.7 pyyaml>=6.0.1 tabulate>=0.9.0
```

Or if using the Nexus-AI virtual environment:

```bash
source .venv/bin/activate  # Activate venv
pip install click pyyaml tabulate
```

## Troubleshooting

### "Module not found" error

Make sure you're in the Nexus-AI root directory:

```bash
cd /path/to/Nexus-AI
nexus-cli project list
```

### "Permission denied" error

Ensure you have read/write permissions:

```bash
ls -la projects/
```

### Dependencies missing

Install required packages:

```bash
pip install click pyyaml tabulate
```

## Quick Start

Once installed, try these commands:

```bash
# List all projects
nexus-cli project list

# Get project details
nexus-cli project describe aws_pricing_agent

# List all agents
nexus-cli agents list

# System overview
nexus-cli overview

# Get help
nexus-cli --help
```

## Next Steps

- Read [USAGE.md](./USAGE.md) for comprehensive usage guide
- Check [README.md](./README.md) for quick reference
- Review [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for technical details

## Uninstallation

To remove the CLI (if needed):

1. Remove the alias from your shell config
2. Delete the wrapper script (if created)
3. The CLI code remains in `nexus_utils/cli/` but won't be accessible

## Support

For issues or questions, refer to:
- [USAGE.md](./USAGE.md) - Detailed usage guide
- [README.md](./README.md) - Quick reference
- Nexus-AI documentation

---

**Installation Date**: 2024-11-24  
**CLI Version**: 1.0.0
