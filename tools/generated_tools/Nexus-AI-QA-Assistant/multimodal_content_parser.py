#!/usr/bin/env python3
"""
Multimodal Content Parser Tool for Nexus-AI-QA-Assistant

This tool provides comprehensive content parsing capabilities for various file formats
including Markdown, YAML, JSON, and Python code. It extracts structured information
and provides intelligent content analysis for the QA assistant.

Author: Nexus-AI Tools Developer
Date: 2025-11-11
Version: 1.0.0
"""

import json
import re
import ast
import yaml
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from strands import tool


@tool
def parse_markdown_content(
    content: str,
    extract_structure: bool = True,
    extract_code_blocks: bool = True,
    extract_links: bool = True
) -> str:
    """
    Parse Markdown content and extract structured information.
    
    This tool analyzes Markdown documents and extracts:
    - Document structure (headings hierarchy)
    - Code blocks with language tags
    - Links and references
    - Lists and tables
    - Metadata (if present)
    
    Args:
        content (str): Markdown content to parse
        extract_structure (bool): Whether to extract document structure tree
        extract_code_blocks (bool): Whether to extract code blocks
        extract_links (bool): Whether to extract links and references
    
    Returns:
        str: JSON string containing parsed Markdown structure
    
    Example:
        >>> result = parse_markdown_content("# Title\\n## Section\\nContent here")
        >>> data = json.loads(result)
        >>> print(data['structure'])
    """
    try:
        result = {
            "status": "success",
            "content_type": "markdown",
            "total_length": len(content),
            "line_count": len(content.splitlines())
        }
        
        # Extract document structure (headings)
        if extract_structure:
            structure = []
            heading_pattern = r'^(#{1,6})\s+(.+)$'
            
            for line_num, line in enumerate(content.splitlines(), 1):
                match = re.match(heading_pattern, line)
                if match:
                    level = len(match.group(1))
                    title = match.group(2).strip()
                    structure.append({
                        "level": level,
                        "title": title,
                        "line_number": line_num
                    })
            
            result["structure"] = structure
            result["heading_count"] = len(structure)
        
        # Extract code blocks
        if extract_code_blocks:
            code_blocks = []
            code_pattern = r'```(\w+)?\n(.*?)```'
            
            for match in re.finditer(code_pattern, content, re.DOTALL):
                language = match.group(1) or "unknown"
                code = match.group(2).strip()
                code_blocks.append({
                    "language": language,
                    "code": code,
                    "line_count": len(code.splitlines())
                })
            
            result["code_blocks"] = code_blocks
            result["code_block_count"] = len(code_blocks)
        
        # Extract links
        if extract_links:
            links = []
            # Markdown link pattern: [text](url)
            link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
            
            for match in re.finditer(link_pattern, content):
                text = match.group(1)
                url = match.group(2)
                links.append({
                    "text": text,
                    "url": url,
                    "type": "markdown_link"
                })
            
            # Plain URL pattern
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            
            for match in re.finditer(url_pattern, content):
                url = match.group(0)
                # Avoid duplicates from markdown links
                if not any(link['url'] == url for link in links):
                    links.append({
                        "text": url,
                        "url": url,
                        "type": "plain_url"
                    })
            
            result["links"] = links
            result["link_count"] = len(links)
        
        # Extract lists
        list_items = []
        list_pattern = r'^[\s]*[-*+]\s+(.+)$'
        
        for line in content.splitlines():
            match = re.match(list_pattern, line)
            if match:
                list_items.append(match.group(1).strip())
        
        result["list_items"] = list_items
        result["list_item_count"] = len(list_items)
        
        # Extract tables
        tables = []
        lines = content.splitlines()
        in_table = False
        current_table = []
        
        for line in lines:
            if '|' in line:
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line)
            else:
                if in_table and current_table:
                    tables.append({
                        "rows": current_table,
                        "row_count": len(current_table)
                    })
                    current_table = []
                in_table = False
        
        if current_table:
            tables.append({
                "rows": current_table,
                "row_count": len(current_table)
            })
        
        result["tables"] = tables
        result["table_count"] = len(tables)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


