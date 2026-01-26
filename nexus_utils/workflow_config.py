"""
工作流配置加载器

从 config/workflows.yaml 加载工作流配置，提供统一的工作流定义访问接口。
所有工作流执行都应该基于此模块获取配置。
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class StageConfig:
    """
    阶段配置数据类
    
    属性:
        name: 阶段标准名称
        display_name: 中文显示名称
        agent_display_name: Agent 英文显示名称
        prompt_file: 提示词文件名（不含路径）
        log_filename: 日志文件名（不含扩展名）
        order: 阶段序号
        prerequisites: 前置阶段列表
        supports_iteration: 是否支持迭代（多 Agent 场景）
        optional: 是否可选
        description: 阶段描述
        prompt_path: 完整提示词路径（自动计算）
    """
    name: str
    display_name: str
    agent_display_name: str
    prompt_file: str
    log_filename: str
    order: int
    prerequisites: List[str] = field(default_factory=list)
    supports_iteration: bool = False
    optional: bool = False
    description: str = ""
    prompt_path: str = ""  # 完整路径，由 WorkflowConfig 计算


@dataclass
class ExecutionConfig:
    """
    执行配置数据类
    
    属性:
        max_retries: 阶段失败最大重试次数
        retry_delay_seconds: 重试间隔（秒）
        stage_timeout_seconds: 单阶段超时时间（秒）
        total_timeout_seconds: 总工作流超时时间（秒）
        checkpoint_interval_seconds: 检查点保存间隔（秒）
    """
    max_retries: int = 3
    retry_delay_seconds: int = 5
    stage_timeout_seconds: int = 3600
    total_timeout_seconds: int = 21600
    checkpoint_interval_seconds: int = 60


@dataclass
class ContextConfig:
    """
    上下文配置数据类
    
    属性:
        max_tokens: 最大上下文 token 数
        summary_threshold_tokens: 触发摘要的阈值
        include_rules: 是否包含工作流规则
        include_local_docs: 是否包含本地文档
    """
    max_tokens: int = 100000
    summary_threshold_tokens: int = 5000
    include_rules: bool = True
    include_local_docs: bool = True


@dataclass
class WorkflowConfig:
    """
    工作流配置数据类
    
    属性:
        workflow_type: 工作流类型标识
        name: 工作流名称
        display_name: 中文显示名称
        description: 工作流描述
        version: 版本号
        enabled: 是否启用
        prompt_base_path: 提示词基础路径
        stages: 阶段配置列表
        legacy_name_mapping: 旧命名兼容映射
        execution: 执行配置
        context: 上下文配置
    """
    workflow_type: str
    name: str
    display_name: str
    description: str
    version: str
    enabled: bool
    prompt_base_path: str
    stages: List[StageConfig]
    legacy_name_mapping: Dict[str, str] = field(default_factory=dict)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    
    def __post_init__(self):
        """初始化后处理：计算完整提示词路径"""
        for stage in self.stages:
            if not stage.prompt_path:
                stage.prompt_path = f"{self.prompt_base_path}/{stage.prompt_file}"
    
    def get_stage(self, stage_name: str) -> Optional[StageConfig]:
        """
        获取阶段配置
        
        参数:
            stage_name: 阶段名称（支持新旧命名）
        
        返回:
            StageConfig 对象，如果未找到则返回 None
        """
        # 标准化名称
        normalized = self.normalize_stage_name(stage_name)
        if not normalized:
            return None
        
        for stage in self.stages:
            if stage.name == normalized:
                return stage
        return None
    
    def normalize_stage_name(self, stage_name: str) -> Optional[str]:
        """
        标准化阶段名称
        
        参数:
            stage_name: 阶段名称（可以是新命名、旧命名）
        
        返回:
            标准化的阶段名称，如果无法识别则返回 None
        """
        if not stage_name:
            return None
        
        name_lower = stage_name.lower()
        
        # 检查是否是标准名称
        for stage in self.stages:
            if stage.name == name_lower:
                return name_lower
        
        # 检查是否是旧命名
        if name_lower in self.legacy_name_mapping:
            return self.legacy_name_mapping[name_lower]
        
        return None
    
    def get_stage_sequence(self) -> List[str]:
        """
        获取阶段执行顺序
        
        返回:
            按顺序排列的阶段名称列表
        """
        sorted_stages = sorted(self.stages, key=lambda s: s.order)
        return [s.name for s in sorted_stages]
    
    def get_iterative_stages(self) -> List[str]:
        """
        获取支持迭代的阶段列表
        
        返回:
            支持迭代的阶段名称列表
        """
        return [s.name for s in self.stages if s.supports_iteration]
    
    def get_optional_stages(self) -> List[str]:
        """
        获取可选阶段列表
        
        返回:
            可选阶段名称列表
        """
        return [s.name for s in self.stages if s.optional]
    
    def get_stage_display_name(self, stage_name: str) -> str:
        """
        获取阶段中文显示名称
        
        参数:
            stage_name: 阶段名称
        
        返回:
            中文显示名称，如果未找到则返回原始名称
        """
        stage = self.get_stage(stage_name)
        return stage.display_name if stage else stage_name
    
    def get_prompt_path(self, stage_name: str) -> Optional[str]:
        """
        获取阶段提示词路径
        
        参数:
            stage_name: 阶段名称
        
        返回:
            提示词路径，如果未找到则返回 None
        """
        stage = self.get_stage(stage_name)
        return stage.prompt_path if stage else None
    
    def get_stages_dict(self) -> Dict[str, StageConfig]:
        """
        获取阶段名称到配置的映射字典
        
        返回:
            {stage_name: StageConfig} 字典
        """
        return {s.name: s for s in self.stages}


# ============================================================================
# 工作流类型枚举
# ============================================================================

class WorkflowType(str, Enum):
    """工作流类型枚举"""
    AGENT_BUILD = "agent_build"
    AGENT_UPDATE = "agent_update"
    TOOL_BUILD = "tool_build"
    MAGICIAN = "magician"


# ============================================================================
# 工作流配置管理器
# ============================================================================

class WorkflowConfigManager:
    """
    工作流配置管理器
    
    单例模式，负责加载和管理所有工作流配置。
    """
    
    _instance: Optional['WorkflowConfigManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config_path: Optional[Path] = None
        self._raw_config: Dict[str, Any] = {}
        self._workflows: Dict[str, WorkflowConfig] = {}
        self._defaults: Dict[str, Any] = {}
        self._version: str = "1.0.0"
        
        # 自动加载配置
        self._load_config()
        self._initialized = True
    
    def _find_config_file(self) -> Path:
        """
        查找配置文件路径
        
        返回:
            配置文件路径
        
        异常:
            FileNotFoundError: 配置文件不存在
        """
        # 尝试多个可能的路径
        possible_paths = [
            Path("config/workflows.yaml"),
            Path(__file__).parent.parent / "config" / "workflows.yaml",
            Path.cwd() / "config" / "workflows.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        raise FileNotFoundError(
            f"Workflow config file not found. Tried: {[str(p) for p in possible_paths]}"
        )
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            self._config_path = self._find_config_file()
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f)
            
            # 解析版本
            self._version = self._raw_config.get('version', '1.0.0')
            
            # 解析默认配置
            self._defaults = self._raw_config.get('defaults', {})
            
            # 解析各工作流配置
            for workflow_type in WorkflowType:
                if workflow_type.value in self._raw_config:
                    self._workflows[workflow_type.value] = self._parse_workflow(
                        workflow_type.value,
                        self._raw_config[workflow_type.value]
                    )
            
            logger.info(f"Loaded workflow config from {self._config_path}, version: {self._version}")
            logger.info(f"Available workflows: {list(self._workflows.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to load workflow config: {e}")
            raise
    
    def _parse_workflow(self, workflow_type: str, config: Dict[str, Any]) -> WorkflowConfig:
        """
        解析单个工作流配置
        
        参数:
            workflow_type: 工作流类型
            config: 原始配置字典
        
        返回:
            WorkflowConfig 对象
        """
        # 解析阶段配置
        stages = []
        for stage_data in config.get('stages', []):
            stage = StageConfig(
                name=stage_data['name'],
                display_name=stage_data['display_name'],
                agent_display_name=stage_data['agent_display_name'],
                prompt_file=stage_data['prompt_file'],
                log_filename=stage_data['log_filename'],
                order=stage_data['order'],
                prerequisites=stage_data.get('prerequisites', []),
                supports_iteration=stage_data.get('supports_iteration', False),
                optional=stage_data.get('optional', False),
                description=stage_data.get('description', ''),
            )
            stages.append(stage)
        
        # 合并默认执行配置
        default_execution = self._defaults.get('execution', {})
        execution = ExecutionConfig(
            max_retries=default_execution.get('max_retries', 3),
            retry_delay_seconds=default_execution.get('retry_delay_seconds', 5),
            stage_timeout_seconds=default_execution.get('stage_timeout_seconds', 3600),
            total_timeout_seconds=default_execution.get('total_timeout_seconds', 21600),
            checkpoint_interval_seconds=default_execution.get('checkpoint_interval_seconds', 60),
        )
        
        # 合并默认上下文配置
        default_context = self._defaults.get('context', {})
        context = ContextConfig(
            max_tokens=default_context.get('max_tokens', 100000),
            summary_threshold_tokens=default_context.get('summary_threshold_tokens', 5000),
            include_rules=default_context.get('include_rules', True),
            include_local_docs=default_context.get('include_local_docs', True),
        )
        
        return WorkflowConfig(
            workflow_type=workflow_type,
            name=config.get('name', workflow_type),
            display_name=config.get('display_name', workflow_type),
            description=config.get('description', ''),
            version=config.get('version', 'latest'),
            enabled=config.get('enabled', True),
            prompt_base_path=config.get('prompt_base_path', ''),
            stages=stages,
            legacy_name_mapping=config.get('legacy_name_mapping', {}),
            execution=execution,
            context=context,
        )
    
    def get_workflow(self, workflow_type: str) -> Optional[WorkflowConfig]:
        """
        获取工作流配置
        
        参数:
            workflow_type: 工作流类型（如 'agent_build', 'agent_update', 'tool_build'）
        
        返回:
            WorkflowConfig 对象，如果未找到则返回 None
        """
        return self._workflows.get(workflow_type)
    
    def get_all_workflows(self) -> Dict[str, WorkflowConfig]:
        """
        获取所有工作流配置
        
        返回:
            {workflow_type: WorkflowConfig} 字典
        """
        return self._workflows.copy()
    
    def get_enabled_workflows(self) -> Dict[str, WorkflowConfig]:
        """
        获取所有启用的工作流配置
        
        返回:
            {workflow_type: WorkflowConfig} 字典
        """
        return {k: v for k, v in self._workflows.items() if v.enabled}
    
    def reload(self) -> None:
        """重新加载配置文件"""
        self._workflows.clear()
        self._load_config()
    
    @property
    def version(self) -> str:
        """配置文件版本"""
        return self._version
    
    @property
    def config_path(self) -> Optional[Path]:
        """配置文件路径"""
        return self._config_path


# ============================================================================
# 便捷函数
# ============================================================================

def get_workflow_config(workflow_type: str) -> Optional[WorkflowConfig]:
    """
    获取工作流配置（便捷函数）
    
    参数:
        workflow_type: 工作流类型
    
    返回:
        WorkflowConfig 对象
    """
    manager = WorkflowConfigManager()
    return manager.get_workflow(workflow_type)


def get_agent_build_workflow() -> WorkflowConfig:
    """
    获取 Agent 构建工作流配置
    
    返回:
        WorkflowConfig 对象
    
    异常:
        ValueError: 工作流配置不存在
    """
    config = get_workflow_config(WorkflowType.AGENT_BUILD.value)
    if not config:
        raise ValueError("Agent build workflow config not found")
    return config


def get_agent_update_workflow() -> WorkflowConfig:
    """
    获取 Agent 更新工作流配置
    
    返回:
        WorkflowConfig 对象
    
    异常:
        ValueError: 工作流配置不存在
    """
    config = get_workflow_config(WorkflowType.AGENT_UPDATE.value)
    if not config:
        raise ValueError("Agent update workflow config not found")
    return config


def get_tool_build_workflow() -> WorkflowConfig:
    """
    获取工具构建工作流配置
    
    返回:
        WorkflowConfig 对象
    
    异常:
        ValueError: 工作流配置不存在
    """
    config = get_workflow_config(WorkflowType.TOOL_BUILD.value)
    if not config:
        raise ValueError("Tool build workflow config not found")
    return config


def get_all_workflow_types() -> List[str]:
    """
    获取所有工作流类型
    
    返回:
        工作流类型列表
    """
    return [wt.value for wt in WorkflowType]
