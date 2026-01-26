"""
工作流验证器

提供提示词工具路径验证和文档格式验证功能。

Requirements:
    - 5.1: 验证所有工具路径
    - 5.3: 验证文档格式
    - 5.5: 工作流初始化时执行验证
    - 5.6: 验证失败时提供详细错误信息
"""

import logging
import importlib
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


@dataclass
class ValidationError:
    """
    验证错误
    
    属性:
        error_type: 错误类型
        path: 相关路径
        message: 错误信息
        suggestion: 修复建议
    """
    error_type: str
    path: str
    message: str
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        result = f"[{self.error_type}] {self.path}: {self.message}"
        if self.suggestion:
            result += f"\n  建议: {self.suggestion}"
        return result


@dataclass
class ValidationResult:
    """
    验证结果
    
    属性:
        valid: 是否验证通过
        errors: 错误列表
        warnings: 警告列表
        validated_paths: 已验证的路径列表
    """
    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    validated_paths: List[str] = field(default_factory=list)
    
    def add_error(self, error: ValidationError) -> None:
        """添加错误"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: ValidationError) -> None:
        """添加警告"""
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> None:
        """合并另一个验证结果"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.validated_paths.extend(other.validated_paths)
        if not other.valid:
            self.valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'valid': self.valid,
            'errors': [str(e) for e in self.errors],
            'warnings': [str(w) for w in self.warnings],
            'validated_paths': self.validated_paths,
        }