@tool
def parse_yaml_content(
    content: str,
    validate_structure: bool = True,
    extract_keys: Optional[List[str]] = None
) -> str:
    """
    Parse YAML content and extract structured configuration.
    
    This tool analyzes YAML configuration files and extracts:
    - Complete configuration structure
    - Specific key values
    - Nested structure information
    - Data types and validation
    
    Args:
        content (str): YAML content to parse
        validate_structure (bool): Whether to validate YAML structure
        extract_keys (Optional[List[str]]): Specific keys to extract (None = all)
    
    Returns:
        str: JSON string containing parsed YAML configuration
    
    Example:
        >>> yaml_content = "name: test\\nversion: 1.0\\nconfig:\\n  key: value"
        >>> result = parse_yaml_content(yaml_content)
        >>> data = json.loads(result)
        >>> print(data['parsed_data'])
    """
    try:
        result = {
            "status": "success",
            "content_type": "yaml",
            "total_length": len(content),
            "line_count": len(content.splitlines())
        }
        
        # Parse YAML content
        try:
            parsed_data = yaml.safe_load(content)
            result["parsed_data"] = parsed_data
            result["is_valid_yaml"] = True
        except yaml.YAMLError as e:
            result["status"] = "error"
            result["is_valid_yaml"] = False
            result["parse_error"] = str(e)
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        # Validate structure
        if validate_structure and parsed_data is not None:
            structure_info = {
                "data_type": type(parsed_data).__name__,
                "is_dict": isinstance(parsed_data, dict),
                "is_list": isinstance(parsed_data, list)
            }
            
            if isinstance(parsed_data, dict):
                structure_info["key_count"] = len(parsed_data)
                structure_info["keys"] = list(parsed_data.keys())
                
                # Analyze nested structure
                nested_keys = []
                for key, value in parsed_data.items():
                    if isinstance(value, (dict, list)):
                        nested_keys.append({
                            "key": key,
                            "type": type(value).__name__,
                            "size": len(value) if isinstance(value, (dict, list)) else 0
                        })
                
                structure_info["nested_keys"] = nested_keys
                
            elif isinstance(parsed_data, list):
                structure_info["item_count"] = len(parsed_data)
                if parsed_data:
                    structure_info["item_types"] = list(set(type(item).__name__ for item in parsed_data))
            
            result["structure_info"] = structure_info
        
        # Extract specific keys
        if extract_keys and isinstance(parsed_data, dict):
            extracted = {}
            for key in extract_keys:
                # Support nested key access with dot notation
                keys = key.split('.')
                value = parsed_data
                
                try:
                    for k in keys:
                        value = value[k]
                    extracted[key] = value
                except (KeyError, TypeError):
                    extracted[key] = None
            
            result["extracted_keys"] = extracted
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


