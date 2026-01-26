"""
阶段配置模块 - 统一的阶段命名和配置单一数据源

此模块是整个系统中阶段相关配置的唯一权威来源。
所有需要阶段信息的地方都应该从这里导入，而不是自己定义。

使用方式:
    from api.v2.core.stage_config import (
        STAGES,
        get_stage_display_name,
        get_stage_number,
        normalize_stage_name,
        get_prompt_path,
        get_log_filename,
    )
"""
from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass


class BuildStage(str, Enum):
    """
    构建阶段枚举 - 标准阶段命名
    
    这是系统中所有阶段名称的唯一标准定义。
    数据库、API、前端都应该使用这些枚举值。
    """
    ORCHESTRATOR = "orchestrator"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    SYSTEM_ARCHITECTURE = "system_architecture"
    AGENT_DESIGN = "agent_design"
    PROMPT_ENGINEER = "prompt_engineer"
    TOOLS_DEVELOPER = "tools_developer"
    AGENT_CODE_DEVELOPER = "agent_code_developer"
    AGENT_DEVELOPER_MANAGER = "agent_developer_manager"
    AGENT_DEPLOYER = "agent_deployer"


@dataclass
class StageConfig:
    """阶段配置数据类"""
    # 标准名称（BuildStage 枚举值）
    name: str
    # 阶段序号（1-9）
    order: int
    # 中文显示名称
    display_name: str
    # 提示词模板路径
    prompt_path: str
    # 日志文件名（不含扩展名）
    log_filename: str
    # Agent 显示名称（英文）
    agent_display_name: str
    # 是否支持迭代（多 Agent 场景）
    supports_iteration: bool = False


# ============== 阶段配置定义 ==============
# 这是整个系统的单一数据源

STAGES: Dict[str, StageConfig] = {
    BuildStage.ORCHESTRATOR.value: StageConfig(
        name=BuildStage.ORCHESTRATOR.value,
        order=1,
        display_name="工作流编排",
        prompt_path="system_agents_prompts/agent_build_workflow/orchestrator",
        log_filename="orchestrator",
        agent_display_name="Orchestrator",
        supports_iteration=False,
    ),
    BuildStage.REQUIREMENTS_ANALYSIS.value: StageConfig(
        name=BuildStage.REQUIREMENTS_ANALYSIS.value,
        order=2,
        display_name="需求分析",
        prompt_path="system_agents_prompts/agent_build_workflow/requirements_analyzer",
        log_filename="requirements_analyzer",
        agent_display_name="Requirements Analyzer",
        supports_iteration=False,
    ),
    BuildStage.SYSTEM_ARCHITECTURE.value: StageConfig(
        name=BuildStage.SYSTEM_ARCHITECTURE.value,
        order=3,
        display_name="系统架构设计",
        prompt_path="system_agents_prompts/agent_build_workflow/system_architect",
        log_filename="system_architect",
        agent_display_name="System Architect",
        supports_iteration=False,
    ),
    BuildStage.AGENT_DESIGN.value: StageConfig(
        name=BuildStage.AGENT_DESIGN.value,
        order=4,
        display_name="Agent设计",
        prompt_path="system_agents_prompts/agent_build_workflow/agent_designer",
        log_filename="agent_designer",
        agent_display_name="Agent Designer",
        supports_iteration=True,
    ),
    BuildStage.PROMPT_ENGINEER.value: StageConfig(
        name=BuildStage.PROMPT_ENGINEER.value,
        order=5,
        display_name="提示词工程",
        prompt_path="system_agents_prompts/agent_build_workflow/prompt_engineer",
        log_filename="prompt_engineer",
        agent_display_name="Prompt Engineer",
        supports_iteration=True,
    ),
    BuildStage.TOOLS_DEVELOPER.value: StageConfig(
        name=BuildStage.TOOLS_DEVELOPER.value,
        order=6,
        display_name="工具开发",
        prompt_path="system_agents_prompts/agent_build_workflow/tool_developer",
        log_filename="tool_developer",
        agent_display_name="Tool Developer",
        supports_iteration=True,
    ),
    BuildStage.AGENT_CODE_DEVELOPER.value: StageConfig(
        name=BuildStage.AGENT_CODE_DEVELOPER.value,
        order=7,
        display_name="代码开发",
        prompt_path="system_agents_prompts/agent_build_workflow/agent_code_developer",
        log_filename="agent_code_developer",
        agent_display_name="Agent Code Developer",
        supports_iteration=True,
    ),
    BuildStage.AGENT_DEVELOPER_MANAGER.value: StageConfig(
        name=BuildStage.AGENT_DEVELOPER_MANAGER.value,
        order=8,
        display_name="开发管理",
        prompt_path="system_agents_prompts/agent_build_workflow/agent_developer_manager",
        log_filename="agent_developer_manager",
        agent_display_name="Agent Developer Manager",
        supports_iteration=False,
    ),
    BuildStage.AGENT_DEPLOYER.value: StageConfig(
        name=BuildStage.AGENT_DEPLOYER.value,
        order=9,
        display_name="Agent部署",
        prompt_path="system_agents_prompts/agent_build_workflow/agent_deployer",
        log_filename="agent_deployer",
        agent_display_name="Agent Deployer",
        supports_iteration=False,
    ),
}


