from .prompts_manager import PromptManager
from .config_loader import ConfigLoader
from .mcp_manager import MCPManager

# 创建全局实例
prompts_manager = PromptManager()

__all__ = [
    'PromptManager',
    'ConfigLoader', 
    'MCPManager',
    'prompts_manager'
]