@tool
def parse_json_content(
    content: str,
    validate_structure: bool = True,
    extract_paths: Optional[List[str]] = None,
    pretty_print: bool = True
) -> str:
    """
    Parse JSON content and extract structured data.
    
    This tool analyzes JSON documents and extracts:
    - Complete JSON structure
    - Specific path values using JSONPath-like notation
    - Schema information
    - Data validation results
    
    Args:
        content (str): JSON content to parse
        validate_structure (bool): Whether to validate JSON structure
        extract_paths (Optional[List[str]]): JSONPath expressions to extract (None = all)
        pretty_print (bool): Whether to format JSON output
    
    Returns:
        str: JSON string containing parsed JSON data
    
    Example:
        >>> json_content = '{"name": "test", "data": {"value": 123}}'
        >>> result = parse_json_content(json_content, extract_paths=["data.value"])
        >>> data = json.loads(result)
        >>> print(data['parsed_data'])
    """
    try:
        result = {
            "status": "success",
            "content_type": "json",
            "total_length": len(content),
            "line_count": len(content.splitlines())
        }
        
        # Parse JSON content
        try:
            parsed_data = json.loads(content)
            result["parsed_data"] = parsed_data
            result["is_valid_json"] = True
        except json.JSONDecodeError as e:
            result["status"] = "error"
            result["is_valid_json"] = False
            result["parse_error"] = {
                "message": str(e),
                "line": e.lineno if hasattr(e, 'lineno') else None,
                "column": e.colno if hasattr(e, 'colno') else None
            }
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        # Validate structure
        if validate_structure and parsed_data is not None:
            structure_info = {
                "data_type": type(parsed_data).__name__,
                "is_object": isinstance(parsed_data, dict),
                "is_array": isinstance(parsed_data, list)
            }
            
            if isinstance(parsed_data, dict):
                structure_info["property_count"] = len(parsed_data)
                structure_info["properties"] = list(parsed_data.keys())
                
                # Analyze nested structure
                nested_properties = []
                for key, value in parsed_data.items():
                    prop_info = {
                        "key": key,
                        "type": type(value).__name__
                    }
                    
                    if isinstance(value, (dict, list)):
                        prop_info["size"] = len(value)
                        prop_info["is_nested"] = True
                    
                    nested_properties.append(prop_info)
                
                structure_info["property_details"] = nested_properties
                
            elif isinstance(parsed_data, list):
                structure_info["item_count"] = len(parsed_data)
                if parsed_data:
                    structure_info["item_types"] = list(set(type(item).__name__ for item in parsed_data))
            
            result["structure_info"] = structure_info
        
        # Extract specific paths
        if extract_paths and isinstance(parsed_data, (dict, list)):
            extracted = {}
            for path in extract_paths:
                # Support nested path access with dot notation
                keys = path.split('.')
                value = parsed_data
                
                try:
                    for k in keys:
                        if isinstance(value, dict):
                            value = value[k]
                        elif isinstance(value, list):
                            # Support array index access
                            if k.isdigit():
                                value = value[int(k)]
                            else:
                                raise KeyError(f"Invalid array access: {k}")
                        else:
                            raise TypeError(f"Cannot access key '{k}' on type {type(value).__name__}")
                    
                    extracted[path] = value
                except (KeyError, TypeError, IndexError) as e:
                    extracted[path] = None
                    result.setdefault("extraction_errors", []).append({
                        "path": path,
                        "error": str(e)
                    })
            
            result["extracted_paths"] = extracted
        
        indent = 2 if pretty_print else None
        return json.dumps(result, ensure_ascii=False, indent=indent)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


