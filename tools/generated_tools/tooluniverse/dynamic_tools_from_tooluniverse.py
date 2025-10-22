from tooluniverse import ToolUniverse
from strands import tool
import json
from typing import Dict, Any

# Global state management
_tool_universe_instance = None
_graph_tools_list = None
_initialized = False

DEFAULT_TOOLS_LIST_FILE = "tools/generated_tools/tooluniverse/embedding/toolslist_from_tooluniverse.json"

# 可配置的工具加载选项
# 设置为 None 将加载所有已安装的工具类型
# 设置为列表将只加载指定的工具类型，例如: ["opentarget", "fda_drug_label"]
# 
# 注意：ToolUniverse默认安装包含约215个工具（4个类别）
# 要加载所有600+工具，需要按照官方文档配置额外的工具文件：
# https://zitniklab.hms.harvard.edu/ToolUniverse/guide/loading_tools.html
LOAD_TOOL_TYPES = None  # None = 加载所有已安装的工具


def _ensure_initialized():
    """确保工具已初始化（单例模式）"""
    global _tool_universe_instance, _graph_tools_list, _initialized
    
    if not _initialized:
        _tool_universe_instance = ToolUniverse()
        
        # 根据配置加载工具
        if LOAD_TOOL_TYPES is None:
            # 加载所有已安装的工具类型
            print("正在加载所有已安装的工具类型...")
            available_types = list(_tool_universe_instance.tool_files.keys())
            print(f"发现 {len(available_types)} 个已安装的工具类型: {available_types}")
            _tool_universe_instance.load_tools(tool_type=available_types)
        else:
            # 加载指定的工具类型
            print(f"正在加载指定的工具类型: {LOAD_TOOL_TYPES}")
            _tool_universe_instance.load_tools(tool_type=LOAD_TOOL_TYPES)
        
        _graph_tools_list = {}
        _load_tools_from_tooluniverse()
        _initialized = True


def _load_tools_from_tooluniverse() -> Dict[str, Any]:
    """直接从ToolUniverse实例加载所有工具（内部函数）"""
    global _tool_universe_instance, _graph_tools_list
    
    # 从ToolUniverse实例获取所有已加载的工具
    # return_all_loaded_tools() 返回的是工具字典列表
    all_loaded_tools = _tool_universe_instance.return_all_loaded_tools()
    
    print(f"✓ 从ToolUniverse加载了 {len(all_loaded_tools)} 个工具")
    
    for tool_info in all_loaded_tools:
        try:
            # tool_info 已经是完整的工具信息字典
            tool_name = tool_info.get('name', '')
            
            # 跳过特殊的系统工具（如 Finish）
            if tool_name and tool_name != 'Finish':
                _graph_tools_list[tool_name] = {
                    "desc": tool_info.get('description', ''),
                    "genre": tool_info.get('type', 'Unknown'),
                    "label": tool_info.get('label', []),
                    "parameter": {}
                }
                
                # 处理参数信息
                if 'parameter' in tool_info and isinstance(tool_info['parameter'], dict):
                    param_spec = tool_info['parameter']
                    if 'properties' in param_spec:
                        properties = param_spec['properties']
                        required_params = param_spec.get('required', [])
                        
                        # 为每个参数添加required字段
                        for param_name, param_info in properties.items():
                            if isinstance(param_info, dict):
                                param_info['required'] = param_name in required_params
                        
                        _graph_tools_list[tool_name]["parameter"] = properties
                    
        except Exception as e:
            tool_name = tool_info.get('name', 'Unknown') if isinstance(tool_info, dict) else 'Unknown'
            print(f"✗ 加载工具 {tool_name} 信息失败: {e}")
            # 即使失败也保留基本信息
            if tool_name and tool_name not in _graph_tools_list:
                _graph_tools_list[tool_name] = {
                    "desc": "",
                    "genre": "Unknown",
                    "parameter": {}
                }
    
    print(f"✓ 成功加载 {len(_graph_tools_list)} 个工具到缓存")
    return _graph_tools_list


@tool(description="""
    Run dynamic tools from tooluniverse
""")
def run_dynamic_tools_from_tooluniverse(tool_name: str, tool_arguments: dict) -> Dict[str, Any]:
    """
    Run dynamic tools from tooluniverse

    Args:
        tool_name(str): The name of the tool to run
        tool_arguments(dict): The arguments of the tool to run

    Returns:
        dict: The result of the tool
    """
    _ensure_initialized()
    global _tool_universe_instance
    
    result = _tool_universe_instance.run({
        "name": tool_name,
        "arguments": tool_arguments
    })
    return result


@tool(description="""
    Get the description of a tool
""")
def get_tool_description(tool_name: str) -> str:
    """
    Get the description of a tool

    Args:
        tool_name(str): The name of the tool to get the description

    Returns:
        str: The description of the tool
    """
    _ensure_initialized()
    global _graph_tools_list
    
    return _graph_tools_list[tool_name]["desc"]


@tool(description="""
    Get the parameters of a tool
""")
def get_tool_parameters(tool_name: str) -> Dict[str, Any]:
    """
    Get the parameters of a tool

    Args:
        tool_name(str): The name of the tool to get the parameters

    Returns:
        dict: The parameters of the tool
    """
    _ensure_initialized()
    global _graph_tools_list
    
    return _graph_tools_list[tool_name]["parameter"]


def get_all_available_tools() -> Dict[str, Any]:
    """
    获取所有可用工具列表（辅助函数，用于测试）
    
    Returns:
        dict: 所有工具的字典，包含名称、描述、genre 和参数
    """
    _ensure_initialized()
    global _graph_tools_list
    
    return _graph_tools_list


def main():
    """测试主函数"""
    print("\n" + "=" * 80)
    print("ToolUniverse Dynamic Tools - 测试")
    print("=" * 80 + "\n")
    
    # 获取所有可用工具列表
    all_tools = get_all_available_tools()
    print(f"✓ 共加载 {len(all_tools)} 个可用工具\n")
    
    # 显示前10个工具
    print("前10个工具:")
    for i, tool_name in enumerate(list(all_tools.keys())[:10], 1):
        tool_info = all_tools[tool_name]
        print(f"  {i}. {tool_name}")
        print(f"     类型: {tool_info['genre']}")
        print(f"     描述: {tool_info['desc'][:80]}..." if len(tool_info['desc']) > 80 else f"     描述: {tool_info['desc']}")
    
    # 测试运行一个工具
    if all_tools:
        print(f"\n" + "-" * 80)
        test_tool_name = list(all_tools.keys())[0]
        print(f"测试运行工具: {test_tool_name}")
        
        # 获取工具参数
        params = get_tool_parameters(test_tool_name)
        print(f"工具参数: {list(params.keys())}")
        
        # 注意：实际运行需要提供正确的参数值
        print("⚠️  提示: 实际运行工具需要提供正确的参数值")

    result = run_dynamic_tools_from_tooluniverse(
        tool_name="OpenTargets_get_associated_targets_by_disease_efoId", 
        tool_arguments={"efoId": "EFO_0000537"}
    )
    print(result)
    
    print("\n" + "=" * 80)
    print("✓ 测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()