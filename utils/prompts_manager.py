from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import yaml
import glob
import os
import sys
from pathlib import Path

default_prompt_path = './prompts/system_agents_prompts/*.yaml'

@dataclass
class EnvironmentConfig:
    """环境配置类"""
    temperature: float
    max_tokens: int
    debug_mode: Optional[bool] = None

@dataclass
class ToolConfig:
    """工具配置类"""
    name: str
    enabled: bool
    description: str

@dataclass
class PerformanceMetrics:
    """性能指标类"""
    accuracy: Optional[float] = None
    response_time: Optional[float] = None
    user_satisfaction: Optional[float] = None

@dataclass
class Compatibility:
    """兼容性配置类"""
    min_strands_version: Optional[str] = None
    supported_models: List[str] = None

@dataclass
class Metadata:
    """元数据类"""
    tags: List[str]
    performance_metrics: Optional[PerformanceMetrics] = None
    dependencies: Optional[List[str]] = None
    compatibility: Optional[Compatibility] = None

@dataclass
class Example:
    """示例对话类"""
    user: str
    assistant: str

@dataclass
class PromptVersion:
    """提示词版本管理类"""
    agent_name: str
    version: str
    status: str
    created_date: str
    author: str
    description: str
    system_prompt: str
    user_prompt_template: Optional[str] = None
    context_window: Optional[int] = None
    tools: Optional[List[ToolConfig]] = None
    constraints: Optional[List[str]] = None
    examples: Optional[List[Example]] = None
    metadata: Optional[Metadata] = None

@dataclass
class PromptAgent:
    """Agent提示词管理类"""
    agent_name: str
    description: str
    category: str
    environments: Dict[str, EnvironmentConfig]
    versions: Dict[str, PromptVersion]
    
    def get_version(self, version: str = "latest") -> Optional[PromptVersion]:
        """获取指定版本的提示词，默认返回最新版本"""
        if version == "latest":
            # 优先返回名为 "latest" 的版本
            if "latest" in self.versions:
                return self.versions.get("latest")
            # 如果不存在 "latest"，则按照版本号比较
            available_versions = [v for v in self.versions.keys() if v != "latest"]
            if available_versions:
                # 使用版本号比较函数
                latest_version = max(available_versions, key=self._version_key)
                return self.versions.get(latest_version)
        return self.versions.get(version)
    
    def _version_key(self, version_str: str) -> tuple:
        """将版本字符串转换为可比较的元组"""
        try:
            # 尝试解析版本号 (如 "2.0.0" -> (2, 0, 0))
            parts = version_str.split('.')
            return tuple(int(part) for part in parts)
        except (ValueError, AttributeError):
            # 如果无法解析，返回 (0,) 作为默认值
            return (0,)
    
    def get_all_versions(self) -> Dict[str, PromptVersion]:
        """获取所有版本的提示词"""
        return self.versions.copy()
    
    def get_environment_config(self, environment: str = "production") -> Optional[EnvironmentConfig]:
        """获取指定环境的配置"""
        return self.environments.get(environment)