@tool
def parse_python_code(
    content: str,
    extract_functions: bool = True,
    extract_classes: bool = True,
    extract_imports: bool = True,
    extract_docstrings: bool = True,
    include_source: bool = False
) -> str:
    """
    Parse Python code and extract code structure information.
    
    This tool analyzes Python source code and extracts:
    - Function definitions with signatures and docstrings
    - Class definitions with methods
    - Import statements
    - Module-level docstrings
    - Comments and annotations
    
    Args:
        content (str): Python source code to parse
        extract_functions (bool): Whether to extract function definitions
        extract_classes (bool): Whether to extract class definitions
        extract_imports (bool): Whether to extract import statements
        extract_docstrings (bool): Whether to extract docstrings
        include_source (bool): Whether to include source code in results
    
    Returns:
        str: JSON string containing parsed Python code structure
    
    Example:
        >>> code = "def hello():\\n    '''Say hello'''\\n    print('hello')"
        >>> result = parse_python_code(code)
        >>> data = json.loads(result)
        >>> print(data['functions'])
    """
    try:
        result = {
            "status": "success",
            "content_type": "python",
            "total_length": len(content),
            "line_count": len(content.splitlines())
        }
        
        # Parse Python code using AST
        try:
            tree = ast.parse(content)
            result["is_valid_python"] = True
        except SyntaxError as e:
            result["status"] = "error"
            result["is_valid_python"] = False
            result["parse_error"] = {
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            }
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        # Extract module docstring
        if extract_docstrings:
            module_docstring = ast.get_docstring(tree)
            result["module_docstring"] = module_docstring
        
        # Extract imports
        if extract_imports:
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.append({
                            "type": "from_import",
                            "module": node.module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno
                        })
            
            result["imports"] = imports
            result["import_count"] = len(imports)
        
        # Extract functions
        if extract_functions:
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip methods (functions inside classes)
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) 
                             if hasattr(parent, 'body') and node in parent.body):
                        
                        func_info = {
                            "name": node.name,
                            "line": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                            "parameters": []
                        }
                        
                        # Extract parameters
                        for arg in node.args.args:
                            param = {"name": arg.arg}
                            if arg.annotation:
                                param["annotation"] = ast.unparse(arg.annotation)
                            func_info["parameters"].append(param)
                        
                        # Extract defaults
                        if node.args.defaults:
                            func_info["has_defaults"] = True
                            func_info["default_count"] = len(node.args.defaults)
                        
                        # Extract return annotation
                        if node.returns:
                            func_info["return_type"] = ast.unparse(node.returns)
                        
                        # Extract docstring
                        if extract_docstrings:
                            docstring = ast.get_docstring(node)
                            func_info["docstring"] = docstring
                        
                        # Extract decorators
                        if node.decorator_list:
                            func_info["decorators"] = [ast.unparse(dec) for dec in node.decorator_list]
                        
                        # Include source code if requested
                        if include_source:
                            func_info["source"] = ast.unparse(node)
                        
                        functions.append(func_info)
            
            result["functions"] = functions
            result["function_count"] = len(functions)
        
        # Extract classes
        if extract_classes:
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [ast.unparse(base) for base in node.bases],
                        "methods": []
                    }
                    
                    # Extract docstring
                    if extract_docstrings:
                        docstring = ast.get_docstring(node)
                        class_info["docstring"] = docstring
                    
                    # Extract decorators
                    if node.decorator_list:
                        class_info["decorators"] = [ast.unparse(dec) for dec in node.decorator_list]
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "line": item.lineno,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                                "parameters": []
                            }
                            
                            # Extract parameters
                            for arg in item.args.args:
                                param = {"name": arg.arg}
                                if arg.annotation:
                                    param["annotation"] = ast.unparse(arg.annotation)
                                method_info["parameters"].append(param)
                            
                            # Extract return annotation
                            if item.returns:
                                method_info["return_type"] = ast.unparse(item.returns)
                            
                            # Extract docstring
                            if extract_docstrings:
                                method_docstring = ast.get_docstring(item)
                                method_info["docstring"] = method_docstring
                            
                            # Extract decorators
                            if item.decorator_list:
                                method_info["decorators"] = [ast.unparse(dec) for dec in item.decorator_list]
                            
                            # Include source code if requested
                            if include_source:
                                method_info["source"] = ast.unparse(item)
                            
                            class_info["methods"].append(method_info)
                    
                    class_info["method_count"] = len(class_info["methods"])
                    
                    # Include source code if requested
                    if include_source:
                        class_info["source"] = ast.unparse(node)
                    
                    classes.append(class_info)
            
            result["classes"] = classes
            result["class_count"] = len(classes)
        
        # Extract global variables
        global_vars = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_info = {
                            "name": target.id,
                            "line": node.lineno
                        }
                        if include_source:
                            var_info["value"] = ast.unparse(node.value)
                        global_vars.append(var_info)
        
        result["global_variables"] = global_vars
        result["global_variable_count"] = len(global_vars)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


