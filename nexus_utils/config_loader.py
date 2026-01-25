#!/usr/bin/env python3
"""
配置加载工具

提供加载和访问配置的功能
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

# 配置默认路径
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 "config", "default_config.yaml")

class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path (str, optional): 配置文件路径，如果不提供则使用默认路径
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self._configure_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        try:
            if not os.path.exists(self.config_path):
                print(f"⚠️ 配置文件不存在: {self.config_path}")
                return {"default-config": {}}
            
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                return config if config else {"default-config": {}}
                
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {"default-config": {}}
    
    def _configure_logging(self):
        """配置日志"""
        log_config = self.get("logging", {})
        log_level = log_config.get("level", "INFO")
        log_format = log_config.get("format", '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = log_config.get("file_path")
        
        # 尝试创建日志目录并配置文件日志
        # 如果失败（如容器环境权限问题），回退到控制台日志
        if log_file:
            try:
                log_dir = os.path.dirname(os.path.abspath(log_file))
                os.makedirs(log_dir, exist_ok=True)
                # 测试是否有写入权限
                test_file = os.path.join(log_dir, '.write_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except (PermissionError, OSError):
                # 容器环境或无权限时，禁用文件日志
                log_file = None
        
        # 配置日志
        try:
            logging.basicConfig(
                level=getattr(logging, log_level),
                format=log_format,
                filename=log_file
            )
        except (PermissionError, OSError):
            # 最终回退：仅控制台日志
            logging.basicConfig(
                level=getattr(logging, log_level),
                format=log_format
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key (str): 配置键
            default (Any, optional): 默认值
            
        Returns:
            Any: 配置值
        """
        config = self.config.get("default-config", {})
        return config.get(key, default)
    
    def get_section(self, section_name: str, default: Any = None) -> Any:
        """
        获取配置部分
        
        Args:
            section_name (str): 配置部分名称
            default (Any, optional): 默认值
            
        Returns:
            Any: 配置部分的值
        """
        config = self.config.get("default-config", {})
        return config.get(section_name, default)
    
    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """
        获取嵌套配置项
        
        Args:
            *keys: 配置键路径
            default (Any, optional): 默认值
            
        Returns:
            Any: 配置值
            
        Example:
            >>> config.get_nested("multimodal_parser", "aws", "s3_bucket")
            "awesome-nexus-ai-file-storage"
        """
        config = self.config.get("default-config", {})
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_with_env_override(self, env_var_name: str, *config_keys: str, default: Any = None) -> Any:
        """
        获取配置项，支持环境变量优先覆盖
        
        优先级：环境变量 > 配置文件 > 默认值
        
        Args:
            env_var_name (str): 环境变量名称
            *config_keys: 配置键路径（用于从配置文件读取）
            default (Any, optional): 默认值
            
        Returns:
            Any: 配置值（优先使用环境变量，否则使用配置文件或默认值）
            
        Example:
            >>> # 优先使用环境变量 OTEL_EXPORTER_OTLP_ENDPOINT
            >>> # 如果不存在，则从配置文件 nexus_ai.OTEL_EXPORTER_OTLP_ENDPOINT 读取
            >>> # 如果都不存在，使用默认值 "http://localhost:4318"
            >>> config.get_with_env_override(
            ...     "OTEL_EXPORTER_OTLP_ENDPOINT",
            ...     "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
            ...     default="http://localhost:4318"
            ... )
        """
        # 优先检查环境变量
        env_value = os.environ.get(env_var_name)
        if env_value:
            return env_value
        
        # 如果环境变量不存在，从配置文件读取
        if config_keys:
            config_value = self.get_nested(*config_keys, default=None)
            if config_value is not None:
                return config_value
        
        # 最后使用默认值
        return default
    
    def get_aws_config(self) -> Dict[str, Any]:
        """
        获取AWS配置
        
        Returns:
            Dict: AWS配置字典
        """
        return self.get("aws", {})
    
    def get_bedrock_config(self) -> Dict[str, Any]:
        """
        获取Bedrock配置
        
        Returns:
            Dict: Bedrock配置字典
        """
        return self.get("bedrock", {})
    
    def get_strands_config(self) -> Dict[str, Any]:
        """
        获取Strands配置
        
        Returns:
            Dict: Strands配置字典
        """
        return self.get("strands", {})
    
    def get_agentcore_config(self) -> Dict[str, Any]:
        """
        获取AgentCore配置
        
        Returns:
            Dict: AgentCore配置字典
        """
        return self.get("agentcore", {})
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """
        获取MCP配置
        
        Returns:
            Dict: MCP配置字典
        """
        return self.get("mcp", {})
    
    def get_multimodal_parser_config(self) -> Dict[str, Any]:
        """
        获取多模态解析器配置
        
        Returns:
            Dict: 多模态解析器配置字典
        """
        return self.get("multimodal_parser", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        获取日志配置
        
        Returns:
            Dict: 日志配置字典
        """
        return self.get("logging", {})
    
    def get_workflow_version_config(self) -> Dict[str, Any]:
        """
        获取工作流默认版本配置
        
        Returns:
            Dict: 工作流版本配置字典，包含 agent_build, agent_update, tool_build
        """
        return self.get_nested("nexus_ai", "workflow_default_version", default={})
    
    def get_workflow_config(self) -> Dict[str, Any]:
        """
        获取工作流引擎配置
        
        支持环境变量覆盖：
        - NEXUS_WORKFLOW_MAX_RETRIES: 最大重试次数
        - NEXUS_WORKFLOW_STAGE_TIMEOUT: 阶段超时时间（秒）
        - NEXUS_WORKFLOW_MAX_CONTEXT_TOKENS: 最大上下文 token 数
        
        Returns:
            Dict: 工作流配置字典
            
        Validates: Requirement 8.6 - 环境变量覆盖
        """
        workflow_config = self.get("workflow", {})
        
        # 应用环境变量覆盖
        execution = workflow_config.get("execution", {})
        execution["max_retries"] = int(os.environ.get(
            "NEXUS_WORKFLOW_MAX_RETRIES", 
            execution.get("max_retries", 3)
        ))
        execution["stage_timeout_seconds"] = int(os.environ.get(
            "NEXUS_WORKFLOW_STAGE_TIMEOUT",
            execution.get("stage_timeout_seconds", 3600)
        ))
        workflow_config["execution"] = execution
        
        context = workflow_config.get("context", {})
        context["max_tokens"] = int(os.environ.get(
            "NEXUS_WORKFLOW_MAX_CONTEXT_TOKENS",
            context.get("max_tokens", 100000)
        ))
        workflow_config["context"] = context
        
        return workflow_config
    
    def get_workflow_stages(self) -> list:
        """
        获取工作流阶段定义
        
        Returns:
            list: 阶段定义列表
        """
        workflow_config = self.get("workflow", {})
        return workflow_config.get("stages", [])
    
    def get_dynamodb_config(self) -> Dict[str, Any]:
        """
        获取 DynamoDB 配置
        
        支持环境变量覆盖：
        - NEXUS_DYNAMODB_TABLE_PREFIX: 表名前缀
        - NEXUS_DYNAMODB_PROJECTS_TABLE: 项目表名
        - NEXUS_DYNAMODB_STAGES_TABLE: 阶段表名
        - NEXUS_DYNAMODB_TASKS_TABLE: 任务表名
        
        Returns:
            Dict: DynamoDB 配置字典
            
        Validates: Requirement 8.6 - 环境变量覆盖
        """
        dynamodb_config = self.get("dynamodb", {})
        
        # 应用环境变量覆盖
        dynamodb_config["table_prefix"] = os.environ.get(
            "NEXUS_DYNAMODB_TABLE_PREFIX",
            dynamodb_config.get("table_prefix", "nexus_")
        )
        
        tables = dynamodb_config.get("tables", {})
        tables["projects"] = os.environ.get(
            "NEXUS_DYNAMODB_PROJECTS_TABLE",
            tables.get("projects", "nexus_projects")
        )
        tables["stages"] = os.environ.get(
            "NEXUS_DYNAMODB_STAGES_TABLE",
            tables.get("stages", "nexus_stages")
        )
        tables["tasks"] = os.environ.get(
            "NEXUS_DYNAMODB_TASKS_TABLE",
            tables.get("tasks", "nexus_tasks")
        )
        dynamodb_config["tables"] = tables
        
        return dynamodb_config
    
    def get_sqs_config(self) -> Dict[str, Any]:
        """
        获取 SQS 配置
        
        支持环境变量覆盖：
        - NEXUS_SQS_BUILD_QUEUE: 构建队列名
        - NEXUS_SQS_DEPLOY_QUEUE: 部署队列名
        - NEXUS_SQS_VISIBILITY_TIMEOUT: 消息可见性超时
        
        Returns:
            Dict: SQS 配置字典
            
        Validates: Requirement 8.6 - 环境变量覆盖
        """
        sqs_config = self.get("sqs", {})
        
        # 应用环境变量覆盖
        queues = sqs_config.get("queues", {})
        queues["build"] = os.environ.get(
            "NEXUS_SQS_BUILD_QUEUE",
            queues.get("build", "nexus-build-queue")
        )
        queues["deploy"] = os.environ.get(
            "NEXUS_SQS_DEPLOY_QUEUE",
            queues.get("deploy", "nexus-deploy-queue")
        )
        sqs_config["queues"] = queues
        
        sqs_config["visibility_timeout"] = int(os.environ.get(
            "NEXUS_SQS_VISIBILITY_TIMEOUT",
            sqs_config.get("visibility_timeout", 3600)
        ))
        
        return sqs_config
    
    def has_section(self, section_name: str) -> bool:
        """
        检查配置部分是否存在
        
        Args:
            section_name (str): 配置部分名称
            
        Returns:
            bool: 是否存在
        """
        config = self.config.get("default-config", {})
        return section_name in config
    
    def list_sections(self) -> list:
        """
        列出所有配置部分
        
        Returns:
            list: 配置部分名称列表
        """
        config = self.config.get("default-config", {})
        return list(config.keys())
    
    def reload_config(self):
        """重新加载配置文件"""
        self.config = self._load_config()
        self._configure_logging()


# 全局配置实例
config = ConfigLoader()


def get_config() -> ConfigLoader:
    """
    获取全局配置实例
    
    Returns:
        ConfigLoader: 配置加载器实例
    """
    return config


if __name__ == "__main__":
    """配置测试"""
    loader = ConfigLoader()
    print("AWS配置:", loader.get_aws_config())
    print("Bedrock配置:", loader.get_bedrock_config())
    print("Strands配置:", loader.get_strands_config())
    print("AgentCore配置:", loader.get_agentcore_config())
    print("MCP配置:", loader.get_mcp_config())
    print("多模态解析器配置:", loader.get_multimodal_parser_config())
    print("日志配置:", loader.get_logging_config())
    print("工作流版本配置:", loader.get_workflow_version_config())
    print("工作流引擎配置:", loader.get_workflow_config())
    print("工作流阶段定义:", loader.get_workflow_stages())
    print("DynamoDB配置:", loader.get_dynamodb_config())
    print("SQS配置:", loader.get_sqs_config())
    print("所有配置部分:", loader.list_sections())
    
    # 测试嵌套配置获取
    s3_bucket = loader.get_nested("multimodal_parser", "aws", "s3_bucket")
    print(f"多模态解析器S3存储桶: {s3_bucket}")
    
    # 测试部分配置获取
    multimodal_config = loader.get_section("multimodal_parser")
    print(f"多模态解析器配置部分: {multimodal_config}")
    
    # 测试环境变量覆盖
    print("\n测试环境变量覆盖:")
    otel_endpoint = loader.get_with_env_override(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
        default="http://localhost:4318"
    )
    print(f"OTEL端点: {otel_endpoint}")