class PromptManager:
    """提示词管理器类"""
    _instance = None
    _initialized = False
    
    def __new__(cls, prompt_path: str = default_prompt_path):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, prompt_path: str = default_prompt_path):
        if not self._initialized:
            self.prompt_path = prompt_path
            self.agents: Dict[str, PromptAgent] = {}
            self.load_prompts()
            PromptManager._initialized = True

    def _parse_environment_config(self, env_data: Dict[str, Any]) -> EnvironmentConfig:
        """解析环境配置"""
        return EnvironmentConfig(
            temperature=env_data.get('temperature', 0.7),
            max_tokens=env_data.get('max_tokens', 2048),
            debug_mode=env_data.get('debug_mode', None)
        )

    def _parse_tool_config(self, tool_data: Dict[str, Any]) -> ToolConfig:
        """解析工具配置"""
        return ToolConfig(
            name=tool_data.get('name', ''),
            enabled=tool_data.get('enabled', True),
            description=tool_data.get('description', '')
        )

    def _parse_performance_metrics(self, metrics_data: Dict[str, Any]) -> PerformanceMetrics:
        """解析性能指标"""
        return PerformanceMetrics(
            accuracy=metrics_data.get('accuracy'),
            response_time=metrics_data.get('response_time'),
            user_satisfaction=metrics_data.get('user_satisfaction')
        )

    def _parse_compatibility(self, compat_data: Dict[str, Any]) -> Compatibility:
        """解析兼容性配置"""
        return Compatibility(
            min_strands_version=compat_data.get('min_strands_version'),
            supported_models=compat_data.get('supported_models', [])
        )

    def _parse_metadata(self, metadata_data: Dict[str, Any]) -> Metadata:
        """解析元数据"""
        performance_metrics = None
        if 'performance_metrics' in metadata_data:
            performance_metrics = self._parse_performance_metrics(metadata_data['performance_metrics'])
        
        compatibility = None
        if 'compatibility' in metadata_data:
            compatibility = self._parse_compatibility(metadata_data['compatibility'])
        
        return Metadata(
            tags=metadata_data.get('tags', []),
            performance_metrics=performance_metrics,
            dependencies=metadata_data.get('dependencies'),
            compatibility=compatibility
        )

    def _parse_examples(self, examples_data: List[Dict[str, str]]) -> List[Example]:
        """解析示例对话"""
        examples = []
        for example_data in examples_data:
            examples.append(Example(
                user=example_data.get('user', ''),
                assistant=example_data.get('assistant', '')
            ))
        return examples

    def load_prompts(self) -> None:
        """加载所有提示词文件"""
        for prompt_file in glob.glob(self.prompt_path):
            try:
                print(f"加载提示词文件: {prompt_file}")
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_data = yaml.safe_load(f)
                    
                if not prompt_data or 'agent' not in prompt_data:
                    continue

                agent_config = prompt_data['agent']
                agent_name = agent_config.get('name', 'template')
                description = agent_config.get('description', '')
                category = agent_config.get('category', 'assistant')
                
                # 解析环境配置
                environments = {}
                for env_name, env_data in agent_config.get('environments', {}).items():
                    environments[env_name] = self._parse_environment_config(env_data)
                
                # 为每个agent创建版本字典
                versions = {}
                for version_config in agent_config.get('versions', []):
                    version = version_config.get('version', 'latest')
                    
                    # 解析工具配置
                    tools = None
                    if 'tools' in version_config:
                        tools = [self._parse_tool_config(tool) for tool in version_config['tools']]
                    
                    # 解析示例
                    examples = None
                    if 'examples' in version_config:
                        examples = self._parse_examples(version_config['examples'])
                    
                    # 解析元数据
                    metadata = None
                    if 'metadata' in version_config:
                        metadata = self._parse_metadata(version_config['metadata'])
                    
                    versions[version] = PromptVersion(
                        agent_name=agent_name,
                        version=version,
                        status=version_config.get('status', 'stable'),
                        created_date=version_config.get('created_date', ''),
                        author=version_config.get('author', ''),
                        description=version_config.get('description', ''),
                        system_prompt=version_config.get('system_prompt', ''),
                        user_prompt_template=version_config.get('user_prompt_template'),
                        context_window=version_config.get('context_window'),
                        tools=tools,
                        constraints=version_config.get('constraints'),
                        examples=examples,
                        metadata=metadata
                    )
                
                # 创建或更新agent
                self.agents[agent_name] = PromptAgent(
                    agent_name=agent_name,
                    description=description,
                    category=category,
                    environments=environments,
                    versions=versions
                )
                
            except Exception as e:
                print(f"加载提示词文件 {prompt_file} 时出错: {str(e)}")

    def get_agent(self, agent_name: str) -> Optional[PromptAgent]:
        """获取指定agent的提示词管理器"""
        return self.agents.get(agent_name)
    
    def get_agent_version(self, agent_name: str, version: str = "latest") -> Optional[PromptVersion]:
        """获取指定agent的指定版本提示词"""
        agent = self.get_agent(agent_name)
        if agent:
            return agent.get_version(version)
        return None
    
    def get_all_agents(self) -> List[str]:
        """获取所有可用的agent名称"""
        return list(self.agents.keys())
    
    def get_agent_versions(self, agent_name: str) -> Dict[str, PromptVersion]:
        """获取指定agent的所有版本提示词"""
        agent = self.get_agent(agent_name)
        if agent:
            return agent.get_all_versions()
        return {}
    
    def get_latest_agent_version(self, agent_name: str) -> Optional[PromptVersion]:
        """获取指定agent的最新版本提示词"""
        return self.get_agent_version(agent_name, "latest")
    
    def get_agent_environment_config(self, agent_name: str, environment: str = "production") -> Optional[EnvironmentConfig]:
        """获取指定agent的环境配置"""
        agent = self.get_agent(agent_name)
        if agent:
            return agent.get_environment_config(environment)
        return None
    
    def get_agents_by_category(self, category: str) -> List[str]:
        """根据类别获取agent列表"""
        return [name for name, agent in self.agents.items() if agent.category == category]
    
    def get_agents_by_tag(self, tag: str) -> List[str]:
        """根据标签获取agent列表"""
        matching_agents = []
        for name, agent in self.agents.items():
            latest_version = agent.get_version("latest")
            if latest_version and latest_version.metadata and tag in latest_version.metadata.tags:
                matching_agents.append(name)
        return matching_agents