@tool
def parse_file_content(
    file_path: str,
    file_type: Optional[str] = None,
    parse_options: Optional[Dict[str, Any]] = None
) -> str:
    """
    Parse file content with automatic type detection.
    
    This tool automatically detects file type and applies appropriate parsing:
    - Markdown files: Extract structure, code blocks, links
    - YAML files: Parse configuration structure
    - JSON files: Parse data structure
    - Python files: Extract code structure
    
    Args:
        file_path (str): Path to the file to parse
        file_type (Optional[str]): File type override (md, yaml, json, py)
        parse_options (Optional[Dict[str, Any]]): Parser-specific options
    
    Returns:
        str: JSON string containing parsed file content
    
    Example:
        >>> result = parse_file_content("config.yaml")
        >>> data = json.loads(result)
        >>> print(data['parsed_data'])
    """
    try:
        # Read file content
        path = Path(file_path)
        
        if not path.exists():
            return json.dumps({
                "status": "error",
                "error_message": f"File not found: {file_path}",
                "error_type": "FileNotFoundError"
            }, ensure_ascii=False, indent=2)
        
        if not path.is_file():
            return json.dumps({
                "status": "error",
                "error_message": f"Path is not a file: {file_path}",
                "error_type": "NotAFileError"
            }, ensure_ascii=False, indent=2)
        
        # Detect file type
        if file_type is None:
            file_type = path.suffix.lstrip('.').lower()
        
        # Read content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Apply appropriate parser
        parse_options = parse_options or {}
        
        if file_type in ['md', 'markdown']:
            return parse_markdown_content(
                content,
                extract_structure=parse_options.get('extract_structure', True),
                extract_code_blocks=parse_options.get('extract_code_blocks', True),
                extract_links=parse_options.get('extract_links', True)
            )
        
        elif file_type in ['yaml', 'yml']:
            return parse_yaml_content(
                content,
                validate_structure=parse_options.get('validate_structure', True),
                extract_keys=parse_options.get('extract_keys')
            )
        
        elif file_type == 'json':
            return parse_json_content(
                content,
                validate_structure=parse_options.get('validate_structure', True),
                extract_paths=parse_options.get('extract_paths'),
                pretty_print=parse_options.get('pretty_print', True)
            )
        
        elif file_type == 'py':
            return parse_python_code(
                content,
                extract_functions=parse_options.get('extract_functions', True),
                extract_classes=parse_options.get('extract_classes', True),
                extract_imports=parse_options.get('extract_imports', True),
                extract_docstrings=parse_options.get('extract_docstrings', True),
                include_source=parse_options.get('include_source', False)
            )
        
        else:
            # Fallback: treat as plain text
            return json.dumps({
                "status": "success",
                "content_type": "text",
                "file_type": file_type,
                "content": content,
                "total_length": len(content),
                "line_count": len(content.splitlines())
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "file_path": file_path
        }, ensure_ascii=False, indent=2)


