# Python Environment Management

## Virtual Environment Activation

When executing Python commands in this project, ALWAYS activate the virtual environment first.

### Required Command Pattern

For ANY Python execution, use this pattern:

```bash
source venv/bin/activate && python [your_command]
```

### Examples

- Running a script: `source venv/bin/activate && python script.py`
- Running with arguments: `source venv/bin/activate && python script.py arg1 arg2`
- Running modules: `source venv/bin/activate && python -m module_name`
- Interactive Python: `source venv/bin/activate && python`

### Rules

1. **NEVER** run `python` directly without first activating the virtual environment
2. **ALWAYS** use `source venv/bin/activate &&` as a prefix to any Python command
3. This applies to ALL Python executions including:
   - Running scripts
   - Installing packages with pip
   - Running tests
   - Interactive Python sessions
   - Module executions

### Rationale

This ensures:

- Consistent dependency management
- Isolation from system Python
- Access to project-specific packages
- Reproducible execution environment
