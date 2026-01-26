"""
Agent 测试验证功能

在 agent_developer_manager 阶段执行 Agent 测试验证，包括：
- 提示词路径验证
- 工具依赖验证
- agent_factory 创建验证

Requirements:
    - 7.2: 提示词路径验证
    - 7.3: 工具依赖验证
    - 7.5: agent_factory 创建验证
    - 7.6: 验证结果记录
"""

import logging
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


class ValidationLevel(Enum):
    """验证级别"""
    ERROR = "error"      # 严重错误，必须修复
    WARNING = "warning"  # 警告，建议修复
    INFO = "info"        # 信息，可选修复


@dataclass
class ValidationIssue:
    """
    验证问题
    
    属性:
        level: 问题级别
        category: 问题类别
        message: 问题描述
        file_path: 相关文件路径
        suggestion: 修复建议
    """
    level: ValidationLevel
    category: str
    message: str
    file_path: Optional[str] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'level': self.level.value,
            'category': self.category,
            'message': self.message,
            'file_path': self.file_path,
            'suggestion': self.suggestion,
        }


@dataclass
class AgentValidationResult:
    """
    Agent 验证结果
    
    属性:
        agent_name: Agent 名称
        is_valid: 是否通过验证
        issues: 问题列表
        prompt_path_valid: 提示词路径是否有效
        tools_valid: 工具依赖是否有效
        factory_valid: agent_factory 创建是否成功
        test_output: 测试输出内容
    """
    agent_name: str
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    prompt_path_valid: bool = False
    tools_valid: bool = False
    factory_valid: bool = False
    test_output: str = ""
    
    @property
    def error_count(self) -> int:
        """获取错误数量"""
        return sum(1 for i in self.issues if i.level == ValidationLevel.ERROR)
    
    @property
    def warning_count(self) -> int:
        """获取警告数量"""
        return sum(1 for i in self.issues if i.level == ValidationLevel.WARNING)
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """添加问题"""
        self.issues.append(issue)
        if issue.level == ValidationLevel.ERROR:
            self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'agent_name': self.agent_name,
            'is_valid': self.is_valid,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'prompt_path_valid': self.prompt_path_valid,
            'tools_valid': self.tools_valid,
            'factory_valid': self.factory_valid,
            'issues': [i.to_dict() for i in self.issues],
            'test_output': self.test_output,
        }