@tool
def extract_code_structure(
    content: str,
    language: str = "python",
    include_comments: bool = True,
    include_complexity: bool = False
) -> str:
    """
    Extract code structure from source code with language-specific analysis.
    
    This tool provides deep code analysis including:
    - Function and class extraction
    - Parameter and return type analysis
    - Docstring and comment extraction
    - Code complexity metrics (optional)
    - Dependency analysis
    
    Args:
        content (str): Source code content
        language (str): Programming language (python, javascript, java, etc.)
        include_comments (bool): Whether to extract comments
        include_complexity (bool): Whether to calculate complexity metrics
    
    Returns:
        str: JSON string containing code structure analysis
    
    Example:
        >>> code = "def calculate(x, y):\\n    return x + y"
        >>> result = extract_code_structure(code)
        >>> data = json.loads(result)
        >>> print(data['functions'])
    """
    try:
        result = {
            "status": "success",
            "content_type": "code",
            "language": language,
            "total_length": len(content),
            "line_count": len(content.splitlines())
        }
        
        if language.lower() == "python":
            # Use Python-specific parsing
            try:
                tree = ast.parse(content)
                result["is_valid_syntax"] = True
                
                # Extract all components
                structure = {
                    "functions": [],
                    "classes": [],
                    "imports": [],
                    "global_variables": []
                }
                
                # Module docstring
                module_docstring = ast.get_docstring(tree)
                if module_docstring:
                    structure["module_docstring"] = module_docstring
                
                # Walk the AST
                for node in ast.walk(tree):
                    # Functions
                    if isinstance(node, ast.FunctionDef):
                        func = {
                            "name": node.name,
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "parameters": [arg.arg for arg in node.args.args],
                            "decorators": [ast.unparse(dec) for dec in node.decorator_list]
                        }
                        
                        if ast.get_docstring(node):
                            func["docstring"] = ast.get_docstring(node)
                        
                        if node.returns:
                            func["return_type"] = ast.unparse(node.returns)
                        
                        structure["functions"].append(func)
                    
                    # Classes
                    elif isinstance(node, ast.ClassDef):
                        cls = {
                            "name": node.name,
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "bases": [ast.unparse(base) for base in node.bases],
                            "methods": [],
                            "decorators": [ast.unparse(dec) for dec in node.decorator_list]
                        }
                        
                        if ast.get_docstring(node):
                            cls["docstring"] = ast.get_docstring(node)
                        
                        # Extract methods
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                method = {
                                    "name": item.name,
                                    "line": item.lineno,
                                    "parameters": [arg.arg for arg in item.args.args]
                                }
                                
                                if ast.get_docstring(item):
                                    method["docstring"] = ast.get_docstring(item)
                                
                                cls["methods"].append(method)
                        
                        structure["classes"].append(cls)
                    
                    # Imports
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            structure["imports"].append({
                                "type": "import",
                                "module": alias.name,
                                "alias": alias.asname,
                                "line": node.lineno
                            })
                    
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            structure["imports"].append({
                                "type": "from_import",
                                "module": node.module,
                                "name": alias.name,
                                "alias": alias.asname,
                                "line": node.lineno
                            })
                
                result["structure"] = structure
                result["function_count"] = len(structure["functions"])
                result["class_count"] = len(structure["classes"])
                result["import_count"] = len(structure["imports"])
                
                # Calculate complexity if requested
                if include_complexity:
                    complexity = {
                        "total_lines": len(content.splitlines()),
                        "code_lines": len([line for line in content.splitlines() if line.strip() and not line.strip().startswith('#')]),
                        "comment_lines": len([line for line in content.splitlines() if line.strip().startswith('#')]),
                        "blank_lines": len([line for line in content.splitlines() if not line.strip()])
                    }
                    result["complexity"] = complexity
                
            except SyntaxError as e:
                result["is_valid_syntax"] = False
                result["syntax_error"] = {
                    "message": str(e),
                    "line": e.lineno,
                    "offset": e.offset
                }
        
        else:
            # Generic code parsing for other languages
            result["note"] = f"Generic parsing for {language} (detailed AST parsing only available for Python)"
            
            # Extract basic structure using regex
            functions = []
            function_patterns = {
                "javascript": r'function\s+(\w+)\s*\([^)]*\)',
                "java": r'(?:public|private|protected)?\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)',
                "cpp": r'[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*{',
                "go": r'func\s+(\w+)\s*\([^)]*\)',
                "rust": r'fn\s+(\w+)\s*\([^)]*\)'
            }
            
            pattern = function_patterns.get(language.lower())
            if pattern:
                for match in re.finditer(pattern, content):
                    functions.append({
                        "name": match.group(1),
                        "signature": match.group(0)
                    })
            
            result["functions"] = functions
            result["function_count"] = len(functions)
        
        # Extract comments if requested
        if include_comments:
            comments = []
            comment_patterns = {
                "python": r'#(.+)$',
                "javascript": r'//(.+)$',
                "java": r'//(.+)$',
                "cpp": r'//(.+)$',
                "go": r'//(.+)$',
                "rust": r'//(.+)$'
            }
            
            pattern = comment_patterns.get(language.lower())
            if pattern:
                for line_num, line in enumerate(content.splitlines(), 1):
                    match = re.search(pattern, line)
                    if match:
                        comments.append({
                            "line": line_num,
                            "comment": match.group(1).strip()
                        })
            
            result["comments"] = comments
            result["comment_count"] = len(comments)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


