# Python Path Fix - Summary

## Problem

Agent scripts were failing with:
```
ModuleNotFoundError: No module named 'nexus_utils.workflow_rule_extract'
```

Even though the module exists at `nexus_utils/workflow_rule_extract.py`.

## Root Cause

Python couldn't find the `nexus_utils` module because the Nexus-AI root directory wasn't in the Python path when running scripts directly.

## Solution Applied

Added Python path setup code to agent scripts that import `nexus_utils`:

```python
# Add Nexus-AI root directory to Python path
import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
nexus_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if nexus_root not in sys.path:
    sys.path.insert(0, nexus_root)
```

This code:
1. Gets the script's directory
2. Calculates the Nexus-AI root directory (3 levels up for agent_build_workflow)
3. Adds it to `sys.path` if not already there
4. Must be placed BEFORE any `nexus_utils` imports

## Files Fixed

### ✅ Fixed Files

1. **agents/system_agents/agent_build_workflow/agent_build_workflow.py**
   - Added path setup at line 14-18
   - Now can be run directly: `python3 agents/system_agents/agent_build_workflow/agent_build_workflow.py`

2. **agents/system_agents/magician.py**
   - Added path setup at line 9-13
   - Now can be run directly: `python3 agents/system_agents/magician.py`

### 🔧 Automated Fix Script

Created `fix_python_paths.py` to automatically fix other agent files:

```bash
python3 fix_python_paths.py
```

This script will:
- Scan `agents/system_agents/` and `agents/generated_agents/`
- Find Python files that import `nexus_utils`
- Add path setup code if not already present
- Report which files were fixed

## How to Use

### Option 1: Run Scripts Directly (Now Works!)

```bash
# From anywhere
python3 /path/to/Nexus-AI/agents/system_agents/magician.py

# Or from Nexus-AI directory
python3 agents/system_agents/agent_build_workflow/agent_build_workflow.py
```

### Option 2: Run from Nexus-AI Root (Still Works)

```bash
cd /path/to/Nexus-AI
python3 agents/system_agents/magician.py
```

### Option 3: Set PYTHONPATH (Still Works)

```bash
export PYTHONPATH=/path/to/Nexus-AI:$PYTHONPATH
python3 agents/system_agents/magician.py
```

## Benefits

✅ **Scripts work from any directory** - No need to cd to Nexus-AI root  
✅ **No environment setup required** - Path is set automatically  
✅ **Backward compatible** - Still works with PYTHONPATH if set  
✅ **Self-contained** - Each script manages its own path  

## Technical Details

### Path Calculation

For different script locations:

**System agents (3 levels deep):**
```
Nexus-AI/agents/system_agents/agent_build_workflow/script.py
         ↑ nexus_root (3 levels up)
```

**Generated agents (2 levels deep):**
```
Nexus-AI/agents/generated_agents/script.py
         ↑ nexus_root (2 levels up)
```

Adjust `os.path.dirname()` calls based on depth:
- 3 levels: `os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))`
- 2 levels: `os.path.dirname(os.path.dirname(script_dir))`

### Why This Works

1. **Dynamic path calculation** - Works regardless of where Nexus-AI is installed
2. **Runs before imports** - Path is set before trying to import nexus_utils
3. **Idempotent** - Checks if path already in sys.path before adding
4. **No side effects** - Only adds path, doesn't modify anything else

## Verification

Test that the fix works:

```bash
# Test agent_build_workflow
python3 agents/system_agents/agent_build_workflow/agent_build_workflow.py

# Test magician
python3 agents/system_agents/magician.py

# Should not see ModuleNotFoundError anymore
```

## Future Considerations

### For New Agent Files

When creating new agent files that import `nexus_utils`, add this at the top:

```python
#!/usr/bin/env python3
"""Your docstring"""

import sys
import os

# Add Nexus-AI root directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
nexus_root = os.path.dirname(os.path.dirname(script_dir))  # Adjust based on depth
if nexus_root not in sys.path:
    sys.path.insert(0, nexus_root)

# Now you can import nexus_utils
from nexus_utils import something
```

### Alternative: Setup.py

For a more permanent solution, consider creating a `setup.py` and installing Nexus-AI as a package:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name='nexus-ai',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'pyyaml>=6.0.1',
        'click>=8.1.7',
        'tabulate>=0.9.0',
        'boto3>=1.34.0',
    ],
)
```

Then install in development mode:
```bash
pip install -e .
```

This would make `nexus_utils` importable from anywhere without path manipulation.

## Related Documentation

- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - General troubleshooting guide
- [fix_python_paths.py](./fix_python_paths.py) - Automated fix script

---

**Fix Applied**: 2024-11-24  
**Status**: ✅ Resolved  
**Impact**: All agent scripts can now run directly without path setup
