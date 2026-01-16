"""
Agent Router 模块

负责 Agent 的配置管理、动态加载和智能路由。
使用 PromptManager 查找和加载 Agent 的 YAML prompt。
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List
import yaml

from nexus_utils.prompts_manager import PromptManager
from nexus_utils.agent_factory import create_agent_from_prompt_template

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Agent 路由器
    
    功能:
    - 从配置文件加载 Agent 列表
    - 使用 PromptManager 查找 Agent 的 YAML prompt
    - Agent 实例缓存管理
    - 智能路由和调用
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化路由器
        
        参数:
            config_path: 配置文件路径，默认为 extensions/slack/config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        self.config_path = Path(config_path)
        
        # 初始化 PromptManager
        self.prompt_manager = PromptManager()
        
        self.config = self._load_config()
        self.agents_config = self._load_agents_config()
        self.default_agent_name = self._get_default_agent_name()
        self._agent_cache: Dict = {}
        
        logger.info(f"AgentRouter 初始化完成，加载了 {len(self.agents_config)} 个 Agent 配置")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"配置文件加载成功: {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {"agents": [], "bot": {}}
    
    def _load_agents_config(self) -> List[Dict]:
        """加载启用的 Agent 配置列表"""
        agents = self.config.get('agents', [])
        enabled_agents = [agent for agent in agents if agent.get('enabled', True)]
        logger.info(f"加载了 {len(enabled_agents)} 个启用的 Agent")
        return enabled_agents
    
    def _get_default_agent_name(self) -> Optional[str]:
        """获取默认 Agent 名称（列表中第一个）"""
        if self.agents_config:
            default_name = self.agents_config[0]['name']
            logger.info(f"默认 Agent: {default_name}")
            return default_name
        return None
    
    def _find_prompt_path(self, agent_name: str) -> Optional[str]:
        """
        使用 PromptManager 查找 Agent 对应的 prompt 路径
        
        参数:
            agent_name: Agent 名称
            
        返回:
            prompt 路径（相对于 prompts/ 目录），如果未找到返回 None
        """
        # 使用 PromptManager 获取 agent 路径
        prompt_path = self.prompt_manager.get_agent_path(agent_name)
        
        if prompt_path:
            logger.debug(f"找到 Agent prompt: {prompt_path}")
            return prompt_path
        
        logger.warning(f"未找到 Agent '{agent_name}' 的 prompt 文件")
        return None
    
    def _get_agent(self, agent_name: str):
        """
        获取或创建 Agent 实例（带缓存）
        
        参数:
            agent_name: Agent 名称
            
        返回:
            Agent 实例，如果失败返回 None
        """
        # 检查缓存
        if agent_name in self._agent_cache:
            logger.debug(f"使用缓存的 Agent: {agent_name}")
            return self._agent_cache[agent_name]
        
        # 查找 prompt 路径
        prompt_path = self._find_prompt_path(agent_name)
        if not prompt_path:
            logger.error(f"Agent '{agent_name}' 的 prompt 不存在")
            return None
        
        # 创建 Agent
        try:
            logger.info(f"正在初始化 Agent: {agent_name}")
            agent = create_agent_from_prompt_template(prompt_path,callback_handler=None)
            self._agent_cache[agent_name] = agent
            logger.info(f"Agent '{agent_name}' 初始化成功")
            return agent
        except Exception as e:
            logger.error(f"创建 Agent '{agent_name}' 失败: {e}", exc_info=True)
            return None
    
    def get_agent_config_by_name(self, name: str) -> Optional[Dict]:
        """
        根据名称获取 Agent 配置
        
        参数:
            name: Agent 名称
            
        返回:
            Agent 配置字典，如果未找到返回 None
        """
        for agent in self.agents_config:
            if agent['name'] == name:
                return agent
        return None
    
    def call_agent(self, user_input: str, agent_name: Optional[str] = None) -> str:
        """
        调用 Agent 处理用户输入
        
        参数:
            user_input: 用户输入内容
            agent_name: 指定的 Agent 名称，如果为 None 则使用默认 Agent
            
        返回:
            Agent 的响应结果（字符串）
        """
        # 选择 Agent
        if agent_name:
            agent_config = self.get_agent_config_by_name(agent_name)
            if not agent_config:
                error_msg = f"未找到名为 '{agent_name}' 的 Agent"
                logger.warning(error_msg)
                return f"❌ {error_msg}"
            target_agent_name = agent_name
        else:
            target_agent_name = self.default_agent_name
            if not target_agent_name:
                error_msg = "没有可用的 Agent"
                logger.error(error_msg)
                return f"❌ {error_msg}"
        
        # 获取 Agent 实例
        agent = self._get_agent(target_agent_name)
        if not agent:
            error_msg = f"无法初始化 Agent '{target_agent_name}'"
            logger.error(error_msg)
            return f"❌ {error_msg}，请检查 prompt 文件是否存在"
        
        # 添加 Slack 格式化提示词到用户输入
        format_instruction = self.get_slack_format_instruction()
        if format_instruction:
            enhanced_input = user_input + format_instruction
        else:
            enhanced_input = user_input
        
        # 调用 Agent
        try:
            logger.info(f"调用 Agent '{target_agent_name}' 处理请求")
            logger.debug(f"用户输入: {user_input}")
            
            # Agent 调用返回 AgentResult
            result = agent(enhanced_input)
            
            # 提取响应内容：result.message 可能是 list 或 dict
            response = str(result)
            
            logger.info(f"Agent '{target_agent_name}' 响应完成")
            return response
            
        except Exception as e:
            error_msg = f"Agent 执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"❌ {error_msg}"
    
    def list_agents(self) -> str:
        """
        列出所有可用的 Agent
        
        返回:
            格式化的 Agent 列表字符串
        """
        if not self.agents_config:
            return "没有可用的 Agent"
        
        lines = ["📋 可用的 Agent:"]
        for i, agent in enumerate(self.agents_config, 1):
            default_mark = " (默认)" if agent['name'] == self.default_agent_name else ""
            
            # 检查 prompt 是否存在
            prompt_path = self._find_prompt_path(agent['name'])
            status = "✅" if prompt_path else "❌"
            
            lines.append(f"{i}. {status} **{agent['name']}**{default_mark}")
            lines.append(f"   {agent.get('description', '无描述')}")
        
        return "\n".join(lines)
    
    def get_disclaimer(self) -> str:
        """获取免责声明"""
        return self.config.get('bot', {}).get('disclaimer', '')
    
    def get_timeout(self) -> int:
        """获取超时时间（秒）"""
        return self.config.get('bot', {}).get('timeout', 60)
    
    def get_slack_format_instruction(self) -> str:
        """获取 Slack 格式化提示词"""
        return self.config.get('bot', {}).get('slack_format_instruction', '')
    
    def clear_cache(self):
        """清除 Agent 缓存"""
        self._agent_cache.clear()
        logger.info("Agent 缓存已清除")
