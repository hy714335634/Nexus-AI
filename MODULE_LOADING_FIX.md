# Module Loading Fix - Without Code Changes

## Problem

Agent scripts fail with:
```
ModuleNotFoundError: No module named 'nexus_utils.workflow_rule_extract'
```

## Solution: Use Wrapper Script (No Code Changes Required)

Instead of modifying agent code, use the provided wrapper script that sets up the environment correctly.

### Method 1: Use run_agent.sh (Recommended)

```bash
# Make it executable (first time only)
chmod +x run_agent.sh

# Run any agent script
./run_agent.sh agents/system_agents/magician.py
./run_agent.sh agents/system_agents/agent_build_workflow/agent_build_workflow.py
```

The wrapper script:
- Sets `PYTHONPATH` to include Nexus-AI root
- Sets required environment variables
- Runs the agent with proper configuration

### Method 2: Set PYTHONPATH Manually

```bash
# From Nexus-AI root directory
export PYTHONPATH=$(pwd):$PYTHONPATH
export BYPASS_TOOL_CONSENT=true

# Now run agents
python3 agents/system_agents/magician.py
python3 agents/system_agents/agent_build_workflow/agent_build_workflow.py
```

### Method 3: Run from Nexus-AI Root with Python -m

```bash
# From Nexus-AI root directory
python3 -m agents.system_agents.magician
python3 -m agents.system_agents.agent_build_workflow.agent_build_workflow
```

### Method 4: Add to Shell Profile (Permanent)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Nexus-AI environment setup
export NEXUS_AI_ROOT="/path/to/Nexus-AI"
export PYTHONPATH="${NEXUS_AI_ROOT}:${PYTHONPATH}"
export BYPASS_TOOL_CONSENT=true

# Alias for running agents
alias run-agent='python3'
```

Then reload:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

Now you can run from anywhere:
```bash
run-agent /path/to/Nexus-AI/agents/system_agents/magician.py
```

## Why This Approach?

✅ **No code changes** - Agent files remain unchanged  
✅ **Clean separation** - Environment setup separate from code  
✅ **Flexible** - Multiple ways to run agents  
✅ **Maintainable** - Easy to update environment without touching code  
✅ **Standard practice** - Following Python best practices  

## Quick Start

```bash
# 1. Navigate to Nexus-AI directory
cd /path/to/Nexus-AI

# 2. Use the wrapper script
./run_agent.sh agents/system_agents/magician.py

# Or set environment and run directly
export PYTHONPATH=$(pwd):$PYTHONPATH
python3 agents/system_agents/magician.py
```

## Troubleshooting

### Still getting ModuleNotFoundError?

**Check 1: Verify you're in Nexus-AI root**
```bash
pwd  # Should show /path/to/Nexus-AI
ls   # Should show agents/, nexus_utils/, prompts/, etc.
```

**Check 2: Verify PYTHONPATH is set**
```bash
echo $PYTHONPATH  # Should include /path/to/Nexus-AI
```

**Check 3: Test module import**
```bash
python3 -c "from nexus_utils import workflow_rule_extract; print('OK')"
```

### Module 'yaml' not found?

Install dependencies:
```bash
pip3 install pyyaml click tabulate boto3
```

## For Development

If you're developing and running agents frequently, create an alias:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias nexus-run='PYTHONPATH=/path/to/Nexus-AI:$PYTHONPATH BYPASS_TOOL_CONSENT=true python3'

# Usage
nexus-run agents/system_agents/magician.py
```

## Alternative: Install as Package

For a permanent solution, install Nexus-AI as a package:

```bash
cd /path/to/Nexus-AI
pip3 install -e .
```

This requires creating a `setup.py` file (see PYTHON_PATH_FIX.md for details).

---

**Status**: ✅ Solution provided without code changes  
**Date**: 2024-11-24  
**Approach**: Environment-based solution