# 全局实例管理器
class PromptManagerRegistry:
    """PromptManager 注册表，用于管理多个 PromptManager 实例"""
    _instances: Dict[str, PromptManager] = {}
    
    @classmethod
    def get_instance(cls, prompt_path: str = default_prompt_path) -> PromptManager:
        """获取指定路径的 PromptManager 实例"""
        if prompt_path not in cls._instances:
            cls._instances[prompt_path] = PromptManager(prompt_path)
        return cls._instances[prompt_path]
    
    @classmethod
    def get_default_instance(cls) -> PromptManager:
        """获取默认的 PromptManager 实例"""
        return cls.get_instance(default_prompt_path)
    
    @classmethod
    def clear_instances(cls) -> None:
        """清除所有实例（主要用于测试）"""
        cls._instances.clear()
        PromptManager._instance = None
        PromptManager._initialized = False

# 便捷函数
def get_prompt_manager(prompt_path: str = default_prompt_path) -> PromptManager:
    """获取 PromptManager 实例的便捷函数"""
    return PromptManagerRegistry.get_instance(prompt_path)

def get_default_prompt_manager() -> PromptManager:
    """获取默认 PromptManager 实例的便捷函数"""
    return PromptManagerRegistry.get_default_instance()

# 使用示例
if __name__ == "__main__":
    # 创建提示词管理器实例
    manager = PromptManager()
    
    # 获取所有可用agent
    agents = manager.get_all_agents()
    print(f"可用agent列表: {agents}")
    print("=" * 100)
    
    # 获取特定agent的所有版本
    for agent_name in agents:
        agent = manager.get_agent(agent_name)
        if agent:
            print(f"[Agent Name: {agent_name}]")
            print(f"描述: {agent.description}")
            print(f"类别: {agent.category}")
            print(f"环境配置: {list(agent.environments.keys())}")
            
            versions = agent.get_all_versions()
            version_list = list(versions.keys())
            print(f"版本列表: {version_list}")
            
            # 获取最新版本
            latest_version = manager.get_latest_agent_version(agent_name)
            if latest_version:
                print(f"\n>>最新版本: {latest_version.version}")
                print(f"状态: {latest_version.status}")
                print(f"描述: {latest_version.description}")
                print(f"系统提示词: {latest_version.system_prompt[:100]}...")
                if latest_version.metadata:
                    print(f"标签: {latest_version.metadata.tags}")
                
            print("-" * 50)