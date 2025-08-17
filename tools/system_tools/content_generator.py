#!/usr/bin/env python3
"""
内容生成工具

根据类型将内容写入到指定目录中，支持agent和prompt两种类型
"""

import sys
import os
from typing import Literal

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import tool
from utils.config_loader import get_config


@tool
def generate_content(type: Literal["agent", "prompt"], content: str, name: str) -> str:
    """
    根据类型生成内容文件
    
    Args:
        type (Literal["agent", "prompt"]): 内容类型，可以是 "agent" 或 "prompt"
        content (str): 要写入的文件内容
        name (str): 文件名（不包含扩展名）
        
    Returns:
        str: 操作结果信息
    """
    try:
        # 验证参数
        if type not in ["agent", "prompt"]:
            return "错误：type参数必须是 'agent' 或 'prompt'"
        
        if not content:
            return "错误：content参数不能为空"
        
        if not name:
            return "错误：name参数不能为空"
        
        # 验证文件名格式（避免路径遍历攻击）
        if "/" in name or "\\" in name or ".." in name:
            return "错误：文件名不能包含路径分隔符或相对路径"
        
        # 根据类型确定目标目录和文件扩展名
        if type == "agent":
            target_dir = os.path.join(project_root, "agents", "generated_agents")
            file_extension = ".py"
        else:  # type == "prompt"
            target_dir = os.path.join(project_root, "prompts", "generated_agents_prompts")
            file_extension = ".yaml"
        
        # 确保目标目录存在
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        
        # 构建完整文件路径
        filename = f"{name}{file_extension}"
        file_path = os.path.join(target_dir, filename)
        
        # 检查文件是否已存在
        if os.path.exists(file_path):
            return f"错误：文件 '{filename}' 已存在于 {target_dir} 目录中，请使用不同的名称"
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 返回成功信息
        result = {
            "status": "success",
            "message": f"成功创建{type}文件",
            "file_path": file_path,
            "file_name": filename,
            "content_length": len(content)
        }
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入文件到 {target_dir}"
    except OSError as e:
        return f"错误：文件系统操作失败: {str(e)}"
    except Exception as e:
        return f"生成内容文件时出现错误: {str(e)}"


@tool
def check_file_exists(type: Literal["agent", "prompt"], name: str) -> str:
    """
    检查指定类型和名称的文件是否已存在
    
    Args:
        type (Literal["agent", "prompt"]): 内容类型，可以是 "agent" 或 "prompt"
        name (str): 文件名（不包含扩展名）
        
    Returns:
        str: 检查结果信息
    """
    try:
        # 验证参数
        if type not in ["agent", "prompt"]:
            return "错误：type参数必须是 'agent' 或 'prompt'"
        
        if not name:
            return "错误：name参数不能为空"
        
        # 根据类型确定目标目录和文件扩展名
        if type == "agent":
            target_dir = os.path.join(project_root, "agents", "generated_agents")
            file_extension = ".py"
        else:  # type == "prompt"
            target_dir = os.path.join(project_root, "prompts", "generated_agents_prompts")
            file_extension = ".yaml"
        
        # 构建完整文件路径
        filename = f"{name}{file_extension}"
        file_path = os.path.join(target_dir, filename)
        
        # 检查文件是否存在
        exists = os.path.exists(file_path)
        
        result = {
            "exists": exists,
            "file_name": filename,
            "file_path": file_path,
            "target_directory": target_dir
        }
        
        if exists:
            # 获取文件信息
            file_stat = os.stat(file_path)
            import time
            result["file_size"] = file_stat.st_size
            result["modified_time"] = time.ctime(file_stat.st_mtime)
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"检查文件存在性时出现错误: {str(e)}"