class AgentValidator:
    """
    Agent 验证器
    
    负责验证生成的 Agent 是否正确配置和可用。
    
    Validates:
        - Requirement 7.2: 提示词路径验证
        - Requirement 7.3: 工具依赖验证
        - Requirement 7.5: agent_factory 创建验证
        - Requirement 7.6: 验证结果记录
    """
    
    def __init__(self, project_name: str):
        """
        初始化验证器
        
        参数:
            project_name: 项目/Agent 名称
        """
        self.project_name = project_name
        self.project_root = _get_project_root()
        self._result: Optional[AgentValidationResult] = None
    
    @property
    def result(self) -> AgentValidationResult:
        """获取验证结果"""
        if self._result is None:
            self._result = AgentValidationResult(agent_name=self.project_name)
        return self._result
    
    def validate_all(self) -> AgentValidationResult:
        """
        执行所有验证
        
        返回:
            AgentValidationResult: 验证结果
        """
        logger.info(f"Starting validation for agent: {self.project_name}")
        
        # 重置结果
        self._result = AgentValidationResult(agent_name=self.project_name)
        
        # 1. 验证提示词路径
        self.validate_prompt_path()
        
        # 2. 验证工具依赖
        self.validate_tool_dependencies()
        
        # 3. 验证 agent_factory 创建
        self.validate_agent_factory()
        
        # 更新整体验证状态
        self.result.is_valid = (
            self.result.prompt_path_valid and
            self.result.tools_valid and
            self.result.factory_valid
        )
        
        logger.info(
            f"Validation completed for {self.project_name}: "
            f"valid={self.result.is_valid}, "
            f"errors={self.result.error_count}, "
            f"warnings={self.result.warning_count}"
        )
        
        return self.result
    
    def validate_prompt_path(self) -> bool:
        """
        验证提示词路径
        
        Validates: Requirement 7.2 - 提示词路径验证
        
        返回:
            bool: 是否通过验证
        """
        logger.info(f"Validating prompt path for: {self.project_name}")
        
        # 检查可能的提示词路径
        possible_paths = [
            self.project_root / "prompts" / "generated_agents_prompts" / self.project_name,
            self.project_root / "prompts" / "generated_agents_prompts" / f"{self.project_name}.yaml",
            self.project_root / "prompts" / "generated_agents_prompts" / self.project_name / "prompt.yaml",
        ]
        
        prompt_path = None
        for path in possible_paths:
            if path.exists():
                prompt_path = path
                break
        
        if not prompt_path:
            self.result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="prompt_path",
                message=f"Prompt file not found for agent: {self.project_name}",
                suggestion="Ensure the prompt file exists in prompts/generated_agents_prompts/",
            ))
            self.result.prompt_path_valid = False
            return False
        
        # 验证提示词文件内容
        try:
            if prompt_path.is_dir():
                prompt_file = prompt_path / "prompt.yaml"
                if not prompt_file.exists():
                    # 查找目录中的 yaml 文件
                    yaml_files = list(prompt_path.glob("*.yaml"))
                    if yaml_files:
                        prompt_file = yaml_files[0]
                    else:
                        self.result.add_issue(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            category="prompt_path",
                            message=f"No YAML file found in prompt directory: {prompt_path}",
                            file_path=str(prompt_path),
                        ))
                        self.result.prompt_path_valid = False
                        return False
            else:
                prompt_file = prompt_path
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            # 验证必要字段
            if not prompt_data:
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="prompt_path",
                    message="Prompt file is empty",
                    file_path=str(prompt_file),
                ))
                self.result.prompt_path_valid = False
                return False
            
            agent_config = prompt_data.get('agent', {})
            if not agent_config:
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="prompt_path",
                    message="Missing 'agent' section in prompt file",
                    file_path=str(prompt_file),
                ))
                self.result.prompt_path_valid = False
                return False
            
            # 检查必要字段
            required_fields = ['name', 'description']
            for field in required_fields:
                if not agent_config.get(field):
                    self.result.add_issue(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="prompt_path",
                        message=f"Missing recommended field: agent.{field}",
                        file_path=str(prompt_file),
                    ))
            
            # 检查版本配置
            versions = agent_config.get('versions', [])
            if not versions:
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="prompt_path",
                    message="No versions defined in prompt file",
                    file_path=str(prompt_file),
                ))
                self.result.prompt_path_valid = False
                return False
            
            # 检查是否有 system_prompt
            has_system_prompt = False
            for version in versions:
                if version.get('system_prompt'):
                    has_system_prompt = True
                    break
            
            if not has_system_prompt:
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="prompt_path",
                    message="No system_prompt defined in any version",
                    file_path=str(prompt_file),
                ))
                self.result.prompt_path_valid = False
                return False
            
            self.result.prompt_path_valid = True
            logger.info(f"Prompt path validation passed: {prompt_file}")
            return True
            
        except yaml.YAMLError as e:
            self.result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="prompt_path",
                message=f"Invalid YAML syntax: {str(e)}",
                file_path=str(prompt_path),
            ))
            self.result.prompt_path_valid = False
            return False
        except Exception as e:
            self.result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="prompt_path",
                message=f"Error reading prompt file: {str(e)}",
                file_path=str(prompt_path),
            ))
            self.result.prompt_path_valid = False
            return False
    
    def validate_tool_dependencies(self) -> bool:
        """
        验证工具依赖
        
        Validates: Requirement 7.3 - 工具依赖验证
        
        返回:
            bool: 是否通过验证
        """
        logger.info(f"Validating tool dependencies for: {self.project_name}")
        
        # 获取提示词文件中的工具依赖
        tool_dependencies = self._get_tool_dependencies()
        
        if not tool_dependencies:
            # 没有工具依赖，视为通过
            self.result.tools_valid = True
            return True
        
        all_valid = True
        
        for tool_path in tool_dependencies:
            is_valid, error_msg = self._validate_single_tool(tool_path)
            if not is_valid:
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="tool_dependency",
                    message=f"Tool not found or invalid: {tool_path}",
                    suggestion=error_msg,
                ))
                all_valid = False
        
        self.result.tools_valid = all_valid
        return all_valid
    
    def _get_tool_dependencies(self) -> List[str]:
        """获取工具依赖列表"""
        # 查找提示词文件
        possible_paths = [
            self.project_root / "prompts" / "generated_agents_prompts" / self.project_name / "prompt.yaml",
            self.project_root / "prompts" / "generated_agents_prompts" / f"{self.project_name}.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    
                    metadata = data.get('agent', {}).get('metadata', {})
                    return metadata.get('tools_dependencies', [])
                except:
                    pass
        
        return []
    
    def _validate_single_tool(self, tool_path: str) -> Tuple[bool, str]:
        """
        验证单个工具
        
        参数:
            tool_path: 工具路径
            
        返回:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 处理 strands_tools 内置工具
        if tool_path.startswith('strands_tools/'):
            tool_name = tool_path.replace('strands_tools/', '')
            try:
                from strands_agents import tools as strands_tools
                if hasattr(strands_tools, tool_name):
                    return True, ""
                return False, f"Built-in tool not found: {tool_name}"
            except ImportError:
                return False, "strands_agents package not installed"
        
        # 处理自定义工具
        if tool_path.startswith('system_tools/') or tool_path.startswith('generated_tools/'):
            parts = tool_path.split('/')
            if len(parts) >= 2:
                tool_dir = self.project_root / "tools" / parts[0]
                tool_file = tool_dir / '/'.join(parts[1:])
                
                # 检查 .py 文件
                if not tool_file.suffix:
                    tool_file = tool_file.with_suffix('.py')
                
                if tool_file.exists():
                    return True, ""
                
                # 检查目录
                tool_dir_path = tool_dir / parts[1]
                if tool_dir_path.is_dir():
                    return True, ""
                
                return False, f"Tool file not found: {tool_file}"
        
        # 其他路径格式
        return True, ""  # 默认通过
    
    def validate_agent_factory(self) -> bool:
        """
        验证 agent_factory 创建
        
        Validates: Requirement 7.5 - agent_factory 创建验证
        
        返回:
            bool: 是否通过验证
        """
        logger.info(f"Validating agent_factory creation for: {self.project_name}")
        
        try:
            from nexus_utils.agent_factory import create_agent_from_prompt_template
            
            # 尝试创建 Agent（不实际执行）
            prompt_path = f"generated_agents_prompts/{self.project_name}"
            
            agent = create_agent_from_prompt_template(
                agent_name=prompt_path,
                env="production",
                enable_logging=False,
            )
            
            if agent is None:
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="agent_factory",
                    message="agent_factory returned None",
                    suggestion="Check prompt file format and tool dependencies",
                ))
                self.result.factory_valid = False
                return False
            
            # 验证 Agent 基本属性
            if not hasattr(agent, '__call__'):
                self.result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="agent_factory",
                    message="Created agent is not callable",
                ))
                self.result.factory_valid = False
                return False
            
            self.result.factory_valid = True
            self.result.test_output = f"Agent created successfully: {type(agent).__name__}"
            logger.info(f"Agent factory validation passed for: {self.project_name}")
            return True
            
        except ImportError as e:
            self.result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="agent_factory",
                message=f"Import error: {str(e)}",
                suggestion="Check if all required packages are installed",
            ))
            self.result.factory_valid = False
            return False
        except Exception as e:
            self.result.add_issue(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="agent_factory",
                message=f"Failed to create agent: {str(e)}",
                suggestion="Check prompt file and tool configurations",
            ))
            self.result.factory_valid = False
            return False


def validate_agent(project_name: str) -> AgentValidationResult:
    """
    验证 Agent
    
    参数:
        project_name: 项目/Agent 名称
        
    返回:
        AgentValidationResult: 验证结果
    """
    validator = AgentValidator(project_name)
    return validator.validate_all()


def validate_multiple_agents(project_names: List[str]) -> Dict[str, AgentValidationResult]:
    """
    验证多个 Agent
    
    参数:
        project_names: 项目/Agent 名称列表
        
    返回:
        Dict: Agent 名称到验证结果的映射
    """
    results = {}
    for name in project_names:
        results[name] = validate_agent(name)
    return results