# ============== 旧命名兼容映射 ==============
# 用于处理历史数据和旧代码的兼容

LEGACY_NAME_MAPPING: Dict[str, str] = {
    # 旧命名 -> 新命名（BuildStage 枚举值）
    "requirements_analyzer": BuildStage.REQUIREMENTS_ANALYSIS.value,
    "system_architect": BuildStage.SYSTEM_ARCHITECTURE.value,
    "agent_designer": BuildStage.AGENT_DESIGN.value,
    "tool_developer": BuildStage.TOOLS_DEVELOPER.value,
}


# ============== 阶段顺序列表 ==============

STAGE_SEQUENCE: List[str] = [
    BuildStage.ORCHESTRATOR.value,
    BuildStage.REQUIREMENTS_ANALYSIS.value,
    BuildStage.SYSTEM_ARCHITECTURE.value,
    BuildStage.AGENT_DESIGN.value,
    BuildStage.PROMPT_ENGINEER.value,
    BuildStage.TOOLS_DEVELOPER.value,
    BuildStage.AGENT_CODE_DEVELOPER.value,
    BuildStage.AGENT_DEVELOPER_MANAGER.value,
    BuildStage.AGENT_DEPLOYER.value,
]


# ============== 支持迭代的阶段 ==============

ITERATIVE_STAGES: List[str] = [
    stage_name for stage_name, config in STAGES.items()
    if config.supports_iteration
]


# ============== 辅助函数 ==============

def normalize_stage_name(stage_name: str) -> Optional[str]:
    """
    将各种阶段名称标准化为 BuildStage 枚举值
    
    支持:
    - 新命名（直接返回）
    - 旧命名（转换为新命名）
    - 大小写不敏感
    
    Args:
        stage_name: 阶段名称（可以是新命名、旧命名或枚举值）
    
    Returns:
        标准化的阶段名称（BuildStage.value）或 None（如果无法识别）
    
    示例:
        >>> normalize_stage_name("requirements_analyzer")
        "requirements_analysis"
        >>> normalize_stage_name("requirements_analysis")
        "requirements_analysis"
        >>> normalize_stage_name("REQUIREMENTS_ANALYSIS")
        "requirements_analysis"
    """
    if not stage_name:
        return None
    
    name_lower = stage_name.lower()
    
    # 1. 检查是否是标准名称
    if name_lower in STAGES:
        return name_lower
    
    # 2. 检查是否是旧命名
    if name_lower in LEGACY_NAME_MAPPING:
        return LEGACY_NAME_MAPPING[name_lower]
    
    # 3. 尝试作为 BuildStage 枚举
    try:
        return BuildStage(name_lower).value
    except ValueError:
        pass
    
    return None


def get_stage_display_name(stage_name: str) -> str:
    """
    获取阶段的中文显示名称
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        中文显示名称，如果无法识别则返回原始名称
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized].display_name
    return stage_name


def get_stage_number(stage_name: str) -> int:
    """
    获取阶段序号（1-9）
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        阶段序号，如果无法识别则返回 0
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized].order
    return 0


def get_prompt_path(stage_name: str) -> Optional[str]:
    """
    获取阶段的提示词模板路径
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        提示词模板路径，如果无法识别则返回 None
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized].prompt_path
    return None


def get_log_filename(stage_name: str) -> Optional[str]:
    """
    获取阶段的日志文件名（不含扩展名）
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        日志文件名，如果无法识别则返回 None
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized].log_filename
    return None


def get_agent_display_name(stage_name: str) -> str:
    """
    获取阶段对应 Agent 的英文显示名称
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        Agent 英文显示名称，如果无法识别则返回原始名称
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized].agent_display_name
    return stage_name


def is_iterative_stage(stage_name: str) -> bool:
    """
    检查阶段是否支持迭代（多 Agent 场景）
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        是否支持迭代
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized].supports_iteration
    return False


def get_stage_config(stage_name: str) -> Optional[StageConfig]:
    """
    获取阶段的完整配置
    
    Args:
        stage_name: 阶段名称（支持新旧命名）
    
    Returns:
        StageConfig 对象，如果无法识别则返回 None
    """
    normalized = normalize_stage_name(stage_name)
    if normalized and normalized in STAGES:
        return STAGES[normalized]
    return None


def get_all_stage_names() -> List[str]:
    """
    获取所有阶段名称（按顺序）
    
    Returns:
        阶段名称列表
    """
    return STAGE_SEQUENCE.copy()


def get_stage_display_name_mapping() -> Dict[str, str]:
    """
    获取阶段名称到显示名称的映射
    
    Returns:
        {stage_name: display_name} 字典
    """
    return {name: config.display_name for name, config in STAGES.items()}


def get_prompt_path_mapping() -> Dict[str, str]:
    """
    获取阶段名称到提示词路径的映射
    
    Returns:
        {stage_name: prompt_path} 字典
    """
    return {name: config.prompt_path for name, config in STAGES.items()}


def get_log_filename_mapping() -> Dict[str, str]:
    """
    获取阶段名称到日志文件名的映射
    
    Returns:
        {stage_name: log_filename} 字典
    """
    return {name: config.log_filename for name, config in STAGES.items()}
