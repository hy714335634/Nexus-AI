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
        
        # 创建日志目录
        if log_file:
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            filename=log_file
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