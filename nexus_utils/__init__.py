from .prompts_manager import PromptManager
from .config_loader import ConfigLoader
from .mcp_manager import MCPManager

# 创建全局实例
prompts_manager = PromptManager()

# 导入agent_factory (可选导入，因为可能有依赖问题)
try:
    from . import agent_factory
except ImportError:
    agent_factory = None

__all__ = [
    'PromptManager',
    'ConfigLoader', 
    'MCPManager',
    'prompts_manager',
    'agent_factory'
]