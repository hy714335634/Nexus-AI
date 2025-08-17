#!/usr/bin/env python3
"""
本地工具管理器

提供本地工具的查询、描述和管理功能，包括：
1. 返回tools/system_tools下除自身外所有工具的脚本名称及路径
2. 返回tools/system_tools下除自身外所有工具的描述信息
3. 根据给定路径返回该路径脚本中所有工具的信息
"""

import sys
import os
import ast
import inspect
import importlib.util
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import tool


class ToolAnalyzer:
    """工具分析器，用于解析Python文件中的工具信息"""
    
    def __init__(self):
        self.current_file = os.path.abspath(__file__)
    
    def extract_tools_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从Python文件中提取工具信息
        
        Args:
            file_path (str): Python文件路径
            
        Returns:
            List[Dict[str, Any]]: 工具信息列表
        """
        tools = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            # 查找被@tool装饰的函数
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 检查是否有@tool装饰器
                    has_tool_decorator = False
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Name) and decorator.id == 'tool') or \
                           (isinstance(decorator, ast.Attribute) and decorator.attr == 'tool'):
                            has_tool_decorator = True
                            break
                    
                    if has_tool_decorator:
                        tool_info = self._extract_function_info(node, content)
                        if tool_info:
                            tools.append(tool_info)
        
        except Exception as e:
            print(f"解析文件 {file_path} 时出错: {str(e)}")
        
        return tools
    
    def _extract_function_info(self, func_node: ast.FunctionDef, content: str) -> Optional[Dict[str, Any]]:
        """
        提取函数信息
        
        Args:
            func_node (ast.FunctionDef): 函数AST节点
            content (str): 文件内容
            
        Returns:
            Optional[Dict[str, Any]]: 函数信息
        """
        try:
            # 提取函数名
            func_name = func_node.name
            
            # 提取文档字符串
            docstring = ""
            if (func_node.body and 
                isinstance(func_node.body[0], ast.Expr) and 
                isinstance(func_node.body[0].value, ast.Constant) and 
                isinstance(func_node.body[0].value.value, str)):
                docstring = func_node.body[0].value.value
            
            # 解析文档字符串
            description, args_info, returns_info = self._parse_docstring(docstring)
            
            # 提取参数信息
            parameters = []
            for arg in func_node.args.args:
                param_info = {
                    "name": arg.arg,
                    "type": self._get_annotation_string(arg.annotation) if arg.annotation else "Any",
                    "description": args_info.get(arg.arg, "")
                }
                parameters.append(param_info)
            
            return {
                "name": func_name,
                "description": description,
                "parameters": parameters,
                "returns": returns_info,
                "docstring": docstring
            }
        
        except Exception as e:
            print(f"提取函数信息时出错: {str(e)}")
            return None
    
    def _parse_docstring(self, docstring: str) -> tuple:
        """
        解析文档字符串
        
        Args:
            docstring (str): 文档字符串
            
        Returns:
            tuple: (描述, 参数信息字典, 返回值信息)
        """
        if not docstring:
            return "", {}, ""
        
        lines = docstring.strip().split('\n')
        description = ""
        args_info = {}
        returns_info = ""
        
        current_section = "description"
        current_arg = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Args:"):
                current_section = "args"
                continue
            elif line.startswith("Returns:"):
                current_section = "returns"
                continue
            elif line.startswith("Raises:"):
                current_section = "raises"
                continue
            
            if current_section == "description" and line:
                if description:
                    description += " "
                description += line
            elif current_section == "args":
                if line and ":" in line:
                    # 解析参数行，格式如: param_name (type): description
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        param_part = parts[0].strip()
                        desc_part = parts[1].strip()
                        
                        # 提取参数名（去掉类型信息）
                        if "(" in param_part and ")" in param_part:
                            param_name = param_part.split("(")[0].strip()
                        else:
                            param_name = param_part
                        
                        args_info[param_name] = desc_part
                        current_arg = param_name
                elif line and current_arg:
                    # 继续上一个参数的描述
                    args_info[current_arg] += " " + line
            elif current_section == "returns" and line:
                if returns_info:
                    returns_info += " "
                returns_info += line
        
        return description, args_info, returns_info
    
    def _get_annotation_string(self, annotation) -> str:
        """
        获取类型注解的字符串表示
        
        Args:
            annotation: AST注解节点
            
        Returns:
            str: 类型字符串
        """
        try:
            if isinstance(annotation, ast.Name):
                return annotation.id
            elif isinstance(annotation, ast.Constant):
                return str(annotation.value)
            elif isinstance(annotation, ast.Attribute):
                return f"{self._get_annotation_string(annotation.value)}.{annotation.attr}"
            elif isinstance(annotation, ast.Subscript):
                value = self._get_annotation_string(annotation.value)
                slice_val = self._get_annotation_string(annotation.slice)
                return f"{value}[{slice_val}]"
            else:
                return "Any"
        except:
            return "Any"


@tool
def get_local_tools_scripts() -> str:
    """
    获取tools/system_tools目录下除自身外所有本地工具脚本的名称及路径
    
    Returns:
        str: 包含所有本地工具脚本信息的格式化字符串，符合LLM提示词规范
    """
    try:
        analyzer = ToolAnalyzer()
        system_tools_dir = os.path.join(project_root, "tools", "system_tools")
        
        if not os.path.exists(system_tools_dir):
            return "错误：tools/system_tools目录不存在"
        
        scripts = []
        current_file = os.path.abspath(__file__)
        
        # 遍历目录中的Python文件
        for file_name in os.listdir(system_tools_dir):
            if file_name.endswith('.py') and not file_name.startswith('__'):
                file_path = os.path.join(system_tools_dir, file_name)
                
                # 跳过自身
                if os.path.abspath(file_path) == current_file:
                    continue
                
                scripts.append({
                    "name": file_name,
                    "path": file_path,
                    "relative_path": f"tools/system_tools/{file_name}"
                })
        
        # 格式化输出
        if not scripts:
            return "tools/system_tools目录下没有找到其他工具脚本"
        
        result = "# 本地工具脚本列表\n\n"
        result += f"共找到 {len(scripts)} 个本地工具脚本：\n\n"
        
        for i, script in enumerate(scripts, 1):
            result += f"{i}. **{script['name']}**\n"
            result += f"   - 完整路径: `{script['path']}`\n"
            result += f"   - 相对路径: `{script['relative_path']}`\n\n"
        
        return result
        
    except Exception as e:
        return f"获取工具脚本列表时出错: {str(e)}"


@tool
def get_local_tools_descriptions() -> str:
    """
    获取tools/system_tools目录下除自身外所有本地工具的描述信息
    
    Returns:
        str: 包含所有本地工具描述信息的格式化字符串，符合LLM提示词规范
    """
    try:
        analyzer = ToolAnalyzer()
        system_tools_dir = os.path.join(project_root, "tools", "system_tools")
        
        if not os.path.exists(system_tools_dir):
            return "错误：tools/system_tools目录不存在"
        
        all_tools = []
        current_file = os.path.abspath(__file__)
        
        # 遍历目录中的Python文件
        for file_name in os.listdir(system_tools_dir):
            if file_name.endswith('.py') and not file_name.startswith('__'):
                file_path = os.path.join(system_tools_dir, file_name)
                
                # 跳过自身
                if os.path.abspath(file_path) == current_file:
                    continue
                
                # 提取文件中的工具
                tools = analyzer.extract_tools_from_file(file_path)
                
                if tools:
                    all_tools.append({
                        "file": file_name,
                        "path": f"tools/system_tools/{file_name}",
                        "tools": tools
                    })
        
        # 格式化输出
        if not all_tools:
            return "tools/system_tools目录下没有找到任何工具"
        
        result = "# 本地工具描述信息\n\n"
        
        total_tools = sum(len(file_info['tools']) for file_info in all_tools)
        result += f"共找到 {len(all_tools)} 个文件中的 {total_tools} 个本地工具：\n\n"
        
        for file_info in all_tools:
            result += f"## 📁 {file_info['file']}\n"
            result += f"**路径**: `{file_info['path']}`\n\n"
            
            for tool_info in file_info['tools']:
                result += f"### 🔧 {tool_info['name']}\n"
                result += f"**描述**: {tool_info['description']}\n\n"
                
                if tool_info['parameters']:
                    result += "**参数**:\n"
                    for param in tool_info['parameters']:
                        result += f"- `{param['name']}` ({param['type']}): {param['description']}\n"
                    result += "\n"
                
                if tool_info['returns']:
                    result += f"**返回值**: {tool_info['returns']}\n\n"
                
                result += "---\n\n"
        
        return result
        
    except Exception as e:
        return f"获取工具描述信息时出错: {str(e)}"


@tool
def get_local_tools_info_by_path(file_path: str) -> str:
    """
    根据给定的路径，返回该路径脚本中所有本地工具的信息
    
    Args:
        file_path (str): Python脚本文件路径（可以是绝对路径或相对于项目根目录的路径）
        
    Returns:
        str: 包含指定文件中所有本地工具信息的格式化字符串，符合LLM提示词规范
    """
    try:
        analyzer = ToolAnalyzer()
        
        # 处理路径
        if not os.path.isabs(file_path):
            # 相对路径，相对于项目根目录
            full_path = os.path.join(project_root, file_path)
        else:
            full_path = file_path
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            return f"错误：文件不存在 - {file_path}"
        
        # 检查是否为Python文件
        if not full_path.endswith('.py'):
            return f"错误：不是Python文件 - {file_path}"
        
        # 提取工具信息
        tools = analyzer.extract_tools_from_file(full_path)
        
        # 格式化输出
        result = f"# 本地工具信息 - {os.path.basename(file_path)}\n\n"
        result += f"**文件路径**: `{file_path}`\n"
        result += f"**完整路径**: `{full_path}`\n\n"
        
        if not tools:
            result += "该文件中没有找到任何本地工具（使用@tool装饰器的函数）\n"
            return result
        
        result += f"共找到 {len(tools)} 个本地工具：\n\n"
        
        for i, tool_info in enumerate(tools, 1):
            result += f"## {i}. 🔧 {tool_info['name']}\n\n"
            result += f"**功能描述**: {tool_info['description']}\n\n"
            
            if tool_info['parameters']:
                result += "**参数列表**:\n"
                for param in tool_info['parameters']:
                    param_desc = param['description'] if param['description'] else "无描述"
                    result += f"- `{param['name']}` ({param['type']}): {param_desc}\n"
                result += "\n"
            else:
                result += "**参数列表**: 无参数\n\n"
            
            if tool_info['returns']:
                result += f"**返回值**: {tool_info['returns']}\n\n"
            else:
                result += "**返回值**: 无返回值描述\n\n"
            
            if tool_info['docstring']:
                result += "**完整文档**:\n```\n"
                result += tool_info['docstring']
                result += "\n```\n\n"
            
            result += "---\n\n"
        
        return result
        
    except Exception as e:
        return f"获取工具信息时出错: {str(e)}"


if __name__ == "__main__":
    # 测试代码
    print("=== 测试本地工具管理器 ===")
    
    print("\n1. 获取所有本地工具脚本:")
    print(get_local_tools_scripts())
    
    print("\n2. 获取所有本地工具描述:")
    print(get_local_tools_descriptions())
    
    print("\n3. 获取指定文件的本地工具信息:")
    print(get_local_tools_info_by_path("tools/system_tools/agent_template_manager.py"))