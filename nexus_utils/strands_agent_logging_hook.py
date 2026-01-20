#!/usr/bin/env python3
"""
基于Strands官方Hooks的Agent日志系统
"""

from typing import Any, Dict, Any as AnyType
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    BeforeInvocationEvent, 
    AfterInvocationEvent
)
from strands.experimental.hooks import (
    BeforeToolInvocationEvent,
    AfterToolInvocationEvent
)
import time
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import yaml


# 全局配置加载
_LOGGING_CONFIG: Dict[str, AnyType] | None = None


def load_logging_config() -> Dict[str, AnyType]:
    """
    加载 logging_config.yaml 配置

    Returns:
        配置字典（加载失败时返回空 dict）
    """
    global _LOGGING_CONFIG
    if _LOGGING_CONFIG is not None:
        return _LOGGING_CONFIG

    try:
        # 项目根目录为当前文件的上级目录
        project_root = Path(__file__).resolve().parent.parent
        config_path = project_root / "config" / "logging_config.yaml"
        if not config_path.exists():
            _LOGGING_CONFIG = {}
            return _LOGGING_CONFIG

        with config_path.open("r", encoding="utf-8") as f:
            _LOGGING_CONFIG = yaml.safe_load(f) or {}
    except Exception:
        # 任何异常都不影响主流程，只是失去增强配置能力
        _LOGGING_CONFIG = {}

    return _LOGGING_CONFIG

# 颜色代码
class Colors:
    # 基础颜色定义
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

    _enabled = True
    _original_values: Dict[str, str] = {}

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        """
        根据配置启用/禁用彩色输出
        """
        if not cls._original_values:
            # 首次调用时保存原始值，便于再次启用
            for attr in [
                "RESET", "BOLD", "RED", "GREEN", "YELLOW",
                "BLUE", "MAGENTA", "CYAN", "WHITE", "GRAY"
            ]:
                cls._original_values[attr] = getattr(cls, attr)

        cls._enabled = enabled
        if not enabled:
            # 禁用时把所有颜色码清空
            for attr in cls._original_values.keys():
                setattr(cls, attr, "")
        else:
            # 启用时恢复原始颜色码
            for attr, value in cls._original_values.items():
                setattr(cls, attr, value)

