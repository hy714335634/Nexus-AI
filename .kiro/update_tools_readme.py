#!/usr/bin/env python3
"""
Auto-update script for tools/system_tools/README_tools.md
This script analyzes all Python files in tools/system_tools and updates the README with current tool information.
"""

import os
import ast
import re
import json
from datetime import datetime
from pathlib import Path

def extract_tools_from_file(file_path):
    """Extract @tool decorated functions from a Python file."""
    tools = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has @tool decorator
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Name) and decorator.id == 'tool') or \
                       (isinstance(decorator, ast.Attribute) and decorator.attr == 'tool'):
                        
                        # Extract docstring
                        docstring = ast.get_docstring(node) or ""
                        
                        # Extract function name
                        func_name = node.name
                        
                        # Parse docstring for description
                        description = ""
                        if docstring:
                            lines = docstring.strip().split('\n')
                            description = lines[0] if lines else ""
                        
                        tools.append({
                            'name': func_name,
                            'description': description
                        })
                        break
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    
    return tools

def get_file_description(file_path):
    """Extract file-level description from docstring or comments."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to get module docstring
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)
        
        if docstring:
            lines = docstring.strip().split('\n')
            return lines[0] if lines else ""
        
        # Fallback to first comment
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('"""') and line.endswith('"""') and len(line) > 6:
                return line[3:-3].strip()
            elif line.startswith('#') and len(line) > 2:
                return line[1:].strip()
    
    except Exception as e:
        print(f"Error reading description from {file_path}: {e}")
    
    return "系统工具"

def generate_readme_content():
    """Generate the complete README content."""
    tools_dir = Path("tools/system_tools")
    
    # Get all Python files except __pycache__ and README
    python_files = []
    for file_path in tools_dir.glob("*.py"):
        if file_path.name not in ["__init__.py", "README_tools.py"]:
            python_files.append(file_path)
    
    # Sort files alphabetically
    python_files.sort(key=lambda x: x.name)
    
    # Analyze each file
    file_info = []
    for file_path in python_files:
        tools = extract_tools_from_file(file_path)
        description = get_file_description(file_path)
        
        file_info.append({
            'filename': file_path.name,
            'description': description,
            'tools': tools,
            'tool_count': len(tools)
        })
    
    # Generate README content
    content = """# System Tools 系统工具

本目录包含 Nexus-AI 平台的核心系统工具，为 Strands agents 提供完整的项目管理、模板管理、配置管理等功能。

## 📋 工具概览

| 工具文件 | 描述 | 工具数量 |
|---------|------|---------|
"""
    
    # Add table rows
    for i, info in enumerate(file_info, 1):
        anchor = f"#{i}-{info['filename'].replace('.py', '').replace('_', '')}"
        content += f"| [{info['filename']}]({anchor}) | {info['description']} | {info['tool_count']} |\n"
    
    content += "\n---\n\n"
    
    # Add detailed sections for each file
    for i, info in enumerate(file_info, 1):
        filename_no_ext = info['filename'].replace('.py', '')
        content += f"## {i}. {info['filename']}\n"
        content += f"> **{info['description']}**\n\n"
        content += "### 🔧 可用工具\n\n"
        
        for tool in info['tools']:
            content += f"- **`{tool['name']}`** - {tool['description']}\n"
        
        content += "\n---\n\n"
    
    # Add footer
    content += """## 📚 使用说明

1. **工具调用格式**: 所有工具都使用 `@tool` 装饰器，可被 Strands agents 直接调用
2. **返回格式**: 大部分工具返回 JSON 格式的结构化数据，便于程序处理
3. **错误处理**: 所有工具都包含完整的错误处理和参数验证
4. **文档完整**: 每个工具都有详细的文档字符串，说明参数和返回值

## 🔗 相关文档

- [Strands Framework 文档](https://docs.strands.ai/)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [AWS Bedrock 文档](https://docs.aws.amazon.com/bedrock/)

---

*最后更新: """ + datetime.now().strftime("%Y-%m-%d") + "*\n"
    
    return content

def main():
    """Main function to update the README."""
    try:
        # Generate new content
        new_content = generate_readme_content()
        
        # Write to README file
        readme_path = Path("tools/system_tools/README_tools.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Successfully updated {readme_path}")
        
    except Exception as e:
        print(f"❌ Error updating README: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())