class PromptValidator:
    """
    提示词验证器
    
    验证提示词模板中的工具路径是否有效。
    
    Validates:
        - Requirement 5.1: 验证所有工具路径
        - Requirement 5.5: 工作流初始化时执行验证
        - Requirement 5.6: 验证失败时提供详细错误信息
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化验证器
        
        参数:
            project_root: 项目根目录（可选）
        """
        self.project_root = project_root or _get_project_root()
        self._tool_cache: Dict[str, bool] = {}
    
    def validate_tool_paths(
        self, 
        prompt_path: str,
        strict: bool = False,
    ) -> ValidationResult:
        """
        验证提示词模板中的工具路径
        
        参数:
            prompt_path: 提示词模板路径
            strict: 是否严格模式（严格模式下警告也视为错误）
            
        返回:
            ValidationResult: 验证结果
            
        Validates:
            - Requirement 5.1: 验证所有工具路径
            - Requirement 5.6: 验证失败时提供详细错误信息
        """
        result = ValidationResult()
        
        # 加载提示词模板
        prompt_data = self._load_prompt_template(prompt_path)
        if prompt_data is None:
            result.add_error(ValidationError(
                error_type="PROMPT_NOT_FOUND",
                path=prompt_path,
                message="提示词模板文件不存在",
                suggestion=f"检查路径是否正确: {prompt_path}",
            ))
            return result
        
        # 提取工具依赖
        tool_dependencies = self._extract_tool_dependencies(prompt_data)
        
        # 验证每个工具路径
        for tool_path in tool_dependencies:
            tool_result = self._validate_single_tool(tool_path)
            result.validated_paths.append(tool_path)
            
            if not tool_result[0]:
                error = ValidationError(
                    error_type="TOOL_NOT_FOUND",
                    path=tool_path,
                    message=tool_result[1],
                    suggestion=self._suggest_tool_fix(tool_path),
                )
                if strict:
                    result.add_error(error)
                else:
                    result.add_warning(error)
        
        return result
    
    def validate_all_workflow_prompts(self) -> ValidationResult:
        """
        验证所有工作流阶段的提示词模板
        
        返回:
            ValidationResult: 验证结果
            
        Validates: Requirement 5.5 - 工作流初始化时执行验证
        """
        from .executor import STAGE_PROMPT_MAPPING
        
        result = ValidationResult()
        
        for stage_name, prompt_path in STAGE_PROMPT_MAPPING.items():
            logger.info(f"Validating prompt for stage: {stage_name}")
            stage_result = self.validate_tool_paths(prompt_path)
            
            # 添加阶段前缀到错误信息
            for error in stage_result.errors:
                error.message = f"[{stage_name}] {error.message}"
            for warning in stage_result.warnings:
                warning.message = f"[{stage_name}] {warning.message}"
            
            result.merge(stage_result)
        
        return result
    
    def _load_prompt_template(self, prompt_path: str) -> Optional[Dict[str, Any]]:
        """
        加载提示词模板
        
        参数:
            prompt_path: 提示词路径
            
        返回:
            Dict: 提示词数据，如果不存在返回 None
        """
        # 尝试多个可能的路径
        possible_paths = [
            self.project_root / "prompts" / f"{prompt_path}.yaml",
            self.project_root / "prompts" / prompt_path / "prompt.yaml",
            self.project_root / "prompts" / f"{prompt_path}/latest.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logger.warning(f"Failed to load prompt template {path}: {e}")
        
        return None
    
    def _extract_tool_dependencies(self, prompt_data: Dict[str, Any]) -> List[str]:
        """
        从提示词数据中提取工具依赖
        
        参数:
            prompt_data: 提示词数据
            
        返回:
            List[str]: 工具路径列表
        """
        tools = []
        
        # 从 metadata.tools_dependencies 提取
        metadata = prompt_data.get('agent', {}).get('metadata', {})
        if 'tools_dependencies' in metadata:
            tools.extend(metadata['tools_dependencies'])
        
        # 从 versions[].tools 提取
        versions = prompt_data.get('agent', {}).get('versions', [])
        for version in versions:
            if 'tools' in version:
                tools.extend(version['tools'])
        
        # 去重
        return list(set(tools))
    
    def _validate_single_tool(self, tool_path: str) -> Tuple[bool, str]:
        """
        验证单个工具路径
        
        参数:
            tool_path: 工具路径
            
        返回:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 检查缓存
        if tool_path in self._tool_cache:
            return (self._tool_cache[tool_path], "")
        
        # 解析工具路径
        is_valid, message = self._check_tool_exists(tool_path)
        self._tool_cache[tool_path] = is_valid
        
        return (is_valid, message)
    
    def _check_tool_exists(self, tool_path: str) -> Tuple[bool, str]:
        """
        检查工具是否存在
        
        参数:
            tool_path: 工具路径
            
        返回:
            Tuple[bool, str]: (是否存在, 错误信息)
        """
        # 处理 strands_tools 内置工具
        if tool_path.startswith('strands_tools/'):
            tool_name = tool_path.replace('strands_tools/', '')
            try:
                from strands_agents import tools as strands_tools
                if hasattr(strands_tools, tool_name):
                    return (True, "")
                return (False, f"Strands 内置工具不存在: {tool_name}")
            except ImportError:
                return (False, "无法导入 strands_agents.tools")
        
        # 处理 system_tools
        if tool_path.startswith('system_tools/'):
            parts = tool_path.replace('system_tools/', '').split('/')
            if len(parts) >= 2:
                module_path = f"tools.system_tools.{parts[0]}.{parts[1]}"
            else:
                module_path = f"tools.system_tools.{parts[0]}"
            
            try:
                importlib.import_module(module_path)
                return (True, "")
            except ImportError as e:
                return (False, f"系统工具导入失败: {e}")
        
        # 处理 generated_tools
        if tool_path.startswith('generated_tools/'):
            parts = tool_path.replace('generated_tools/', '').split('/')
            if len(parts) >= 2:
                module_path = f"tools.generated_tools.{parts[0]}.{parts[1]}"
            else:
                module_path = f"tools.generated_tools.{parts[0]}"
            
            try:
                importlib.import_module(module_path)
                return (True, "")
            except ImportError as e:
                return (False, f"生成工具导入失败: {e}")
        
        # 处理 template_tools
        if tool_path.startswith('template_tools/'):
            parts = tool_path.replace('template_tools/', '').split('/')
            if len(parts) >= 2:
                module_path = f"tools.template_tools.{parts[0]}.{parts[1]}"
            else:
                module_path = f"tools.template_tools.{parts[0]}"
            
            try:
                importlib.import_module(module_path)
                return (True, "")
            except ImportError as e:
                return (False, f"模板工具导入失败: {e}")
        
        # 未知工具类型
        return (False, f"未知的工具路径格式: {tool_path}")
    
    def _suggest_tool_fix(self, tool_path: str) -> str:
        """
        为工具路径问题提供修复建议
        
        参数:
            tool_path: 工具路径
            
        返回:
            str: 修复建议
        """
        if tool_path.startswith('strands_tools/'):
            return "检查 strands_agents 是否正确安装，或工具名称是否正确"
        
        if tool_path.startswith('system_tools/'):
            return "检查 tools/system_tools/ 目录下是否存在对应的工具模块"
        
        if tool_path.startswith('generated_tools/'):
            return "检查 tools/generated_tools/ 目录下是否存在对应的工具模块"
        
        if tool_path.startswith('template_tools/'):
            return "检查 tools/template_tools/ 目录下是否存在对应的工具模块"
        
        return "检查工具路径格式是否正确，应以 strands_tools/、system_tools/、generated_tools/ 或 template_tools/ 开头"


class DocumentValidator:
    """
    文档验证器
    
    验证各阶段输出文档的格式是否符合标准。
    
    Validates: Requirement 5.3 - 验证文档格式
    """
    
    # 各阶段期望的文档格式 - 使用 BuildStage 枚举值
    STAGE_DOCUMENT_FORMATS = {
        "requirements_analysis": {
            "format": "markdown",
            "required_sections": ["需求概述", "功能需求", "非功能需求"],
        },
        "system_architecture": {
            "format": "json",
            "required_fields": ["architecture_type", "components"],
        },
        "agent_design": {
            "format": "markdown",
            "required_sections": ["Agent 设计", "能力定义"],
        },
        "tools_developer": {
            "format": "python",
            "required_patterns": [r"@tool", r"def\s+\w+"],
        },
        "prompt_engineer": {
            "format": "yaml",
            "required_fields": ["agent", "name", "system_prompt"],
        },
        "agent_code_developer": {
            "format": "python",
            "required_patterns": [r"from\s+nexus_utils", r"create_agent"],
        },
    }
    
    def validate_document(
        self, 
        stage_name: str, 
        content: str
    ) -> ValidationResult:
        """
        验证文档格式
        
        参数:
            stage_name: 阶段名称
            content: 文档内容
            
        返回:
            ValidationResult: 验证结果
            
        Validates: Requirement 5.3 - 验证文档格式
        """
        result = ValidationResult()
        
        if stage_name not in self.STAGE_DOCUMENT_FORMATS:
            # 未定义格式要求的阶段，跳过验证
            return result
        
        format_spec = self.STAGE_DOCUMENT_FORMATS[stage_name]
        doc_format = format_spec["format"]
        
        if doc_format == "markdown":
            self._validate_markdown(content, format_spec, result)
        elif doc_format == "json":
            self._validate_json(content, format_spec, result)
        elif doc_format == "yaml":
            self._validate_yaml(content, format_spec, result)
        elif doc_format == "python":
            self._validate_python(content, format_spec, result)
        
        return result
    
    def _validate_markdown(
        self, 
        content: str, 
        spec: Dict[str, Any], 
        result: ValidationResult
    ) -> None:
        """验证 Markdown 格式"""
        required_sections = spec.get("required_sections", [])
        
        for section in required_sections:
            # 检查是否包含必需的章节标题
            pattern = rf"#+\s*{re.escape(section)}"
            if not re.search(pattern, content, re.IGNORECASE):
                result.add_warning(ValidationError(
                    error_type="MISSING_SECTION",
                    path=section,
                    message=f"缺少必需的章节: {section}",
                    suggestion=f"添加 '## {section}' 章节",
                ))
    
    def _validate_json(
        self, 
        content: str, 
        spec: Dict[str, Any], 
        result: ValidationResult
    ) -> None:
        """验证 JSON 格式"""
        import json
        
        # 尝试提取 JSON 块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        json_content = json_match.group(1) if json_match else content
        
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(ValidationError(
                error_type="INVALID_JSON",
                path="document",
                message=f"JSON 格式无效: {e}",
                suggestion="检查 JSON 语法是否正确",
            ))
            return
        
        # 检查必需字段
        required_fields = spec.get("required_fields", [])
        for field in required_fields:
            if field not in data:
                result.add_warning(ValidationError(
                    error_type="MISSING_FIELD",
                    path=field,
                    message=f"缺少必需的字段: {field}",
                    suggestion=f"在 JSON 中添加 '{field}' 字段",
                ))
    
    def _validate_yaml(
        self, 
        content: str, 
        spec: Dict[str, Any], 
        result: ValidationResult
    ) -> None:
        """验证 YAML 格式"""
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            result.add_error(ValidationError(
                error_type="INVALID_YAML",
                path="document",
                message=f"YAML 格式无效: {e}",
                suggestion="检查 YAML 语法是否正确",
            ))
            return
        
        if data is None:
            result.add_error(ValidationError(
                error_type="EMPTY_YAML",
                path="document",
                message="YAML 内容为空",
                suggestion="添加有效的 YAML 内容",
            ))
            return
        
        # 检查必需字段（支持嵌套路径）
        required_fields = spec.get("required_fields", [])
        for field in required_fields:
            if not self._check_nested_field(data, field):
                result.add_warning(ValidationError(
                    error_type="MISSING_FIELD",
                    path=field,
                    message=f"缺少必需的字段: {field}",
                    suggestion=f"在 YAML 中添加 '{field}' 字段",
                ))
    
    def _validate_python(
        self, 
        content: str, 
        spec: Dict[str, Any], 
        result: ValidationResult
    ) -> None:
        """验证 Python 代码格式"""
        required_patterns = spec.get("required_patterns", [])
        
        for pattern in required_patterns:
            if not re.search(pattern, content):
                result.add_warning(ValidationError(
                    error_type="MISSING_PATTERN",
                    path=pattern,
                    message=f"缺少必需的代码模式: {pattern}",
                    suggestion="检查代码是否包含必需的导入或函数定义",
                ))
    
    def _check_nested_field(self, data: Dict, field_path: str) -> bool:
        """检查嵌套字段是否存在"""
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        
        return True


# 便捷函数
def validate_workflow_prompts() -> ValidationResult:
    """
    验证所有工作流提示词模板
    
    返回:
        ValidationResult: 验证结果
    """
    validator = PromptValidator()
    return validator.validate_all_workflow_prompts()


def validate_tool_path(tool_path: str) -> Tuple[bool, str]:
    """
    验证单个工具路径
    
    参数:
        tool_path: 工具路径
        
    返回:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    validator = PromptValidator()
    result = validator._validate_single_tool(tool_path)
    return result


def validate_document(stage_name: str, content: str) -> ValidationResult:
    """
    验证文档格式
    
    参数:
        stage_name: 阶段名称
        content: 文档内容
        
    返回:
        ValidationResult: 验证结果
    """
    validator = DocumentValidator()
    return validator.validate_document(stage_name, content)
