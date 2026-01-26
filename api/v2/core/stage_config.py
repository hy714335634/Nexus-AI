"""
阶段配置模块 - 统一的阶段命名和配置单一数据源

此模块是整个系统中阶段相关配置的唯一权威来源。
所有需要阶段信息的地方都应该从这里导入，而不是自己定义。

配置来源: config/workflows.yaml
默认工作流: agent_build

使用方式:
    from api.v2.core.stage_config import (
        STAGES,
        get_stage_display_name,
        get_stage_number,
        normalize_stage_name,
        get_prompt_path,
        get_log_filename,
        get_workflow_config,
    )
"""
from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

# 导入工作流配置管理器
from nexus_utils.workflow_config import (
    WorkflowConfigManager,
    WorkflowConfig,
    StageConfig as WorkflowStageConfig,
    WorkflowType,
    get_agent_build_workflow,
    get_workflow_config as _get_workflow_config,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 工作流配置获取
# ============================================================================

def get_workflow_config(workflow_type: str = "agent_build") -> WorkflowConfig:
    """
    获取工作流配置
    
    参数:
        workflow_type: 工作流类型，默认为 'agent_build'
    
    返回:
        WorkflowConfig 对象
    
    异常:
        ValueError: 工作流配置不存在
    """
    config = _get_workflow_config(workflow_type)
    if not config:
        raise ValueError(f"Workflow config not found: {workflow_type}")
    return config


# ============================================================================
# 默认使用 Agent Build 工作流（向后兼容）
# ============================================================================

def _get_default_workflow() -> WorkflowConfig:
    """获取默认工作流配置（Agent Build）"""
    return get_agent_build_workflow()


# ============================================================================
# BuildStage 枚举 - 动态生成
# ============================================================================

def _create_build_stage_enum():
    """
    从配置文件动态创建 BuildStage 枚举
    
    返回:
        BuildStage 枚举类
    """
    workflow = _get_default_workflow()
    members = {}
    for stage in workflow.stages:
        # 枚举成员名称为大写
        enum_name = stage.name.upper()
        members[enum_name] = stage.name
    
    return Enum('BuildStage', members, type=str)


# 创建枚举（延迟初始化）
BuildStage = _create_build_stage_enum()


# ============================================================================
# StageConfig 数据类（向后兼容）
# ============================================================================

@dataclass
class StageConfig:
    """
    阶段配置数据类（向后兼容）
    
    此类保持与旧代码的兼容性，内部使用 WorkflowStageConfig
    """
    name: str
    order: int
    display_name: str
    prompt_path: str
    log_filename: str
    agent_display_name: str
    supports_iteration: bool = False
    
    @classmethod
    def from_workflow_stage(cls, stage: WorkflowStageConfig) -> 'StageConfig':
        """从 WorkflowStageConfig 创建"""
        return cls(
            name=stage.name,
            order=stage.order,
            display_name=stage.display_name,
            prompt_path=stage.prompt_path,
            log_filename=stage.log_filename,
            agent_display_name=stage.agent_display_name,
            supports_iteration=stage.supports_iteration,
        )


# ============================================================================
# STAGES 字典 - 从配置文件加载
# ============================================================================

def _load_stages() -> Dict[str, StageConfig]:
    """从配置文件加载阶段配置"""
    workflow = _get_default_workflow()
    stages = {}
    for stage in workflow.stages:
        stages[stage.name] = StageConfig.from_workflow_stage(stage)
    return stages


STAGES: Dict[str, StageConfig] = _load_stages()


# ============================================================================
# 旧命名兼容映射 - 从配置文件加载
# ============================================================================

def _load_legacy_mapping() -> Dict[str, str]:
    """从配置文件加载旧命名映射"""
    workflow = _get_default_workflow()
    return workflow.legacy_name_mapping.copy()


LEGACY_NAME_MAPPING: Dict[str, str] = _load_legacy_mapping()


# ============================================================================
# 阶段顺序列表 - 从配置文件加载
# ============================================================================

def _load_stage_sequence() -> List[str]:
    """从配置文件加载阶段顺序"""
    workflow = _get_default_workflow()
    return workflow.get_stage_sequence()


STAGE_SEQUENCE: List[str] = _load_stage_sequence()


# ============================================================================
# 支持迭代的阶段 - 从配置文件加载
# ============================================================================

def _load_iterative_stages() -> List[str]:
    """从配置文件加载支持迭代的阶段"""
    workflow = _get_default_workflow()
    return workflow.get_iterative_stages()


ITERATIVE_STAGES: List[str] = _load_iterative_stages()


# ============================================================================
# 辅助函数
# ============================================================================

def normalize_stage_name(stage_name: str, workflow_type: str = "agent_build") -> Optional[str]:
    """
    将各种阶段名称标准化为标准枚举值
    
    支持:
    - 新命名（直接返回）
    - 旧命名（转换为新命名）
    - 大小写不敏感
    
    参数:
        stage_name: 阶段名称（可以是新命名、旧命名或枚举值）
        workflow_type: 工作流类型，默认为 'agent_build'
    
    返回:
        标准化的阶段名称或 None（如果无法识别）
    
    示例:
        >>> normalize_stage_name("requirements_analyzer")
        "requirements_analysis"
        >>> normalize_stage_name("requirements_analysis")
        "requirements_analysis"
    """
    if not stage_name:
        return None
    
    workflow = get_workflow_config(workflow_type)
    return workflow.normalize_stage_name(stage_name)


def get_stage_display_name(stage_name: str, workflow_type: str = "agent_build") -> str:
    """
    获取阶段的中文显示名称
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        中文显示名称，如果无法识别则返回原始名称
    """
    workflow = get_workflow_config(workflow_type)
    return workflow.get_stage_display_name(stage_name)


def get_stage_number(stage_name: str, workflow_type: str = "agent_build") -> int:
    """
    获取阶段序号
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        阶段序号，如果无法识别则返回 0
    """
    workflow = get_workflow_config(workflow_type)
    stage = workflow.get_stage(stage_name)
    return stage.order if stage else 0


def get_prompt_path(stage_name: str, workflow_type: str = "agent_build") -> Optional[str]:
    """
    获取阶段的提示词模板路径
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        提示词模板路径，如果无法识别则返回 None
    """
    workflow = get_workflow_config(workflow_type)
    return workflow.get_prompt_path(stage_name)


def get_log_filename(stage_name: str, workflow_type: str = "agent_build") -> Optional[str]:
    """
    获取阶段的日志文件名（不含扩展名）
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        日志文件名，如果无法识别则返回 None
    """
    workflow = get_workflow_config(workflow_type)
    stage = workflow.get_stage(stage_name)
    return stage.log_filename if stage else None


def get_agent_display_name(stage_name: str, workflow_type: str = "agent_build") -> str:
    """
    获取阶段对应 Agent 的英文显示名称
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        Agent 英文显示名称，如果无法识别则返回原始名称
    """
    workflow = get_workflow_config(workflow_type)
    stage = workflow.get_stage(stage_name)
    return stage.agent_display_name if stage else stage_name


def is_iterative_stage(stage_name: str, workflow_type: str = "agent_build") -> bool:
    """
    检查阶段是否支持迭代（多 Agent 场景）
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        是否支持迭代
    """
    workflow = get_workflow_config(workflow_type)
    stage = workflow.get_stage(stage_name)
    return stage.supports_iteration if stage else False


def get_stage_config(stage_name: str, workflow_type: str = "agent_build") -> Optional[StageConfig]:
    """
    获取阶段的完整配置
    
    参数:
        stage_name: 阶段名称（支持新旧命名）
        workflow_type: 工作流类型
    
    返回:
        StageConfig 对象，如果无法识别则返回 None
    """
    workflow = get_workflow_config(workflow_type)
    stage = workflow.get_stage(stage_name)
    return StageConfig.from_workflow_stage(stage) if stage else None


def get_all_stage_names(workflow_type: str = "agent_build") -> List[str]:
    """
    获取所有阶段名称（按顺序）
    
    参数:
        workflow_type: 工作流类型
    
    返回:
        阶段名称列表
    """
    workflow = get_workflow_config(workflow_type)
    return workflow.get_stage_sequence()


def get_stage_display_name_mapping(workflow_type: str = "agent_build") -> Dict[str, str]:
    """
    获取阶段名称到显示名称的映射
    
    参数:
        workflow_type: 工作流类型
    
    返回:
        {stage_name: display_name} 字典
    """
    workflow = get_workflow_config(workflow_type)
    return {s.name: s.display_name for s in workflow.stages}


def get_prompt_path_mapping(workflow_type: str = "agent_build") -> Dict[str, str]:
    """
    获取阶段名称到提示词路径的映射
    
    参数:
        workflow_type: 工作流类型
    
    返回:
        {stage_name: prompt_path} 字典
    """
    workflow = get_workflow_config(workflow_type)
    return {s.name: s.prompt_path for s in workflow.stages}


def get_log_filename_mapping(workflow_type: str = "agent_build") -> Dict[str, str]:
    """
    获取阶段名称到日志文件名的映射
    
    参数:
        workflow_type: 工作流类型
    
    返回:
        {stage_name: log_filename} 字典
    """
    workflow = get_workflow_config(workflow_type)
    return {s.name: s.log_filename for s in workflow.stages}


# ============================================================================
# 工作流相关函数
# ============================================================================

def get_available_workflows() -> List[str]:
    """
    获取所有可用的工作流类型
    
    返回:
        工作流类型列表
    """
    manager = WorkflowConfigManager()
    return list(manager.get_enabled_workflows().keys())


def get_workflow_stages(workflow_type: str) -> List[str]:
    """
    获取指定工作流的所有阶段
    
    参数:
        workflow_type: 工作流类型
    
    返回:
        阶段名称列表
    """
    workflow = get_workflow_config(workflow_type)
    return workflow.get_stage_sequence()


def reload_workflow_config() -> None:
    """
    重新加载工作流配置
    
    用于配置文件更新后刷新内存中的配置
    """
    global STAGES, LEGACY_NAME_MAPPING, STAGE_SEQUENCE, ITERATIVE_STAGES, BuildStage
    
    manager = WorkflowConfigManager()
    manager.reload()
    
    # 重新加载各项配置
    STAGES = _load_stages()
    LEGACY_NAME_MAPPING = _load_legacy_mapping()
    STAGE_SEQUENCE = _load_stage_sequence()
    ITERATIVE_STAGES = _load_iterative_stages()
    BuildStage = _create_build_stage_enum()
    
    logger.info("Workflow config reloaded")
