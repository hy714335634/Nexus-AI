#!/usr/bin/env python3
"""
Script to add Python path setup to all agent files that import nexus_utils
"""

import os
import re
from pathlib import Path

# Path setup code to add
PATH_SETUP_CODE = """
# Add Nexus-AI root directory to Python path
import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
nexus_root = os.path.dirname(os.path.dirname(script_dir))
if nexus_root not in sys.path:
    sys.path.insert(0, nexus_root)
"""

def needs_path_setup(content: str) -> bool:
    """Check if file needs path setup"""
    # Check if it imports nexus_utils
    if 'from nexus_utils' not in content and 'import nexus_utils' not in content:
        return False
    
    # Check if it already has path setup
    if 'sys.path.insert' in content or 'PYTHONPATH' in content:
        return False
    
    return True

def add_path_setup(file_path: Path):
    """Add path setup to a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not needs_path_setup(content):
        print(f"  ⏭️  Skipping {file_path.name} (already has path setup or doesn't need it)")
        return False
    
    # Find the position after shebang and docstring
    lines = content.split('\n')
    insert_pos = 0
    
    # Skip shebang
    if lines[0].startswith('#!'):
        insert_pos = 1
    
    # Skip docstring
    in_docstring = False
    for i in range(insert_pos, len(lines)):
        line = lines[i].strip()
        if line.startswith('"""') or line.startswith("'''"):
            if in_docstring:
                insert_pos = i + 1
                break
            else:
                in_docstring = True
        elif not in_docstring and line and not line.startswith('#'):
            insert_pos = i
            break
    
    # Insert path setup code
    lines.insert(insert_pos, PATH_SETUP_CODE)
    
    # Write back
    new_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  ✅ Fixed {file_path.name}")
    return True

def main():
    """Main function"""
    print("🔍 Scanning for Python files that need path setup...\n")
    
    # Directories to scan
    scan_dirs = [
        'agents/system_agents',
        'agents/generated_agents',
    ]
    
    fixed_count = 0
    
    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
        
        print(f"📁 Scanning {scan_dir}/")
        
        for root, dirs, files in os.walk(scan_dir):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    file_path = Path(root) / file
                    if add_path_setup(file_path):
                        fixed_count += 1
    
    print(f"\n✨ Done! Fixed {fixed_count} files.")
    print("\nYou can now run agent files directly:")
    print("  python3 agents/system_agents/magician.py")
    print("  python3 agents/system_agents/agent_build_workflow/agent_build_workflow.py")

if __name__ == '__main__':
    main()
