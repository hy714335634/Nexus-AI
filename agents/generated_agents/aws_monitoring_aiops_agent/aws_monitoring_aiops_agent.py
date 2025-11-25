#!/usr/bin/env python3
"""
AWS CloudWatch 智能监控与AIOps Agent

专业的AWS CloudWatch监控与AIOps专家，能够自动监控AWS CloudWatch指标、
分析日志数据，检测异常，进行根因分析，并生成自愈脚本，帮助运维团队
快速响应和解决AWS环境中的问题。

功能包括：
1. 监控指标获取与异常检测：收集和分析AWS CloudWatch指标，识别异常模式和阈值偏差
2. 多维度AWS服务监控：监控EC2、Lambda、RDS、ECS、API Gateway、ALB/ELB等多种AWS服务
3. 日志深度分析与根因推断：分析CloudWatch日志，识别错误模式，推断问题根因
4. 上下文关联分析：关联指标异常与日志事件，建立完整因果链
5. 自愈脚本生成：根据分析结果生成Shell、Python或AWS CLI修复脚本
6. 结构化分析报告生成：创建清晰、可操作的分析报告和修复建议

支持两种运行模式：
- 一次性分析模式：针对特定告警或问题进行深入分析和诊断
- 持续监控模式：定期轮询CloudWatch，主动发现和分析潜在问题
"""

import os
import json
import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class AWSMonitoringAIOpsAgent:
    """
    AWS CloudWatch 智能监控与AIOps Agent类
    
    提供AWS CloudWatch监控、日志分析、异常检测、根因分析和自愈脚本生成功能。
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化AWS监控AIOps Agent
        
        Args:
            config_file: 配置文件路径，如果不提供则使用默认配置
        """
        self.config = self._load_config(config_file)
        self.agent = self._initialize_agent()
        
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        default_config = {
            "agent_params": {
                "env": "production",
                "version": "latest",
                "model_id": "default"
            },
            "default_region": "us-east-1",
            "monitoring_interval_minutes": 5,
            "log_query_max_duration_hours": 24,
            "max_retries": 3,
            "retry_delay_seconds": 1
        }
        
        if not config_file:
            return default_config
        
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # 合并用户配置和默认配置
                for key, value in user_config.items():
                    if key in default_config and isinstance(value, dict) and isinstance(default_config[key], dict):
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
                return default_config
        except Exception as e:
            print(f"⚠️ 配置文件加载失败: {e}，使用默认配置")
            return default_config
    
    def _initialize_agent(self):
        """
        初始化Agent实例
        
        Returns:
            创建的Agent实例
        """
        agent_params = self.config.get("agent_params", {})
        
        # 使用agent_factory创建agent
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/aws_monitoring_aiops_agent/aws_monitoring_aiops_agent",
            **agent_params
        )
        
        return agent
    
    def analyze_alarm(self, alarm_info: Dict[str, Any], region: Optional[str] = None) -> str:
        """
        一次性分析模式：分析特定告警
        
        Args:
            alarm_info: 告警信息字典，包含告警ID、名称、时间等
            region: AWS区域，如果不提供则使用配置中的默认区域
            
        Returns:
            分析结果和建议
        """
        if not region:
            region = self.config.get("default_region", "us-east-1")
        
        # 构建分析请求
        request = {
            "运行模式": "一次性分析",
            "AWS区域": region,
            "告警信息": alarm_info,
            "时间窗口": self._get_time_window_for_alarm(alarm_info)
        }
        
        # 调用Agent进行分析
        result = self.agent(json.dumps(request, ensure_ascii=False))
        return result
    
    def analyze_issue(self, issue_description: str, resources: List[str], region: Optional[str] = None, 
                     time_window_hours: int = 6) -> str:
        """
        一次性分析模式：分析特定问题
        
        Args:
            issue_description: 问题描述
            resources: 相关资源列表
            region: AWS区域，如果不提供则使用配置中的默认区域
            time_window_hours: 分析时间窗口（小时）
            
        Returns:
            分析结果和建议
        """
        if not region:
            region = self.config.get("default_region", "us-east-1")
        
        # 计算时间窗口
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # 构建分析请求
        request = {
            "运行模式": "一次性分析",
            "AWS区域": region,
            "问题描述": issue_description,
            "监控目标": resources,
            "时间窗口": {
                "开始时间": start_time.isoformat(),
                "结束时间": end_time.isoformat()
            }
        }
        
        # 调用Agent进行分析
        result = self.agent(json.dumps(request, ensure_ascii=False))
        return result
    
    def start_continuous_monitoring(self, regions: List[str], resources: Dict[str, List[str]], 
                                  duration_minutes: Optional[int] = None) -> None:
        """
        启动持续监控模式
        
        Args:
            regions: 要监控的AWS区域列表
            resources: 要监控的资源字典，键为资源类型，值为资源ID列表
            duration_minutes: 监控持续时间（分钟），如果不提供则持续运行直到中断
        """
        monitoring_interval = self.config.get("monitoring_interval_minutes", 5)
        start_time = datetime.utcnow()
        
        print(f"📊 开始持续监控 - 间隔: {monitoring_interval}分钟")
        print(f"🌎 监控区域: {', '.join(regions)}")
        print(f"🎯 监控资源: {json.dumps(resources, indent=2, ensure_ascii=False)}")
        
        try:
            iteration = 1
            while True:
                current_time = datetime.utcnow()
                elapsed_minutes = (current_time - start_time).total_seconds() / 60
                
                # 检查是否达到指定的持续时间
                if duration_minutes and elapsed_minutes >= duration_minutes:
                    print(f"✅ 监控完成 - 持续时间: {duration_minutes}分钟")
                    break
                
                print(f"\n⏱️ 监控迭代 #{iteration} - {current_time.isoformat()}")
                
                # 构建监控请求
                request = {
                    "运行模式": "持续监控",
                    "AWS区域": regions,
                    "监控目标": resources,
                    "时间窗口": {
                        "开始时间": (current_time - timedelta(minutes=monitoring_interval)).isoformat(),
                        "结束时间": current_time.isoformat()
                    }
                }
                
                # 调用Agent进行监控
                try:
                    result = self.agent(json.dumps(request, ensure_ascii=False))
                    print(result)
                except Exception as e:
                    print(f"❌ 监控迭代失败: {e}")
                
                # 等待下一个监控间隔
                iteration += 1
                time.sleep(monitoring_interval * 60)
                
        except KeyboardInterrupt:
            print("\n🛑 监控已手动停止")
    
    def _get_time_window_for_alarm(self, alarm_info: Dict[str, Any]) -> Dict[str, str]:
        """
        根据告警信息计算合适的时间窗口
        
        Args:
            alarm_info: 告警信息字典
            
        Returns:
            包含开始时间和结束时间的字典
        """
        # 从告警信息中获取时间，如果没有则使用当前时间
        alarm_time_str = alarm_info.get("time", None)
        if alarm_time_str:
            try:
                alarm_time = datetime.fromisoformat(alarm_time_str.replace('Z', '+00:00'))
            except ValueError:
                alarm_time = datetime.utcnow()
        else:
            alarm_time = datetime.utcnow()
        
        # 设置时间窗口，告警前后的时间范围
        hours_before = min(3, self.config.get("log_query_max_duration_hours", 24) / 2)
        hours_after = min(1, self.config.get("log_query_max_duration_hours", 24) / 4)
        
        start_time = alarm_time - timedelta(hours=hours_before)
        end_time = alarm_time + timedelta(hours=hours_after)
        
        return {
            "开始时间": start_time.isoformat(),
            "结束时间": end_time.isoformat()
        }