@tool
def chunk_large_content(
    content: str,
    chunk_size: int = 4000,
    overlap: int = 200,
    preserve_structure: bool = True
) -> str:
    """
    Split large content into manageable chunks with optional overlap.
    
    This tool intelligently splits large documents while:
    - Preserving semantic boundaries (paragraphs, sections)
    - Maintaining context with overlap
    - Keeping code blocks intact
    - Preserving Markdown structure
    
    Args:
        content (str): Content to chunk
        chunk_size (int): Maximum characters per chunk
        overlap (int): Number of characters to overlap between chunks
        preserve_structure (bool): Whether to preserve document structure
    
    Returns:
        str: JSON string containing chunked content
    
    Example:
        >>> long_text = "..." * 10000
        >>> result = chunk_large_content(long_text, chunk_size=1000)
        >>> data = json.loads(result)
        >>> print(f"Split into {data['chunk_count']} chunks")
    """
    try:
        result = {
            "status": "success",
            "original_length": len(content),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "preserve_structure": preserve_structure
        }
        
        chunks = []
        
        if preserve_structure:
            # Split by paragraphs or sections
            # Try to split at double newlines first
            sections = re.split(r'\n\n+', content)
            
            current_chunk = ""
            for section in sections:
                # If adding this section exceeds chunk size
                if len(current_chunk) + len(section) > chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        "chunk_id": len(chunks) + 1,
                        "content": current_chunk.strip(),
                        "length": len(current_chunk),
                        "start_pos": len(''.join(c['content'] for c in chunks))
                    })
                    
                    # Start new chunk with overlap
                    if overlap > 0 and len(current_chunk) > overlap:
                        current_chunk = current_chunk[-overlap:] + "\n\n" + section
                    else:
                        current_chunk = section
                else:
                    # Add section to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + section
                    else:
                        current_chunk = section
            
            # Add final chunk
            if current_chunk:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "content": current_chunk.strip(),
                    "length": len(current_chunk),
                    "start_pos": len(''.join(c['content'] for c in chunks))
                })
        
        else:
            # Simple character-based chunking
            pos = 0
            chunk_id = 1
            
            while pos < len(content):
                end_pos = min(pos + chunk_size, len(content))
                chunk_content = content[pos:end_pos]
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": chunk_content,
                    "length": len(chunk_content),
                    "start_pos": pos,
                    "end_pos": end_pos
                })
                
                pos = end_pos - overlap if overlap > 0 else end_pos
                chunk_id += 1
        
        result["chunks"] = chunks
        result["chunk_count"] = len(chunks)
        result["average_chunk_size"] = sum(c['length'] for c in chunks) / len(chunks) if chunks else 0
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


