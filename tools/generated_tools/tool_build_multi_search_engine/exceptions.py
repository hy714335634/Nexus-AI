#!/usr/bin/env python3
"""
自定义异常类模块
定义多搜索引擎工具的自定义异常类
"""


class SearchEngineError(Exception):
    """搜索引擎错误基类"""
    
    def __init__(self, engine: str, message: str):
        """
        初始化搜索引擎错误
        
        Args:
            engine: 搜索引擎名称
            message: 错误信息
        """
        self.engine = engine
        self.message = message
        super().__init__(f"[{engine}] {message}")


class EngineUnavailableError(SearchEngineError):
    """搜索引擎不可用异常"""
    pass


class ParseError(SearchEngineError):
    """结果解析错误异常"""
    pass


class ValidationError(Exception):
    """参数验证错误异常"""
    
    def __init__(self, message: str):
        """
        初始化验证错误
        
        Args:
            message: 错误信息
        """
        self.message = message
        super().__init__(message)