# 创建Agent实例的便捷函数
def create_aws_monitoring_agent(config_file: Optional[str] = None) -> AWSMonitoringAIOpsAgent:
    """
    创建AWS监控AIOps Agent实例
    
    Args:
        config_file: 配置文件路径，如果不提供则使用默认配置
        
    Returns:
        AWSMonitoringAIOpsAgent实例
    """
    return AWSMonitoringAIOpsAgent(config_file)


if __name__ == "__main__":
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='AWS CloudWatch 智能监控与AIOps Agent')
    
    # 通用参数
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS区域')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='运行模式')
    
    # 一次性分析模式 - 告警
    alarm_parser = subparsers.add_parser('alarm', help='分析特定告警')
    alarm_parser.add_argument('--alarm-id', type=str, required=True, help='告警ID')
    alarm_parser.add_argument('--alarm-name', type=str, help='告警名称')
    alarm_parser.add_argument('--alarm-time', type=str, help='告警时间(ISO格式)')
    
    # 一次性分析模式 - 问题
    issue_parser = subparsers.add_parser('issue', help='分析特定问题')
    issue_parser.add_argument('--description', type=str, required=True, help='问题描述')
    issue_parser.add_argument('--resources', type=str, required=True, help='相关资源列表(逗号分隔)')
    issue_parser.add_argument('--time-window', type=int, default=6, help='分析时间窗口(小时)')
    
    # 持续监控模式
    monitor_parser = subparsers.add_parser('monitor', help='启动持续监控')
    monitor_parser.add_argument('--regions', type=str, help='要监控的AWS区域列表(逗号分隔)')
    monitor_parser.add_argument('--resources-file', type=str, required=True, help='要监控的资源JSON文件路径')
    monitor_parser.add_argument('--duration', type=int, help='监控持续时间(分钟)')
    
    args = parser.parse_args()
    
    # 创建Agent实例
    agent = create_aws_monitoring_agent(args.config)
    
    # 根据命令执行相应的功能
    if args.command == 'alarm':
        # 构建告警信息
        alarm_info = {
            "id": args.alarm_id,
            "name": args.alarm_name if args.alarm_name else args.alarm_id,
            "time": args.alarm_time if args.alarm_time else datetime.utcnow().isoformat()
        }
        
        # 分析告警
        result = agent.analyze_alarm(alarm_info, args.region)
        print(result)
        
    elif args.command == 'issue':
        # 解析资源列表
        resources = [r.strip() for r in args.resources.split(',')]
        
        # 分析问题
        result = agent.analyze_issue(args.description, resources, args.region, args.time_window)
        print(result)
        
    elif args.command == 'monitor':
        # 解析区域列表
        regions = [args.region]
        if args.regions:
            regions = [r.strip() for r in args.regions.split(',')]
        
        # 加载资源文件
        try:
            with open(args.resources_file, 'r') as f:
                resources = json.load(f)
        except Exception as e:
            print(f"❌ 资源文件加载失败: {e}")
            exit(1)
        
        # 启动持续监控
        agent.start_continuous_monitoring(regions, resources, args.duration)
        
    else:
        parser.print_help()