@tool
def list_generated_files(type: Literal["agent", "prompt"]) -> str:
    """
    列出指定类型的所有已生成文件
    
    Args:
        type (Literal["agent", "prompt"]): 内容类型，可以是 "agent" 或 "prompt"
        
    Returns:
        str: 文件列表信息
    """
    try:
        # 验证参数
        if type not in ["agent", "prompt"]:
            return "错误：type参数必须是 'agent' 或 'prompt'"
        
        # 根据类型确定目标目录和文件扩展名
        if type == "agent":
            target_dir = os.path.join(project_root, "agents", "generated_agents")
            file_extension = ".py"
        else:  # type == "prompt"
            target_dir = os.path.join(project_root, "prompts", "generated_agents_prompts")
            file_extension = ".yaml"
        
        # 检查目录是否存在
        if not os.path.exists(target_dir):
            return f"目录 {target_dir} 不存在"
        
        # 获取文件列表
        files = []
        for filename in os.listdir(target_dir):
            if filename.endswith(file_extension):
                file_path = os.path.join(target_dir, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    import time
                    files.append({
                        "name": filename,
                        "name_without_extension": filename[:-len(file_extension)],
                        "size": file_stat.st_size,
                        "modified_time": time.ctime(file_stat.st_mtime),
                        "full_path": file_path
                    })
        
        # 按名称排序
        files.sort(key=lambda x: x["name"])
        
        result = {
            "type": type,
            "directory": target_dir,
            "file_count": len(files),
            "files": files
        }
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"列出生成文件时出现错误: {str(e)}"


@tool
def get_available_name_suggestions(type: Literal["agent", "prompt"], base_name: str) -> str:
    """
    为冲突的文件名提供可用的名称建议
    
    Args:
        type (Literal["agent", "prompt"]): 内容类型，可以是 "agent" 或 "prompt"
        base_name (str): 基础文件名
        
    Returns:
        str: 可用名称建议列表
    """
    try:
        # 验证参数
        if type not in ["agent", "prompt"]:
            return "错误：type参数必须是 'agent' 或 'prompt'"
        
        if not base_name:
            return "错误：base_name参数不能为空"
        
        # 根据类型确定目标目录和文件扩展名
        if type == "agent":
            target_dir = os.path.join(project_root, "agents", "generated_agents")
            file_extension = ".py"
        else:  # type == "prompt"
            target_dir = os.path.join(project_root, "prompts", "generated_agents_prompts")
            file_extension = ".yaml"
        
        suggestions = []
        
        # 生成数字后缀建议
        for i in range(1, 11):  # 生成1-10的后缀
            suggested_name = f"{base_name}_{i}"
            file_path = os.path.join(target_dir, f"{suggested_name}{file_extension}")
            if not os.path.exists(file_path):
                suggestions.append(suggested_name)
        
        # 生成时间戳后缀建议
        import time
        timestamp = int(time.time())
        timestamp_name = f"{base_name}_{timestamp}"
        timestamp_file_path = os.path.join(target_dir, f"{timestamp_name}{file_extension}")
        if not os.path.exists(timestamp_file_path):
            suggestions.append(timestamp_name)
        
        # 生成版本后缀建议
        for version in ["v1", "v2", "v3"]:
            version_name = f"{base_name}_{version}"
            version_file_path = os.path.join(target_dir, f"{version_name}{file_extension}")
            if not os.path.exists(version_file_path):
                suggestions.append(version_name)
        
        result = {
            "base_name": base_name,
            "type": type,
            "suggestions": suggestions[:5],  # 限制返回前5个建议
            "total_suggestions": len(suggestions)
        }
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"生成名称建议时出现错误: {str(e)}"


# 主函数，用于直接调用测试
def main():
    """主函数，用于测试内容生成工具"""
    print("=== 内容生成工具测试 ===")
    
    # 测试检查文件存在性
    print("\n1. 检查文件存在性:")
    print(check_file_exists("agent", "test_agent"))
    
    # 测试列出文件
    print("\n2. 列出已生成的agent文件:")
    print(list_generated_files("agent"))
    
    print("\n3. 列出已生成的prompt文件:")
    print(list_generated_files("prompt"))
    
    # 测试名称建议
    print("\n4. 获取名称建议:")
    print(get_available_name_suggestions("agent", "test"))
    
    # 测试生成内容（使用测试内容）
    test_agent_content = '''#!/usr/bin/env python3
"""
测试Agent
"""

def main():
    print("这是一个测试Agent")

if __name__ == "__main__":
    main()
'''
    
    test_prompt_content = '''agent:
  name: "test_prompt"
  description: "测试提示词"
  category: "test"
'''
    
    print("\n5. 测试生成agent文件:")
    result = generate_content("agent", test_agent_content, "test_agent_demo")
    print(result)
    
    print("\n6. 测试生成prompt文件:")
    result = generate_content("prompt", test_prompt_content, "test_prompt_demo")
    print(result)


if __name__ == "__main__":
    main()