@tool
def extract_key_content(
    content: str,
    content_type: str = "auto",
    extraction_rules: Optional[Dict[str, Any]] = None
) -> str:
    """
    Extract key content from documents based on importance and relevance.
    
    This tool intelligently extracts the most important content:
    - Headings and section titles
    - Key paragraphs and summaries
    - Important code blocks
    - Configuration values
    - Metadata and attributes
    
    Args:
        content (str): Document content to analyze
        content_type (str): Content type (auto, markdown, code, config)
        extraction_rules (Optional[Dict[str, Any]]): Custom extraction rules
    
    Returns:
        str: JSON string containing extracted key content
    
    Example:
        >>> doc = "# Main\\n\\nImportant text.\\n\\n## Details\\n\\nMore info."
        >>> result = extract_key_content(doc, content_type="markdown")
        >>> data = json.loads(result)
        >>> print(data['key_sections'])
    """
    try:
        result = {
            "status": "success",
            "content_type": content_type,
            "original_length": len(content),
            "line_count": len(content.splitlines())
        }
        
        extraction_rules = extraction_rules or {}
        
        # Auto-detect content type if needed
        if content_type == "auto":
            if re.search(r'^#{1,6}\s+.+$', content, re.MULTILINE):
                content_type = "markdown"
            elif re.search(r'^def\s+\w+\s*\(|^class\s+\w+', content, re.MULTILINE):
                content_type = "python_code"
            elif content.strip().startswith('{') or content.strip().startswith('['):
                content_type = "json"
            elif re.search(r'^\w+:\s*.+$', content, re.MULTILINE):
                content_type = "yaml"
            else:
                content_type = "text"
            
            result["detected_type"] = content_type
        
        # Extract based on content type
        if content_type == "markdown":
            # Extract headings and their content
            sections = []
            current_section = None
            
            for line in content.splitlines():
                heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                
                if heading_match:
                    # Save previous section
                    if current_section:
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        "level": len(heading_match.group(1)),
                        "title": heading_match.group(2).strip(),
                        "content": []
                    }
                elif current_section:
                    current_section["content"].append(line)
            
            # Save last section
            if current_section:
                sections.append(current_section)
            
            # Calculate importance scores
            for section in sections:
                section["content_text"] = "\n".join(section["content"]).strip()
                section["content_length"] = len(section["content_text"])
                section["importance_score"] = _calculate_importance_score(
                    section["title"],
                    section["content_text"],
                    section["level"]
                )
            
            # Sort by importance
            sections.sort(key=lambda x: x["importance_score"], reverse=True)
            
            result["sections"] = sections
            result["section_count"] = len(sections)
            
            # Extract top sections
            top_n = extraction_rules.get("top_sections", 5)
            result["key_sections"] = sections[:top_n]
        
        elif content_type == "python_code":
            # Use existing Python parser
            parse_result = parse_python_code(
                content,
                extract_functions=True,
                extract_classes=True,
                extract_imports=True,
                extract_docstrings=True,
                include_source=False
            )
            
            parse_data = json.loads(parse_result)
            
            if parse_data.get("status") == "success":
                result["structure"] = parse_data.get("structure", {})
                result["functions"] = parse_data.get("functions", [])
                result["classes"] = parse_data.get("classes", [])
                result["imports"] = parse_data.get("imports", [])
                
                # Identify key functions (those with docstrings or decorators)
                key_functions = [
                    f for f in result.get("functions", [])
                    if f.get("docstring") or f.get("decorators")
                ]
                result["key_functions"] = key_functions
        
        elif content_type == "json":
            # Parse JSON and extract key-value pairs
            parse_result = parse_json_content(content, validate_structure=True)
            parse_data = json.loads(parse_result)
            
            if parse_data.get("status") == "success":
                result["parsed_data"] = parse_data.get("parsed_data")
                result["structure_info"] = parse_data.get("structure_info")
        
        elif content_type == "yaml":
            # Parse YAML and extract configuration
            parse_result = parse_yaml_content(content, validate_structure=True)
            parse_data = json.loads(parse_result)
            
            if parse_data.get("status") == "success":
                result["parsed_data"] = parse_data.get("parsed_data")
                result["structure_info"] = parse_data.get("structure_info")
        
        else:
            # Plain text extraction
            # Extract first paragraph and key sentences
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            result["paragraphs"] = paragraphs
            result["paragraph_count"] = len(paragraphs)
            
            # Extract first paragraph as key content
            if paragraphs:
                result["key_paragraph"] = paragraphs[0]
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }, ensure_ascii=False, indent=2)


def _calculate_importance_score(title: str, content: str, level: int) -> float:
    """
    Calculate importance score for a document section.
    
    Args:
        title: Section title
        content: Section content
        level: Heading level (1-6)
    
    Returns:
        Importance score (0-100)
    """
    score = 0.0
    
    # Level score (higher level = more important)
    level_score = (7 - level) * 15
    score += level_score
    
    # Content length score
    content_length = len(content)
    if content_length > 500:
        score += 20
    elif content_length > 200:
        score += 15
    elif content_length > 50:
        score += 10
    else:
        score += 5
    
    # Title keywords score
    important_keywords = [
        'overview', 'introduction', 'summary', 'conclusion',
        'important', 'key', 'critical', 'main', 'primary',
        'architecture', 'design', 'implementation', 'usage'
    ]
    
    title_lower = title.lower()
    for keyword in important_keywords:
        if keyword in title_lower:
            score += 10
            break
    
    # Content keywords score
    content_lower = content.lower()
    keyword_count = sum(1 for keyword in important_keywords if keyword in content_lower)
    score += min(keyword_count * 5, 25)
    
    return min(score, 100)
