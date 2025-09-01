#!/usr/bin/env python3
"""
基于Strands官方Hooks的Agent日志系统
"""

from typing import Any
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

# 颜色代码
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

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
        
        # 设置日志记录器
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 使用现有的nexus_ai.log
        log_file = "logs/nexus_ai.log"
        
        # 配置日志记录器
        self.logger = logging.getLogger(f"agent.{self.agent_name}")
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 设置格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
    
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """注册所有Hook回调"""
        # 注册主要的Agent生命周期事件
        registry.add_callback(BeforeInvocationEvent, self.log_agent_start)
        registry.add_callback(AfterInvocationEvent, self.log_agent_end)
        
        # 注册工具调用事件（使用实验性事件）
        try:
            registry.add_callback(BeforeToolInvocationEvent, self.log_tool_start)
            registry.add_callback(AfterToolInvocationEvent, self.log_tool_end)
        except Exception as e:
            self.logger.warning(f"无法注册工具调用Hook - {self.agent_name}: {e}")
    
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
        
        if input_data:
            input_str = str(input_data)
            if len(input_str) > 300:
                input_str = input_str[:300] + "..."
            self.logger.info(f"   📥 输入内容: {input_str}")
        
        self.logger.info(f"   🔄 正在处理中...")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}🚀 [AGENT] {self.agent_name} 开始执行{Colors.RESET}")
        print(f"{Colors.BLUE}📍 请求ID:\t{self.request_id}{Colors.RESET}")
        print(f"{Colors.BLUE}⏰ 时间:\t{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
        
        if input_data:
            input_str = str(input_data)
            if len(input_str) > 200:
                input_str = input_str[:200] + "..."
            print(f"{Colors.BLUE}📥 输入:\t{input_str}{Colors.RESET}")
        
        print(f"{Colors.YELLOW}🔄 状态:\t处理中...{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}📋 工具调用列表:{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'─'*80}{Colors.RESET}")
    
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
        
        if output_data:
            output_str = str(output_data)
            if len(output_str) > 300:
                output_str = output_str[:300] + "..."
            self.logger.info(f"   📤 输出结果: {output_str}")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"{Colors.MAGENTA}{'─'*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 [AGENT] {self.agent_name} 执行完成{Colors.RESET}")
        print(f"{Colors.BLUE}📍 请求ID:\t{self.request_id}{Colors.RESET}")
        print(f"{Colors.BLUE}⏰ 时间:\t{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}")
        print(f"{Colors.MAGENTA}⏱️  耗时:\t{duration:.2f}秒{Colors.RESET}")
        print(f"{Colors.YELLOW}🔧 工具调用:\t{self.tool_count}次{Colors.RESET}")
        
        if output_data:
            output_str = str(output_data)
            if len(output_str) > 200:
                output_str = output_str[:200] + "..."
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
        
        if tool_params:
            param_str = json.dumps(tool_params, ensure_ascii=False, indent=2)
            if len(param_str) > 200:
                param_str = param_str[:200] + "..."
            self.logger.info(f"      📋 参数: {param_str}")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"{Colors.YELLOW}🔧 [{self.tool_count:02d}] 调用工具:\t{tool_name}{Colors.RESET}")
        
        if tool_params:
            # 简化参数显示
            if len(tool_params) > 0:
                param_summary = ", ".join([f"{k}={v}" for k, v in list(tool_params.items())[:3]])
                if len(tool_params) > 3:
                    param_summary += "..."
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
        
        if tool_result:
            result_str = str(tool_result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            self.logger.info(f"      📤 结果: {result_str}")
        
        # 控制台输出（使用颜色高亮和制表符）
        print(f"{Colors.GREEN}✅ [{self.tool_count:02d}] 工具完成:\t{tool_name}{Colors.RESET}")
        
        if tool_result:
            # 简化结果显示
            result_str = str(tool_result)
            if len(result_str) > 100:
                result_str = result_str[:100] + "..."
            print(f"{Colors.CYAN}   📤 结果:\t{result_str}{Colors.RESET}")
        
        print(f"{Colors.MAGENTA}   {'─'*40}{Colors.RESET}")


def create_agent_logging_hook(agent_name: str) -> AgentLoggingHook:
    """
    创建Agent日志Hook
    
    Args:
        agent_name: Agent的名称
    
    Returns:
        AgentLoggingHook实例
    """
    return AgentLoggingHook(agent_name)
