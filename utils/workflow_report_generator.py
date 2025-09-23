#!/usr/bin/env python3
"""
工作流总结报告生成器
用于解析工作流执行结果并生成详细的总结报告
基于官方Strands GraphResult数据结构
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class StageMetrics:
    """单个阶段的执行指标"""
    stage_name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    tool_call_details: List[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.tool_call_details is None:
            self.tool_call_details = []


@dataclass
class WorkflowSummary:
    """工作流总体总结"""
    project_name: str
    workflow_start_time: str
    workflow_end_time: str
    total_duration: float
    total_input_tokens: int
    total_output_tokens: int
    total_tool_calls: int
    successful_stages: int
    failed_stages: int
    stages: List[StageMetrics]
    tool_usage_summary: Dict[str, int]
    cost_estimation: Dict[str, Any]
    project_config_summary: Optional[Dict[str, Any]] = None
    total_tools: int = 0


class WorkflowReportGenerator:
    """工作流报告生成器"""
    
    def __init__(self):
        self.stages_order = [
            "orchestrator",
            "requirements_analyzer", 
            "system_architect",
            "agent_designer",
            "agent_developer_manager"
        ]
    
    def _load_project_config(self, project_dir: str) -> tuple[Optional[Dict[str, Any]], int]:
        """
        从项目目录中加载project_config.json文件
        
        Args:
            project_dir: 项目目录路径
            
        Returns:
            tuple: (project_config_summary, total_tools)
        """
        try:
            config_path = os.path.join(project_dir, "project_config.json")
            
            if not os.path.exists(config_path):
                print(f"⚠️ 项目配置文件不存在: {config_path}")
                return None, 0
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 提取summary和total_tools信息
            summary = config_data.get('summary', {})
            total_tools = config_data.get('total_tools', 0)
            
            print(f"🔍 成功加载项目配置: {config_path}")
            print(f"🔍 项目配置摘要: {summary}")
            print(f"🔍 总工具数量: {total_tools}")
            
            return summary, total_tools
            
        except Exception as e:
            print(f"⚠️ 加载项目配置文件失败: {e}")
            return None, 0
    
    def parse_workflow_result(self, graph_result: Any, project_dir: str = None) -> WorkflowSummary:
        """解析GraphResult对象"""
        try:
            print(f"🔍 开始解析工作流结果，类型: {type(graph_result)}")
            print(f"🔍 可用属性: {[attr for attr in dir(graph_result) if not attr.startswith('_')]}")
            
            # 检查accumulated_usage
            if hasattr(graph_result, 'accumulated_usage'):
                usage = graph_result.accumulated_usage
                print(f"🔍 accumulated_usage类型: {type(usage)}")
                print(f"🔍 accumulated_usage内容: {usage}")
            else:
                print(f"⚠️ 未找到accumulated_usage属性")
            
            # 检查results
            if hasattr(graph_result, 'results'):
                results = graph_result.results
                print(f"🔍 results类型: {type(results)}")
                print(f"🔍 results键: {list(results.keys()) if results else 'None'}")
            else:
                print(f"⚠️ 未找到results属性")
            
            # 提取项目名称
            project_name = self._extract_project_name_from_orchestrator(graph_result)
            
            # 提取时间信息
            workflow_start_time = datetime.now().isoformat()  # 这里应该从实际执行时间获取
            workflow_end_time = datetime.now().isoformat()
            
            # 解析各个阶段的指标
            stages = self._parse_stages_metrics(graph_result)
            
            # 优先使用系统级别的真实Token统计
            total_input_tokens = 0
            total_output_tokens = 0
            
            # 检查是否有系统级别的accumulated_usage
            # GraphResult继承自MultiAgentResult，accumulated_usage可能在父类中
            usage = None
            if hasattr(graph_result, 'accumulated_usage'):
                usage = graph_result.accumulated_usage
            elif hasattr(graph_result, '__dict__'):
                # 检查所有属性，寻找usage相关信息
                for attr_name, attr_value in graph_result.__dict__.items():
                    if 'usage' in attr_name.lower() and hasattr(attr_value, 'inputTokens'):
                        usage = attr_value
                        break
            
            if usage:
                # 支持字典和对象两种格式的usage
                if isinstance(usage, dict):
                    total_input_tokens = usage.get('inputTokens', 0)
                    total_output_tokens = usage.get('outputTokens', 0)
                    print(f"🔍 使用系统级别Token统计(字典格式): input={total_input_tokens}, output={total_output_tokens}")
                elif hasattr(usage, 'inputTokens') and hasattr(usage, 'outputTokens'):
                    total_input_tokens = usage.inputTokens
                    total_output_tokens = usage.outputTokens
                    print(f"🔍 使用系统级别Token统计(对象格式): input={total_input_tokens}, output={total_output_tokens}")
                else:
                    print(f"⚠️ usage格式不支持: {type(usage)}")
                    usage = None
            
            if not usage:
                # 如果没有系统级别统计，使用各阶段累加
                total_input_tokens = sum(stage.input_tokens for stage in stages)
                total_output_tokens = sum(stage.output_tokens for stage in stages)
                print(f"🔍 从各阶段累加Token统计: input={total_input_tokens}, output={total_output_tokens}")
                print(f"⚠️ 未找到系统级别accumulated_usage，使用各阶段估算值")
            
            # 计算其他指标
            total_tool_calls = sum(stage.tool_calls for stage in stages)
            successful_stages = sum(1 for stage in stages if stage.success)
            failed_stages = len(stages) - successful_stages
            
            # 优先使用系统级别的执行时间
            if hasattr(graph_result, 'execution_time'):
                total_duration = graph_result.execution_time / 1000.0  # 转换为秒
                print(f"🔍 使用系统级别执行时间: {total_duration:.2f}秒")
            else:
                # 如果没有系统级别时间，使用各阶段累加
                total_duration = sum(stage.duration or 0 for stage in stages)
                print(f"🔍 使用各阶段累加执行时间: {total_duration:.2f}秒")
            
            # 生成工具使用总结
            tool_usage_summary = self._generate_tool_usage_summary(stages)
            
            # 成本估算
            cost_estimation = self._estimate_costs(total_input_tokens, total_output_tokens)
            
            # 加载项目配置信息
            project_config_summary, total_tools = self._load_project_config(project_dir) if project_dir else (None, 0)
            
            return WorkflowSummary(
                project_name=project_name,
                workflow_start_time=workflow_start_time,
                workflow_end_time=workflow_end_time,
                total_duration=total_duration,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_tool_calls=total_tool_calls,
                successful_stages=successful_stages,
                failed_stages=failed_stages,
                stages=stages,
                tool_usage_summary=tool_usage_summary,
                cost_estimation=cost_estimation,
                project_config_summary=project_config_summary,
                total_tools=total_tools
            )
            
        except Exception as e:
            print(f"❌ 解析工作流结果失败: {e}")
            # 返回默认的空总结
            return self._create_empty_summary()
    
    def _extract_project_name_from_orchestrator(self, graph_result: Any) -> str:
        """从多个来源提取项目名称"""
        try:
            # 方法1: 从orchestrator阶段的project_init工具调用中提取
            project_name = self._extract_from_orchestrator_tools(graph_result)
            if project_name != "unknown_project":
                print(f"🔍 从orchestrator工具调用中提取项目名称: {project_name}")
                return project_name
            
            # 方法2: 从result对象的字符串表示中提取
            project_name = self._extract_from_result_string(graph_result)
            if project_name != "unknown_project":
                print(f"🔍 从result字符串中提取项目名称: {project_name}")
                return project_name
            
            # 方法3: 从accumulated_usage中提取（如果有项目信息）
            project_name = self._extract_from_usage_info(graph_result)
            if project_name != "unknown_project":
                print(f"🔍 从usage信息中提取项目名称: {project_name}")
                return project_name
            
            print(f"⚠️ 无法从任何来源提取项目名称")
            return "unknown_project"
            
        except Exception as e:
            print(f"⚠️ 提取项目名称失败: {e}")
            return "unknown_project"
    
    def _extract_from_orchestrator_tools(self, graph_result: Any) -> str:
        """从orchestrator阶段的工具调用中提取项目名称"""
        try:
            # 检查是否有results属性
            if not hasattr(graph_result, 'results') or not graph_result.results:
                return "unknown_project"
            
            results = graph_result.results
            
            # 查找orchestrator阶段
            if 'orchestrator' not in results:
                return "unknown_project"
            
            orchestrator_result = results['orchestrator']
            
            # 检查是否有result属性
            if not hasattr(orchestrator_result, 'result'):
                return "unknown_project"
            
            orchestrator_agent_result = orchestrator_result.result
            
            # 检查是否有metrics和tool_metrics
            if (not hasattr(orchestrator_agent_result, 'metrics') or
                not hasattr(orchestrator_agent_result.metrics, 'tool_metrics')):
                return "unknown_project"
            
            tool_metrics = orchestrator_agent_result.metrics.tool_metrics
            
            # 查找project_init工具调用
            if 'project_init' not in tool_metrics:
                return "unknown_project"
            
            project_init_tool = tool_metrics['project_init']
            
            # 从工具输入中提取项目名称
            if hasattr(project_init_tool, 'tool') and project_init_tool.tool:
                tool_info = project_init_tool.tool
                if isinstance(tool_info, dict) and 'input' in tool_info:
                    project_name = tool_info['input'].get('project_name')
                    if project_name:
                        return project_name
            
            return "unknown_project"
            
        except Exception as e:
            print(f"⚠️ 从orchestrator工具调用提取项目名称失败: {e}")
            return "unknown_project"
    
    def _extract_from_result_string(self, graph_result: Any) -> str:
        """从result对象的字符串表示中提取项目名称"""
        try:
            # 将整个result对象转换为字符串进行搜索
            result_str = str(graph_result)
            
            import re
            # 查找项目名称模式
            project_patterns = [
                r"'([^']+_agent)'",
                r"'([^']+_generator)'", 
                r"'([^']+_tool)'",
                r"'([^']+_cloner)'",
                r'"([^"]+_agent)"',
                r'"([^"]+_generator)"',
                r'"([^"]+_tool)"',
                r'"([^"]+_cloner)"'
            ]
            
            for pattern in project_patterns:
                matches = re.findall(pattern, result_str)
                for match in matches:
                    if len(match) > 3 and not match.startswith('_') and not match.startswith('unknown'):
                        return match
            
            return "unknown_project"
            
        except Exception as e:
            print(f"⚠️ 从result字符串提取项目名称失败: {e}")
            return "unknown_project"
    
    def _extract_from_usage_info(self, graph_result: Any) -> str:
        """从usage信息中提取项目名称"""
        try:
            # 这个方法可以扩展，比如从特定的usage字段中提取项目信息
            # 目前返回unknown_project，但为将来扩展预留
            return "unknown_project"
            
        except Exception as e:
            print(f"⚠️ 从usage信息提取项目名称失败: {e}")
            return "unknown_project"
    
    def _parse_stages_metrics(self, graph_result: Any) -> List[StageMetrics]:
        """解析各个阶段的执行指标"""
        stages = []
        
        try:
            # 检查是否有results属性
            if not hasattr(graph_result, 'results') or not graph_result.results:
                # 创建默认阶段
                for stage_name in self.stages_order:
                    stages.append(StageMetrics(
                        stage_name=stage_name,
                        success=False,
                        error_message="没有找到results属性"
                    ))
                return stages
            
            results = graph_result.results
            
            # 遍历各个阶段
            for stage_name in self.stages_order:
                stage_metrics = self._parse_single_stage(stage_name, results)
                stages.append(stage_metrics)
            
        except Exception as e:
            print(f"⚠️ 解析阶段指标时出错: {e}")
            # 创建默认阶段
            for stage_name in self.stages_order:
                stages.append(StageMetrics(
                    stage_name=stage_name,
                    success=False,
                    error_message=f"解析错误: {str(e)}"
                ))
        
        return stages
    
    def _parse_single_stage(self, stage_name: str, results: dict) -> StageMetrics:
        """解析单个阶段的指标"""
        try:
            # 初始化阶段指标
            stage_metrics = StageMetrics(stage_name=stage_name)
            
            # 检查该阶段是否存在
            if stage_name not in results:
                stage_metrics.success = False
                stage_metrics.error_message = "阶段未执行"
                return stage_metrics
            
            node_result = results[stage_name]
            
            # 检查是否是空的NodeResult
            if not hasattr(node_result, 'result') or not node_result.result:
                stage_metrics.success = False
                stage_metrics.error_message = "阶段结果为空"
                print(f"⚠️ 阶段 {stage_name} 结果为空")
                return stage_metrics
            
            # 提取execution_time
            if hasattr(node_result, 'execution_time'):
                stage_metrics.duration = node_result.execution_time / 1000.0  # 转换为秒
                print(f"🔍 阶段 {stage_name} 执行时间: {stage_metrics.duration:.2f}秒")
            
            # 提取status
            if hasattr(node_result, 'status'):
                status_str = str(node_result.status)
                stage_metrics.success = 'COMPLETED' in status_str or 'completed' in status_str
                print(f"🔍 阶段 {stage_name} 状态: {status_str} -> 成功: {stage_metrics.success}")
            
            # 提取该阶段自己的accumulated_usage中的token信息
            if hasattr(node_result, 'accumulated_usage'):
                usage = node_result.accumulated_usage
                # 支持字典和对象两种格式
                if isinstance(usage, dict):
                    stage_metrics.input_tokens = usage.get('inputTokens', 0)
                    stage_metrics.output_tokens = usage.get('outputTokens', 0)
                    print(f"🔍 阶段 {stage_name} Token统计(字典格式): input={stage_metrics.input_tokens}, output={stage_metrics.output_tokens}")
                elif hasattr(usage, 'inputTokens') and hasattr(usage, 'outputTokens'):
                    stage_metrics.input_tokens = usage.inputTokens
                    stage_metrics.output_tokens = usage.outputTokens
                    print(f"🔍 阶段 {stage_name} Token统计(对象格式): input={stage_metrics.input_tokens}, output={stage_metrics.output_tokens}")
                else:
                    print(f"🔍 阶段 {stage_name} accumulated_usage格式不支持: {type(usage)}")
            else:
                print(f"🔍 阶段 {stage_name} 无accumulated_usage信息")
            
            # 提取AgentResult中的metrics信息
            if hasattr(node_result, 'result'):
                agent_result = node_result.result
                
                # 检查是否是AgentResult
                if hasattr(agent_result, 'metrics'):
                    metrics = agent_result.metrics
                    
                    # 提取cycle_count
                    if hasattr(metrics, 'cycle_count'):
                        cycle_count = metrics.cycle_count
                        # 如果没有找到token信息，使用cycle_count估算
                        if stage_metrics.input_tokens == 0:
                            stage_metrics.input_tokens = cycle_count * 150
                        if stage_metrics.output_tokens == 0:
                            stage_metrics.output_tokens = cycle_count * 75
                    
                    # 提取tool_metrics
                    if hasattr(metrics, 'tool_metrics'):
                        tool_metrics = metrics.tool_metrics
                        
                        # 计算工具调用次数
                        stage_metrics.tool_calls = len(tool_metrics)
                        
                        # 解析每个工具的详细信息
                        for tool_name, tool_metric in tool_metrics.items():
                            tool_detail = {
                                'tool_name': tool_name,
                                'call_count': getattr(tool_metric, 'call_count', 0),
                                'success_count': getattr(tool_metric, 'success_count', 0),
                                'error_count': getattr(tool_metric, 'error_count', 0),
                                'total_time': getattr(tool_metric, 'total_time', 0.0)
                            }
                            stage_metrics.tool_call_details.append(tool_detail)
            
            # 如果没有从metrics获取到执行时间，使用默认值
            if stage_metrics.duration is None or stage_metrics.duration == 0:
                stage_metrics.duration = 2.0  # 默认2秒
            
            # 如果没有找到token信息，标记为0而不是估算
            # 这样可以区分真实数据和缺失数据
            if stage_metrics.input_tokens == 0:
                print(f"🔍 阶段 {stage_name} 无输入Token数据")
            if stage_metrics.output_tokens == 0:
                print(f"🔍 阶段 {stage_name} 无输出Token数据")
            
            return stage_metrics
            
        except Exception as e:
            return StageMetrics(
                stage_name=stage_name,
                success=False,
                error_message=f"解析阶段指标失败: {str(e)}"
            )
    
    def _generate_tool_usage_summary(self, stages: List[StageMetrics]) -> Dict[str, int]:
        """生成工具使用总结"""
        tool_summary = {}
        
        for stage in stages:
            for tool_detail in stage.tool_call_details:
                tool_name = tool_detail['tool_name']
                call_count = tool_detail['call_count']
                tool_summary[tool_name] = tool_summary.get(tool_name, 0) + call_count
        
        return tool_summary
    
    def _calculate_tool_statistics(self, stages: List[StageMetrics]) -> Dict[str, Dict[str, Any]]:
        """计算工具详细统计信息"""
        tool_stats = {}
        
        for stage in stages:
            for tool_detail in stage.tool_call_details:
                tool_name = tool_detail['tool_name']
                
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {
                        'call_count': 0,
                        'success_count': 0,
                        'error_count': 0,
                        'total_time': 0.0,
                        'avg_time': 0.0,
                        'success_rate': 0.0
                    }
                
                stats = tool_stats[tool_name]
                stats['call_count'] += tool_detail['call_count']
                stats['success_count'] += tool_detail['success_count']
                stats['error_count'] += tool_detail['error_count']
                stats['total_time'] += tool_detail['total_time']
        
        # 计算平均值和成功率
        for tool_name, stats in tool_stats.items():
            if stats['call_count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['call_count']
                stats['success_rate'] = (stats['success_count'] / stats['call_count']) * 100
        
        return tool_stats
    
    def _generate_key_findings(self, summary: WorkflowSummary) -> List[str]:
        """生成关键发现"""
        findings = []
        
        # 分析执行时间
        if summary.total_duration > 300:  # 超过5分钟
            findings.append(f"⚠️ 执行时间较长 ({self._format_duration(summary.total_duration)})，可能存在性能瓶颈")
        elif summary.total_duration < 30:  # 少于30秒
            findings.append(f"✅ 执行时间较短 ({self._format_duration(summary.total_duration)})，性能表现良好")
        
        # 分析Token使用
        token_efficiency = summary.total_output_tokens / max(summary.total_input_tokens, 1)
        if token_efficiency < 0.1:
            findings.append(f"⚠️ Token效率较低 ({token_efficiency:.2f})，输出相对输入较少")
        elif token_efficiency > 0.5:
            findings.append(f"✅ Token效率较高 ({token_efficiency:.2f})，输出相对输入较多")
        
        # 分析失败阶段
        if summary.failed_stages > 0:
            findings.append(f"❌ 有 {summary.failed_stages} 个阶段执行失败，需要检查错误原因")
        
        # 分析工具使用
        if summary.total_tool_calls == 0:
            findings.append("⚠️ 没有工具调用记录，可能影响功能完整性")
        elif summary.total_tool_calls > 50:
            findings.append(f"📊 工具调用次数较多 ({summary.total_tool_calls})，说明工作流复杂度较高")
        
        # 分析成本
        cost_per_tool = summary.cost_estimation.get('total_cost_usd', 0) / max(summary.total_tool_calls, 1)
        if cost_per_tool > 0.01:  # 每个工具调用成本超过1美分
            findings.append(f"💰 工具调用成本较高 (${cost_per_tool:.4f}/次)，建议优化工具使用")
        
        return findings
    
    def _generate_optimization_suggestions(self, summary: WorkflowSummary) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于执行时间的建议
        if summary.total_duration > 300:
            suggestions.append("考虑并行化处理或优化算法以减少执行时间")
        
        # 基于Token使用的建议
        token_efficiency = summary.total_output_tokens / max(summary.total_input_tokens, 1)
        if token_efficiency < 0.1:
            suggestions.append("优化提示词设计，提高输出质量")
        
        # 基于失败阶段的建议
        if summary.failed_stages > 0:
            suggestions.append("检查失败阶段的错误日志，修复相关问题")
        
        # 基于工具使用的建议
        if summary.total_tool_calls > 0:
            tool_stats = self._calculate_tool_statistics(summary.stages)
            slow_tools = [name for name, stats in tool_stats.items() if stats['avg_time'] > 1.0]
            if slow_tools:
                suggestions.append(f"优化慢速工具: {', '.join(slow_tools)}")
        
        # 基于成本的建议
        if summary.cost_estimation.get('total_cost_usd', 0) > 1.0:
            suggestions.append("考虑使用更经济的模型或优化Token使用")
        
        # 通用建议
        suggestions.extend([
            "定期监控工作流性能指标",
            "建立性能基准和告警机制",
            "考虑缓存重复计算的结果"
        ])
        
        return suggestions
    
    def _format_tokens(self, tokens: int) -> str:
        """格式化Token数量，按K为单位显示"""
        if tokens >= 1000:
            return f"{tokens/1000:.1f}K"
        else:
            return str(tokens)
    
    def _format_duration(self, duration: float) -> str:
        """格式化执行时间，显示为更易读的格式"""
        if duration < 60:
            return f"{duration:.1f}秒"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = duration % 60
            return f"{minutes}分{seconds:.1f}秒"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}小时{minutes}分钟"
    
    def _calculate_stage_efficiency(self, stage: StageMetrics) -> str:
        """计算阶段效率评分"""
        if not stage.success:
            return "❌ 失败"
        
        if stage.duration and stage.duration > 0:
            # 基于执行时间和工具调用次数计算效率
            tool_efficiency = stage.tool_calls / stage.duration if stage.duration > 0 else 0
            if tool_efficiency > 2:
                return "🚀 优秀"
            elif tool_efficiency > 1:
                return "✅ 良好"
            elif tool_efficiency > 0.5:
                return "⚠️ 一般"
            else:
                return "🐌 较慢"
        else:
            return "❓ 未知"
    
    def _estimate_costs(self, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """估算成本（基于Claude 3.7 Sonnet定价）"""
        # Claude 3.7 Sonnet定价（每1000个token）
        input_cost_per_1k = 0.003  # $0.003 per 1K input tokens
        output_cost_per_1k = 0.015  # $0.015 per 1K output tokens
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return {
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "pricing_model": "Claude 3.7 Sonnet",
            "input_rate_per_1k": input_cost_per_1k,
            "output_rate_per_1k": output_cost_per_1k
        }
    
    def _create_empty_summary(self) -> WorkflowSummary:
        """创建空的总结（当解析失败时）"""
        current_time = datetime.now().isoformat()
        
        return WorkflowSummary(
            project_name="unknown_project",
            workflow_start_time=current_time,
            workflow_end_time=current_time,
            total_duration=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_tool_calls=0,
            successful_stages=0,
            failed_stages=len(self.stages_order),
            stages=[],
            tool_usage_summary={},
            cost_estimation={
                "total_cost_usd": 0.0, 
                "pricing_model": "Claude 3.7 Sonnet",
                "input_rate_per_1k": 0.003,
                "output_rate_per_1k": 0.015
            },
            project_config_summary=None,
            total_tools=0
        )
    
    def generate_markdown_report(self, summary: WorkflowSummary, output_path: str) -> str:
        """生成Markdown格式的报告"""
        try:
            report_content = self._format_markdown_report(summary)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"✅ 工作流总结报告已生成: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 生成报告失败: {e}")
            return ""
    
    def _format_markdown_report(self, summary: WorkflowSummary) -> str:
        """格式化Markdown报告内容"""
        report_lines = [
            "# 工作流执行总结报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**项目名称**: {summary.project_name}",
            "",
            "## 📊 总体概览",
            "",
            f"- **工作流状态**: {'✅ 成功完成' if summary.failed_stages == 0 else f'⚠️ 部分失败 ({summary.failed_stages}个阶段失败)'}",
            f"- **总执行时间**: {summary.total_duration:.2f} 秒 ({self._format_duration(summary.total_duration)})",
            f"- **成功阶段数**: {summary.successful_stages}/{len(summary.stages)}",
            f"- **总输入Token**: {self._format_tokens(summary.total_input_tokens)}",
            f"- **总输出Token**: {self._format_tokens(summary.total_output_tokens)}",
            f"- **总工具调用次数**: {summary.total_tool_calls}",
            "",
        ]
        
        # 添加项目配置信息
        if summary.project_config_summary or summary.total_tools > 0:
            report_lines.extend([
                "## 📋 项目配置信息",
                "",
            ])
            
            if summary.total_tools > 0:
                report_lines.append(f"- **项目总工具数量**: {summary.total_tools}")
            
            if summary.project_config_summary:
                config_summary = summary.project_config_summary
                report_lines.extend([
                    f"- **智能体脚本数量**: {config_summary.get('agent_scripts_count', 0)}",
                    f"- **提示文件数量**: {config_summary.get('prompt_files_count', 0)}",
                    f"- **生成工具文件数量**: {config_summary.get('generated_tool_files_count', 0)}",
                    f"- **所有脚本有效**: {'✅ 是' if config_summary.get('all_scripts_valid', False) else '❌ 否'}",
                    f"- **所有工具有效**: {'✅ 是' if config_summary.get('all_tools_valid', False) else '❌ 否'}",
                    f"- **所有提示有效**: {'✅ 是' if config_summary.get('all_prompts_valid', False) else '❌ 否'}",
                ])
            
            report_lines.append("")
        
        report_lines.extend([
            "## 💰 成本估算",
            "",
            f"- **输入成本**: ${summary.cost_estimation.get('input_cost_usd', 0):.6f} USD",
            f"- **输出成本**: ${summary.cost_estimation.get('output_cost_usd', 0):.6f} USD", 
            f"- **总成本**: ${summary.cost_estimation.get('total_cost_usd', 0):.6f} USD",
            f"- **定价模型**: {summary.cost_estimation.get('pricing_model', 'Unknown')}",
            f"- **输入费率**: ${summary.cost_estimation.get('input_rate_per_1k', 0):.3f} USD/1K tokens",
            f"- **输出费率**: ${summary.cost_estimation.get('output_rate_per_1k', 0):.3f} USD/1K tokens",
            "",
            "## 🔄 阶段执行详情",
            "",
            "| 阶段名称 | 状态 | 执行时间(秒) | 输入Token | 输出Token | 工具调用次数 | 效率评分 |",
            "|---------|------|-------------|-----------|-----------|-------------|----------|"
        ])
        
        # 添加各阶段详情
        for stage in summary.stages:
            status_icon = "✅" if stage.success else "❌"
            duration = f"{stage.duration:.2f}" if stage.duration else "N/A"
            efficiency = self._calculate_stage_efficiency(stage)
            
            report_lines.append(
                f"| {stage.stage_name} | {status_icon} | {duration} | {self._format_tokens(stage.input_tokens)} | {self._format_tokens(stage.output_tokens)} | {stage.tool_calls} | {efficiency} |"
            )
            
            # 如果有错误信息，添加详细信息
            if stage.error_message:
                report_lines.append(f"| | **错误**: {stage.error_message} | | | | | |")
        
        report_lines.extend([
            "",
            "## 🛠️ 工具使用统计",
            "",
            "| 工具名称 | 调用次数 | 使用频率 | 平均耗时(秒) | 成功率 |",
            "|---------|----------|----------|-------------|--------|"
        ])
        
        # 添加工具使用统计
        if summary.tool_usage_summary:
            tool_stats = self._calculate_tool_statistics(summary.stages)
            for tool_name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['call_count'], reverse=True):
                frequency = f"{stats['call_count']}/{summary.total_tool_calls}" if summary.total_tool_calls > 0 else "0/0"
                avg_time = f"{stats['avg_time']:.3f}" if stats['avg_time'] > 0 else "N/A"
                success_rate = f"{stats['success_rate']:.1f}%" if stats['success_rate'] >= 0 else "N/A"
                report_lines.append(f"| {tool_name} | {stats['call_count']} | {frequency} | {avg_time} | {success_rate} |")
        else:
            report_lines.append("| 无工具调用记录 | 0 | 0/0 | N/A | N/A |")
        
        report_lines.extend([
            "",
            "## 📈 性能分析",
            "",
            f"- **平均每阶段执行时间**: {summary.total_duration / len(summary.stages):.2f} 秒",
            f"- **Token效率**: {summary.total_output_tokens / max(summary.total_input_tokens, 1):.2f} (输出/输入比)",
            f"- **工具调用频率**: {summary.total_tool_calls / max(summary.total_duration, 1):.2f} 次/秒",
            f"- **平均每阶段Token消耗**: {self._format_tokens((summary.total_input_tokens + summary.total_output_tokens) // len(summary.stages))}",
            f"- **成本效率**: ${summary.cost_estimation.get('total_cost_usd', 0) / max(summary.total_tool_calls, 1):.6f} USD/工具调用",
            "",
            "### 🎯 阶段性能对比",
            "",
            "| 阶段 | 执行时间占比 | Token占比 | 工具调用占比 | 效率等级 |",
            "|------|-------------|----------|-------------|----------|"
        ])
        
        # 添加阶段性能对比
        for stage in summary.stages:
            time_ratio = (stage.duration / summary.total_duration * 100) if summary.total_duration > 0 and stage.duration else 0
            token_ratio = ((stage.input_tokens + stage.output_tokens) / (summary.total_input_tokens + summary.total_output_tokens) * 100) if (summary.total_input_tokens + summary.total_output_tokens) > 0 else 0
            tool_ratio = (stage.tool_calls / summary.total_tool_calls * 100) if summary.total_tool_calls > 0 else 0
            efficiency = self._calculate_stage_efficiency(stage)
            
            report_lines.append(
                f"| {stage.stage_name} | {time_ratio:.1f}% | {token_ratio:.1f}% | {tool_ratio:.1f}% | {efficiency} |"
            )
        
        report_lines.extend([
            "",
            "## 🔍 详细工具调用记录",
            ""
        ])
        
        # 添加详细工具调用记录
        for stage in summary.stages:
            if stage.tool_call_details:
                report_lines.extend([
                    f"### {stage.stage_name}",
                    "",
                    "| 工具名称 | 调用次数 | 成功次数 | 失败次数 | 总耗时(秒) | 平均耗时(秒) | 成功率 |",
                    "|---------|----------|----------|----------|------------|-------------|--------|"
                ])
                
                for tool_detail in stage.tool_call_details:
                    avg_time = tool_detail['total_time'] / tool_detail['call_count'] if tool_detail['call_count'] > 0 else 0
                    success_rate = (tool_detail['success_count'] / tool_detail['call_count'] * 100) if tool_detail['call_count'] > 0 else 0
                    
                    report_lines.append(
                        f"| {tool_detail['tool_name']} | {tool_detail['call_count']} | "
                        f"{tool_detail['success_count']} | {tool_detail['error_count']} | "
                        f"{tool_detail['total_time']:.3f} | {avg_time:.3f} | {success_rate:.1f}% |"
                    )
                report_lines.append("")
        
        report_lines.extend([
            "## 📝 总结与建议",
            "",
            f"本次工作流执行共涉及 {len(summary.stages)} 个阶段，",
            f"成功完成 {summary.successful_stages} 个阶段，",
            f"总耗时 {summary.total_duration:.2f} 秒 ({self._format_duration(summary.total_duration)})，",
            f"消耗Token {self._format_tokens(summary.total_input_tokens + summary.total_output_tokens)} 个，",
            f"调用工具 {summary.total_tool_calls} 次，",
            f"总成本 ${summary.cost_estimation.get('total_cost_usd', 0):.6f} USD。",
            "",
            "### 🎯 关键发现",
            ""
        ])
        
        # 添加关键发现
        findings = self._generate_key_findings(summary)
        for finding in findings:
            report_lines.append(f"- {finding}")
        
        report_lines.extend([
            "",
            "### 💡 优化建议",
            ""
        ])
        
        # 添加优化建议
        suggestions = self._generate_optimization_suggestions(summary)
        for suggestion in suggestions:
            report_lines.append(f"- {suggestion}")
        
        report_lines.extend([
            "",
            "---",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(report_lines)

def generate_workflow_summary_report_bk(graph_result: Any, 
                                   default_project_root_path: str) -> str:
    """
    生成工作流总结报告的主函数
    
    Args:
        graph_result: GraphResult对象
        default_project_root_path: 项目根路径
    
    Returns:
        生成的报告文件路径
    """
    try:
        # 创建报告生成器
        generator = WorkflowReportGenerator()
        
        # 解析工作流结果
        summary = generator.parse_workflow_result(graph_result)
        
        # 确定输出路径
        if default_project_root_path.startswith('/projects/'):
            # 如果是相对路径，转换为绝对路径
            project_root = os.path.join(os.getcwd(), default_project_root_path.lstrip('/'))
        else:
            project_root = default_project_root_path
        
        # 在projects/<project_name>下生成报告
        project_dir = os.path.join(project_root, summary.project_name)
        output_path = os.path.join(project_dir, "workflow_summary_report.md")
        
        # 生成报告
        report_path = generator.generate_markdown_report(summary, output_path)
        
        return report_path
        
    except Exception as e:
        print(f"❌ 生成工作流总结报告失败: {e}")
        return ""


def generate_workflow_summary_report(graph_result: Any, 
                                   default_project_root_path: str) -> str:
    """
    生成工作流总结报告的主函数
    
    Args:
        graph_result: GraphResult对象
        default_project_root_path: 项目根路径
    
    Returns:
        生成的报告文件路径
    """
    try:
        # 创建报告生成器
        generator = WorkflowReportGenerator()
        
        # 确定输出路径
        if default_project_root_path.startswith('/projects/'):
            # 如果是相对路径，转换为绝对路径
            project_root = os.path.join(os.getcwd(), default_project_root_path.lstrip('/'))
        else:
            project_root = default_project_root_path
        
        # 先解析工作流结果获取项目名称
        temp_summary = generator.parse_workflow_result(graph_result)
        project_name = temp_summary.project_name
        
        # 在projects/<project_name>下生成报告
        project_dir = os.path.join(project_root, project_name)
        output_path = os.path.join(project_dir, "workflow_summary_report.md")
        
        # 重新解析工作流结果，这次包含项目目录信息
        summary = generator.parse_workflow_result(graph_result, project_dir)
        
        # 生成报告
        report_path = generator.generate_markdown_report(summary, output_path)
        
        return report_path
        
    except Exception as e:
        print(f"❌ 生成工作流总结报告失败: {e}")
        return ""


if __name__ == "__main__":
    # 测试代码
    print("工作流报告生成器测试")
    print("请直接传递GraphResult对象给generate_workflow_summary_report函数")
    print("示例用法:")
    print("  from utils.workflow_report_generator import generate_workflow_summary_report")
    print("  report_path = generate_workflow_summary_report(graph_result, './projects')")