class AgentLoggingHook(HookProvider):
    """Agent日志Hook，用于记录Agent的执行情况"""
    
    def __init__(self, agent_name: str = "Unknown"):
        """
        初始化Agent日志Hook
        
        Args:
            agent_name: Agent的名称
        """
        self.agent_name = agent_name
        self.start_time = None
        self.request_id = None
        self.tool_count = 0
        self.config = load_logging_config()

        enhanced_cfg = self.config.get("enhanced_logging", {})
        strands_cfg = self.config.get("strands_hooks", {})

        # 截断配置
        truncate_cfg = enhanced_cfg.get("truncate_length", {}) if isinstance(enhanced_cfg.get("truncate_length", {}), dict) else {}
        self.truncate_input = int(truncate_cfg.get("input", 300))
        self.truncate_output = int(truncate_cfg.get("output", 300))
        self.truncate_tool_result = int(truncate_cfg.get("tool_result", 200))

        # Hook 行为配置
        self.enable_enhanced_logging = bool(strands_cfg.get("enable_enhanced_logging", True))
        self.log_all_agent_calls = bool(strands_cfg.get("log_all_agent_calls", True))
        self.log_all_tool_calls = bool(strands_cfg.get("log_all_tool_calls", True))
        self.log_arguments = bool(strands_cfg.get("log_arguments", True))
        self.log_results = bool(strands_cfg.get("log_results", True))
        self.sensitive_fields = strands_cfg.get("sensitive_fields", []) or []

        # 彩色输出开关
        enable_colors = bool(enhanced_cfg.get("enable_colors", True))
        Colors.set_enabled(enable_colors)

        # 分隔线配置
        separators_cfg = enhanced_cfg.get("separators", {}) if isinstance(enhanced_cfg.get("separators", {}), dict) else {}
        self.workflow_sep_char = separators_cfg.get("workflow", "=")
        self.agent_sep_char = separators_cfg.get("agent", "-")
        self.tool_sep_char = separators_cfg.get("tool", ".")
        
        # 设置日志记录器
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        enhanced_cfg = self.config.get("enhanced_logging", {})

        # 日志文件路径及是否写文件
        log_file = enhanced_cfg.get("log_file", "logs/nexus_ai.log")
        log_to_file = bool(enhanced_cfg.get("log_to_file", True))
        log_level_str = str(enhanced_cfg.get("log_level", "INFO")).upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        # 配置日志记录器
        self.logger = logging.getLogger(f"agent.{self.agent_name}")
        self.logger.setLevel(log_level)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            if log_to_file:
                try:
                    # 确保日志目录存在
                    log_dir = os.path.dirname(log_file)
                    if log_dir:
                        os.makedirs(log_dir, exist_ok=True)

                    file_handler = logging.FileHandler(log_file, encoding='utf-8')
                    file_handler.setLevel(log_level)
                    file_handler.setFormatter(formatter)
                    self.logger.addHandler(file_handler)
                except PermissionError as e:
                    # 在容器环境中可能没有写入权限，静默处理
                    print(f"⚠️ 无法创建日志文件 {log_file}: {e}，将仅使用控制台输出")
                except Exception as e:
                    print(f"⚠️ 设置文件日志失败: {e}，将仅使用控制台输出")
            
            # 可选：如有需要，也可以添加控制台 handler（当前已有 print 输出，一般不再重复）
    
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """注册所有Hook回调"""
        # 如果在配置中关闭了增强日志，直接返回
        if not self.enable_enhanced_logging:
            return

        # 注册主要的Agent生命周期事件
        if self.log_all_agent_calls:
            registry.add_callback(BeforeInvocationEvent, self.log_agent_start)
            registry.add_callback(AfterInvocationEvent, self.log_agent_end)
        
        # 注册工具调用事件（使用实验性事件）
        if self.log_all_tool_calls:
            try:
                registry.add_callback(BeforeToolInvocationEvent, self.log_tool_start)
                registry.add_callback(AfterToolInvocationEvent, self.log_tool_end)
            except Exception as e:
                self.logger.warning(f"无法注册工具调用Hook - {self.agent_name}: {e}")

    def _truncate(self, text: str, max_len: int) -> str:
        """根据配置截断字符串"""
        if max_len is None or max_len <= 0:
            return text
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    def _mask_sensitive(self, data: AnyType) -> AnyType:
        """
        根据配置中的 sensitive_fields 对数据进行敏感信息脱敏
        仅对 dict 类型做键级别过滤，其他类型原样返回
        """
        if not self.sensitive_fields:
            return data

        try:
            if isinstance(data, dict):
                masked: Dict[AnyType, AnyType] = {}
                for k, v in data.items():
                    if isinstance(k, str) and any(sf.lower() in k.lower() for sf in self.sensitive_fields):
                        masked[k] = "***"
                    else:
                        masked[k] = v
                return masked
        except Exception:
            # 避免脱敏失败导致主流程异常
            return data

        return data
    
    def log_agent_start(self, event: BeforeInvocationEvent) -> None:
        """记录Agent开始执行"""
        self.start_time = time.time()
        self.request_id = id(event)
        self.tool_count = 0
        
        # 获取输入数据
        input_data = None
        if hasattr(event, 'request') and event.request:
            if hasattr(event.request, 'messages') and event.request.messages:
                input_data = event.request.messages[-1].content if event.request.messages else None
            elif hasattr(event.request, 'content'):
                input_data = event.request.content
        
        # 记录到日志文件
        self.logger.info(f"🚀 AGENT开始执行: {self.agent_name}")
        self.logger.info(f"   📍 请求ID: {self.request_id}")
        self.logger.info(f"   ⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.log_arguments and input_data is not None:
            input_str = str(input_data)
            input_str = self._truncate(input_str, self.truncate_input)
            self.logger.info(f"   📥 输入内容: {input_str}")
        
        self.logger.info(f"   🔄 正在处理中...")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}🚀 [AGENT] {self.agent_name} 开始执行{Colors.RESET}")
        print(f"{Colors.BLUE}📍 请求ID:\t{self.request_id}{Colors.RESET}")
        print(f"{Colors.BLUE}⏰ 时间:\t{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
        
        if self.log_arguments and input_data is not None:
            input_str = str(input_data)
            input_str = self._truncate(input_str, self.truncate_input)
            print(f"{Colors.BLUE}📥 输入:\t{input_str}{Colors.RESET}")
        
        print(f"{Colors.YELLOW}🔄 状态:\t处理中...{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{self.workflow_sep_char * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}📋 工具调用列表:{Colors.RESET}")
        print(f"{Colors.MAGENTA}{self.agent_sep_char * 80}{Colors.RESET}")
    
    def log_agent_end(self, event: AfterInvocationEvent) -> None:
        """记录Agent结束执行"""
        if self.start_time:
            duration = time.time() - self.start_time
        else:
            duration = 0
        
        # 获取输出数据
        output_data = None
        if hasattr(event, 'response') and event.response:
            if hasattr(event.response, 'content'):
                output_data = event.response.content
            elif hasattr(event.response, 'messages') and event.response.messages:
                output_data = event.response.messages[-1].content if event.response.messages else None
        
        # 记录到日志文件
        self.logger.info(f"🎉 AGENT执行完成: {self.agent_name}")
        self.logger.info(f"   📍 请求ID: {self.request_id}")
        self.logger.info(f"   ⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"   ⏱️  总耗时: {duration:.2f}秒")
        
        if self.log_results and output_data is not None:
            output_str = str(output_data)
            output_str = self._truncate(output_str, self.truncate_output)
            self.logger.info(f"   📤 输出结果: {output_str}")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"{Colors.MAGENTA}{self.agent_sep_char * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{self.workflow_sep_char * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 [AGENT] {self.agent_name} 执行完成{Colors.RESET}")
        print(f"{Colors.BLUE}📍 请求ID:\t{self.request_id}{Colors.RESET}")
        print(f"{Colors.BLUE}⏰ 时间:\t{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
        print(f"{Colors.MAGENTA}⏱️  耗时:\t{duration:.2f}秒{Colors.RESET}")
        print(f"{Colors.YELLOW}🔧 工具调用:\t{self.tool_count}次{Colors.RESET}")
        
        if self.log_results and output_data is not None:
            output_str = str(output_data)
            output_str = self._truncate(output_str, self.truncate_output)
            print(f"{Colors.BLUE}📤 输出:\t{output_str}{Colors.RESET}")
        
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")
        
        # 重置状态
        self.start_time = None
        self.request_id = None
        self.tool_count = 0
    
    def log_tool_start(self, event: Any) -> None:
        """记录工具开始调用"""
        self.tool_count += 1
        tool_name = "Unknown"
        tool_params = {}
        
        # 尝试从不同的事件类型中获取工具信息
        if hasattr(event, 'tool_use'):
            tool_name = event.tool_use.get('name', 'Unknown')
            tool_params = event.tool_use.get('input', {})
        elif hasattr(event, 'selected_tool'):
            tool_name = getattr(event.selected_tool, 'name', 'Unknown')
            if hasattr(event, 'tool_use') and event.tool_use:
                tool_params = event.tool_use.get('input', {})
        
        # 记录到日志文件
        self.logger.info(f"   🔧 [TOOL] {self.agent_name} 调用工具: {tool_name}")
        
        if self.log_arguments and tool_params:
            safe_params = self._mask_sensitive(tool_params)
            param_str = json.dumps(safe_params, ensure_ascii=False, indent=2)
            param_str = self._truncate(param_str, self.truncate_tool_result)
            self.logger.info(f"      📋 参数: {param_str}")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"{Colors.YELLOW}🔧 [{self.tool_count:02d}] 调用工具:\t{tool_name}{Colors.RESET}")
        
        if self.log_arguments and tool_params:
            # 简化参数显示（只显示脱敏后的前若干项）
            safe_params = self._mask_sensitive(tool_params)
            items = list(safe_params.items())
            if len(items) > 0:
                param_summary = ", ".join([f"{k}={v}" for k, v in items[:3]])
                if len(items) > 3:
                    param_summary += "..."
                param_summary = self._truncate(param_summary, self.truncate_tool_result)
                print(f"{Colors.CYAN}   📋 参数:\t{param_summary}{Colors.RESET}")
    
    def log_tool_end(self, event: Any) -> None:
        """记录工具调用结束"""
        tool_name = "Unknown"
        tool_result = None
        
        # 尝试从不同的事件类型中获取工具信息
        if hasattr(event, 'tool_use'):
            tool_name = event.tool_use.get('name', 'Unknown')
        elif hasattr(event, 'selected_tool'):
            tool_name = getattr(event.selected_tool, 'name', 'Unknown')
        
        # 尝试获取工具结果
        if hasattr(event, 'result'):
            tool_result = event.result
        
        # 记录到日志文件
        self.logger.info(f"   ✅ [TOOL] {self.agent_name} 工具完成: {tool_name}")
        
        if self.log_results and tool_result is not None:
            safe_result = self._mask_sensitive(tool_result) if isinstance(tool_result, dict) else tool_result
            result_str = str(safe_result)
            result_str = self._truncate(result_str, self.truncate_tool_result)
            self.logger.info(f"      📤 结果: {result_str}")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"{Colors.GREEN}✅ [{self.tool_count:02d}] 工具完成:\t{tool_name}{Colors.RESET}")
        
        if self.log_results and tool_result is not None:
            # 简化结果显示
            safe_result = self._mask_sensitive(tool_result) if isinstance(tool_result, dict) else tool_result
            result_str = str(safe_result)
            result_str = self._truncate(result_str, self.truncate_tool_result)
            print(f"{Colors.CYAN}   📤 结果:\t{result_str}{Colors.RESET}")
        
        print(f"{Colors.MAGENTA}   {self.tool_sep_char * 40}{Colors.RESET}")


def create_agent_logging_hook(agent_name: str) -> AgentLoggingHook:
    """
    创建Agent日志Hook
    
    Args:
        agent_name: Agent的名称
    
    Returns:
        AgentLoggingHook实例
    """
    return AgentLoggingHook(agent_name)
