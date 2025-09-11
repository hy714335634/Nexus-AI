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
    
    def parse_workflow_result(self, graph_result: Any) -> WorkflowSummary:
        """解析GraphResult对象"""
        try:
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
            
            if usage and hasattr(usage, 'inputTokens') and hasattr(usage, 'outputTokens'):
                total_input_tokens = usage.inputTokens
                total_output_tokens = usage.outputTokens
                print(f"🔍 使用系统级别Token统计: input={total_input_tokens}, output={total_output_tokens}")
            else:
                # 如果没有系统级别统计，使用各阶段累加
                total_input_tokens = sum(stage.input_tokens for stage in stages)
                total_output_tokens = sum(stage.output_tokens for stage in stages)
                print(f"🔍 从各阶段累加Token统计: input={total_input_tokens}, output={total_output_tokens}")
                print(f"⚠️ 未找到系统级别accumulated_usage，使用各阶段估算值")
            
            # 计算其他指标
            total_tool_calls = sum(stage.tool_calls for stage in stages)
            successful_stages = sum(1 for stage in stages if stage.success)
            failed_stages = len(stages) - successful_stages
            
            # 计算总执行时间
            total_duration = sum(stage.duration or 0 for stage in stages)
            
            # 生成工具使用总结
            tool_usage_summary = self._generate_tool_usage_summary(stages)
            
            # 成本估算
            cost_estimation = self._estimate_costs(total_input_tokens, total_output_tokens)
            
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
                cost_estimation=cost_estimation
            )
            
        except Exception as e:
            print(f"❌ 解析工作流结果失败: {e}")
            # 返回默认的空总结
            return self._create_empty_summary()
    
    def _extract_project_name_from_orchestrator(self, graph_result: Any) -> str:
        """从orchestrator阶段的project_init工具调用中提取项目名称"""
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
            
            # 如果没找到project_init，尝试从字符串中提取项目名称
            if hasattr(graph_result, 'obj_str'):
                import re
                # 查找项目名称模式
                project_patterns = [
                    r"'([^']+_generator)'",
                    r"'([^']+_agent)'",
                    r"'([^']+_tool)'",
                    r"'([^']+_cloner)'"
                ]
                
                for pattern in project_patterns:
                    match = re.search(pattern, graph_result.obj_str)
                    if match:
                        project_name = match.group(1)
                        if len(project_name) > 3 and not project_name.startswith('_'):
                            return project_name
            
            return "unknown_project"
            
        except Exception as e:
            print(f"⚠️ 从orchestrator提取项目名称失败: {e}")
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
            
            # 提取execution_time
            if hasattr(node_result, 'execution_time'):
                stage_metrics.duration = node_result.execution_time / 1000.0  # 转换为秒
            
            # 提取status
            if hasattr(node_result, 'status'):
                status_str = str(node_result.status)
                stage_metrics.success = 'COMPLETED' in status_str or 'completed' in status_str
            
            # 提取该阶段自己的accumulated_usage中的token信息
            if hasattr(node_result, 'accumulated_usage'):
                usage = node_result.accumulated_usage
                if hasattr(usage, 'inputTokens'):
                    stage_metrics.input_tokens = usage.inputTokens
                if hasattr(usage, 'outputTokens'):
                    stage_metrics.output_tokens = usage.outputTokens
                print(f"🔍 阶段 {stage_name} Token统计: input={stage_metrics.input_tokens}, output={stage_metrics.output_tokens}")
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
            
            # 如果没有找到token信息，使用基于工具调用次数的合理估算
            if stage_metrics.input_tokens == 0:
                # 基于工具调用次数估算：每个工具调用约200-500 tokens
                estimated_input = max(200, stage_metrics.tool_calls * 300)
                stage_metrics.input_tokens = estimated_input
            if stage_metrics.output_tokens == 0:
                # 输出tokens通常是输入的30-50%
                estimated_output = max(100, int(stage_metrics.input_tokens * 0.4))
                stage_metrics.output_tokens = estimated_output
            
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
    
    def _format_tokens(self, tokens: int) -> str:
        """格式化Token数量，按K为单位显示"""
        if tokens >= 1000:
            return f"{tokens/1000:.1f}K"
        else:
            return str(tokens)
    
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
            }
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
            f"- **总执行时间**: {summary.total_duration:.2f} 秒",
            f"- **成功阶段数**: {summary.successful_stages}/{len(summary.stages)}",
            f"- **总输入Token**: {self._format_tokens(summary.total_input_tokens)}",
            f"- **总输出Token**: {self._format_tokens(summary.total_output_tokens)}",
            f"- **总工具调用次数**: {summary.total_tool_calls}",
            "",
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
            "| 阶段名称 | 状态 | 执行时间(秒) | 输入Token | 输出Token | 工具调用次数 |",
            "|---------|------|-------------|-----------|-----------|-------------|"
        ]
        
        # 添加各阶段详情
        for stage in summary.stages:
            status_icon = "✅" if stage.success else "❌"
            duration = f"{stage.duration:.2f}" if stage.duration else "N/A"
            
            report_lines.append(
                f"| {stage.stage_name} | {status_icon} | {duration} | {self._format_tokens(stage.input_tokens)} | {self._format_tokens(stage.output_tokens)} | {stage.tool_calls} |"
            )
            
            # 如果有错误信息，添加详细信息
            if stage.error_message:
                report_lines.append(f"| | **错误**: {stage.error_message} | | | | |")
        
        report_lines.extend([
            "",
            "## 🛠️ 工具使用统计",
            "",
            "| 工具名称 | 调用次数 |",
            "|---------|----------|"
        ])
        
        # 添加工具使用统计
        if summary.tool_usage_summary:
            for tool_name, call_count in sorted(summary.tool_usage_summary.items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"| {tool_name} | {call_count} |")
        else:
            report_lines.append("| 无工具调用记录 | 0 |")
        
        report_lines.extend([
            "",
            "## 📈 性能分析",
            "",
            f"- **平均每阶段执行时间**: {summary.total_duration / len(summary.stages):.2f} 秒",
            f"- **Token效率**: {summary.total_output_tokens / max(summary.total_input_tokens, 1):.2f} (输出/输入比)",
            f"- **工具调用频率**: {summary.total_tool_calls / max(summary.total_duration, 1):.2f} 次/秒",
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
                    "| 工具名称 | 调用次数 | 成功次数 | 失败次数 | 总耗时(秒) |",
                    "|---------|----------|----------|----------|------------|"
                ])
                
                for tool_detail in stage.tool_call_details:
                    report_lines.append(
                        f"| {tool_detail['tool_name']} | {tool_detail['call_count']} | "
                        f"{tool_detail['success_count']} | {tool_detail['error_count']} | "
                        f"{tool_detail['total_time']:.3f} |"
                    )
                report_lines.append("")
        
        report_lines.extend([
            "## 📝 总结",
            "",
            f"本次工作流执行共涉及 {len(summary.stages)} 个阶段，",
            f"成功完成 {summary.successful_stages} 个阶段，",
            f"总耗时 {summary.total_duration:.2f} 秒，",
            f"消耗Token {self._format_tokens(summary.total_input_tokens + summary.total_output_tokens)} 个，",
            f"调用工具 {summary.total_tool_calls} 次。",
            "",
            "---",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(report_lines)


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


if __name__ == "__main__":
    # 测试代码
    print("工作流报告生成器测试")
    print("请直接传递GraphResult对象给generate_workflow_summary_report函数")
    print("示例用法:")
    print("  from utils.workflow_report_generator import generate_workflow_summary_report")
    print("  report_path = generate_workflow_summary_report(graph_result, './projects')")