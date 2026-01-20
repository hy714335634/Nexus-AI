#!/usr/bin/env python3
"""
项目信息采集模块

在工作流报告生成后，将项目的完整信息同步到 DynamoDB，包括：
- 项目基本信息 (config.yaml, status.yaml)
- 工作流报告统计数据 (workflow_summary_report.md)
- Token 计数、成本估算
- 各阶段执行详情
- 工具使用统计
"""

import os
import re
import json
import yaml
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorkflowMetrics:
    """工作流指标数据"""
    total_duration_seconds: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    total_tools: int = 0
    successful_stages: int = 0
    failed_stages: int = 0
    cost_input_usd: float = 0.0
    cost_output_usd: float = 0.0
    cost_total_usd: float = 0.0
    pricing_model: str = ""


@dataclass
class StageMetricsData:
    """阶段指标数据"""
    stage_name: str
    status: str = "completed"
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    efficiency_rating: str = ""
    error_message: Optional[str] = None


@dataclass
class ProjectConfigSummary:
    """项目配置摘要"""
    agent_scripts_count: int = 0
    prompt_files_count: int = 0
    generated_tool_files_count: int = 0
    all_scripts_valid: bool = True
    all_tools_valid: bool = True
    all_prompts_valid: bool = True


class ProjectInfoCollector:
    """项目信息采集器"""
    
    def __init__(self, project_root_path: str = "./projects"):
        """
        初始化采集器
        
        Args:
            project_root_path: 项目根目录路径
        """
        self.project_root_path = project_root_path
        self._db_client = None
    
    @property
    def db_client(self):
        """懒加载 DynamoDB 客户端"""
        if self._db_client is None:
            try:
                from api.v2.database.dynamodb import db_client
                self._db_client = db_client
            except ImportError as e:
                logger.warning(f"无法导入 DynamoDB 客户端: {e}")
                self._db_client = None
        return self._db_client
    
    def collect_and_sync(
        self,
        project_name: str,
        project_id: Optional[str] = None,
        workflow_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        采集项目信息并同步到 DynamoDB
        
        Args:
            project_name: 项目名称（本地目录名）
            project_id: 数据库中的项目ID（可选，如果提供则更新该记录）
            workflow_metrics: 工作流指标（可选，如果提供则直接使用）
        
        Returns:
            采集和同步结果
        """
        result = {
            "success": False,
            "project_name": project_name,
            "project_id": project_id,
            "collected_data": {},
            "sync_status": {},
            "errors": []
        }
        
        try:
            project_dir = os.path.join(self.project_root_path, project_name)
            
            if not os.path.exists(project_dir):
                result["errors"].append(f"项目目录不存在: {project_dir}")
                return result
            
            # 1. 采集项目配置信息
            config_data = self._collect_config(project_dir)
            result["collected_data"]["config"] = config_data
            
            # 2. 采集项目状态信息
            status_data = self._collect_status(project_dir)
            result["collected_data"]["status"] = status_data
            
            # 3. 采集项目配置JSON
            project_config = self._collect_project_config(project_dir)
            result["collected_data"]["project_config"] = project_config
            
            # 4. 采集或使用工作流报告指标
            if workflow_metrics:
                metrics_data = workflow_metrics
            else:
                metrics_data = self._parse_workflow_report(project_dir)
            result["collected_data"]["workflow_metrics"] = metrics_data
            
            # 5. 同步到 DynamoDB
            if self.db_client:
                sync_result = self._sync_to_dynamodb(
                    project_id=project_id,
                    project_name=project_name,
                    config_data=config_data,
                    status_data=status_data,
                    project_config=project_config,
                    metrics_data=metrics_data
                )
                result["sync_status"] = sync_result
                result["success"] = sync_result.get("success", False)
            else:
                result["sync_status"] = {"success": False, "message": "DynamoDB 客户端不可用"}
                logger.warning("DynamoDB 客户端不可用，跳过同步")
            
            if not result["errors"]:
                result["success"] = True
                
        except Exception as e:
            logger.error(f"采集项目信息失败: {e}")
            result["errors"].append(str(e))
        
        return result
    
    def _collect_config(self, project_dir: str) -> Dict[str, Any]:
        """采集 config.yaml"""
        config_path = os.path.join(project_dir, "config.yaml")
        if not os.path.exists(config_path):
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get("project", {}) if config else {}
        except Exception as e:
            logger.warning(f"读取 config.yaml 失败: {e}")
            return {}
    
    def _collect_status(self, project_dir: str) -> Dict[str, Any]:
        """采集 status.yaml"""
        status_path = os.path.join(project_dir, "status.yaml")
        if not os.path.exists(status_path):
            return {}
        
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                status = yaml.safe_load(f)
            return status if status else {}
        except Exception as e:
            logger.warning(f"读取 status.yaml 失败: {e}")
            return {}
    
    def _collect_project_config(self, project_dir: str) -> Dict[str, Any]:
        """采集 project_config.json"""
        config_path = os.path.join(project_dir, "project_config.json")
        if not os.path.exists(config_path):
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config if config else {}
        except Exception as e:
            logger.warning(f"读取 project_config.json 失败: {e}")
            return {}
    
    def _parse_workflow_report(self, project_dir: str) -> Dict[str, Any]:
        """解析 workflow_summary_report.md 提取指标"""
        report_path = os.path.join(project_dir, "workflow_summary_report.md")
        if not os.path.exists(report_path):
            return {}
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metrics = {
                "total_duration_seconds": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tool_calls": 0,
                "total_tools": 0,
                "successful_stages": 0,
                "failed_stages": 0,
                "cost_input_usd": 0.0,
                "cost_output_usd": 0.0,
                "cost_total_usd": 0.0,
                "pricing_model": "",
                "stages": []
            }
            
            # 解析总执行时间
            duration_match = re.search(r'\*\*总执行时间\*\*:\s*([\d.]+)\s*秒', content)
            if duration_match:
                metrics["total_duration_seconds"] = float(duration_match.group(1))
            
            # 解析成功阶段数
            stages_match = re.search(r'\*\*成功阶段数\*\*:\s*(\d+)/(\d+)', content)
            if stages_match:
                metrics["successful_stages"] = int(stages_match.group(1))
                total_stages = int(stages_match.group(2))
                metrics["failed_stages"] = total_stages - metrics["successful_stages"]
            
            # 解析总输入Token
            input_tokens_match = re.search(r'\*\*总输入Token\*\*:\s*([\d.]+)K?', content)
            if input_tokens_match:
                value = float(input_tokens_match.group(1))
                if 'K' in content[input_tokens_match.start():input_tokens_match.end() + 5]:
                    value *= 1000
                metrics["total_input_tokens"] = int(value)
            
            # 解析总输出Token
            output_tokens_match = re.search(r'\*\*总输出Token\*\*:\s*([\d.]+)K?', content)
            if output_tokens_match:
                value = float(output_tokens_match.group(1))
                if 'K' in content[output_tokens_match.start():output_tokens_match.end() + 5]:
                    value *= 1000
                metrics["total_output_tokens"] = int(value)
            
            # 解析总工具调用次数
            tool_calls_match = re.search(r'\*\*总工具调用次数\*\*:\s*(\d+)', content)
            if tool_calls_match:
                metrics["total_tool_calls"] = int(tool_calls_match.group(1))
            
            # 解析项目总工具数量
            total_tools_match = re.search(r'\*\*项目总工具数量\*\*:\s*(\d+)', content)
            if total_tools_match:
                metrics["total_tools"] = int(total_tools_match.group(1))
            
            # 解析成本信息
            input_cost_match = re.search(r'\*\*输入成本\*\*:\s*\$([\d.]+)', content)
            if input_cost_match:
                metrics["cost_input_usd"] = float(input_cost_match.group(1))
            
            output_cost_match = re.search(r'\*\*输出成本\*\*:\s*\$([\d.]+)', content)
            if output_cost_match:
                metrics["cost_output_usd"] = float(output_cost_match.group(1))
            
            total_cost_match = re.search(r'\*\*总成本\*\*:\s*\$([\d.]+)', content)
            if total_cost_match:
                metrics["cost_total_usd"] = float(total_cost_match.group(1))
            
            pricing_model_match = re.search(r'\*\*定价模型\*\*:\s*(.+)', content)
            if pricing_model_match:
                metrics["pricing_model"] = pricing_model_match.group(1).strip()
            
            # 解析阶段执行详情表格
            stages = self._parse_stages_table(content)
            metrics["stages"] = stages
            
            return metrics
            
        except Exception as e:
            logger.warning(f"解析 workflow_summary_report.md 失败: {e}")
            return {}
    
    def _parse_stages_table(self, content: str) -> List[Dict[str, Any]]:
        """解析阶段执行详情表格"""
        stages = []
        
        # 查找阶段执行详情表格
        table_pattern = r'\| 阶段名称 \| 状态 \| 执行时间\(秒\) \| 输入Token \| 输出Token \| 工具调用次数 \| 效率评分 \|'
        table_match = re.search(table_pattern, content)
        
        if not table_match:
            return stages
        
        # 从表格开始位置向后查找数据行
        table_start = table_match.end()
        lines = content[table_start:].split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not line.startswith('|'):
                continue
            if '---' in line:
                continue
            if '阶段名称' in line:
                continue
            
            # 解析表格行
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            if len(cells) >= 7:
                stage_name = cells[0]
                status = "completed" if "✅" in cells[1] else "failed"
                
                # 解析执行时间
                duration_str = cells[2]
                try:
                    duration = float(duration_str) if duration_str != "N/A" else 0.0
                except ValueError:
                    duration = 0.0
                
                # 解析Token数量（处理K后缀）
                input_tokens = self._parse_token_value(cells[3])
                output_tokens = self._parse_token_value(cells[4])
                
                # 解析工具调用次数
                try:
                    tool_calls = int(cells[5])
                except ValueError:
                    tool_calls = 0
                
                efficiency = cells[6] if len(cells) > 6 else ""
                
                stages.append({
                    "stage_name": stage_name,
                    "status": status,
                    "duration_seconds": duration,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "tool_calls": tool_calls,
                    "efficiency_rating": efficiency
                })
        
        return stages
    
    def _parse_token_value(self, value_str: str) -> int:
        """解析Token值（处理K后缀）"""
        try:
            value_str = value_str.strip()
            if value_str == "N/A" or not value_str:
                return 0
            
            if 'K' in value_str.upper():
                value_str = value_str.upper().replace('K', '')
                return int(float(value_str) * 1000)
            else:
                return int(float(value_str))
        except ValueError:
            return 0
    
    def _sync_to_dynamodb(
        self,
        project_id: Optional[str],
        project_name: str,
        config_data: Dict[str, Any],
        status_data: Dict[str, Any],
        project_config: Dict[str, Any],
        metrics_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """同步数据到 DynamoDB"""
        result = {
            "success": False,
            "project_updated": False,
            "stages_updated": 0,
            "errors": []
        }
        
        if not self.db_client:
            result["errors"].append("DynamoDB 客户端不可用")
            return result
        
        try:
            # 1. 更新项目记录
            if project_id:
                project_updates = self._build_project_updates(
                    config_data, status_data, project_config, metrics_data
                )
                
                if project_updates:
                    self.db_client.update_project(project_id, project_updates)
                    result["project_updated"] = True
                    logger.info(f"已更新项目 {project_id} 的指标数据")
            
            # 2. 更新阶段记录
            if project_id and metrics_data.get("stages"):
                stages_updated = self._sync_stages(project_id, metrics_data["stages"])
                result["stages_updated"] = stages_updated
            
            result["success"] = True
            
        except Exception as e:
            logger.error(f"同步到 DynamoDB 失败: {e}")
            result["errors"].append(str(e))
        
        return result
    
    def _build_project_updates(
        self,
        config_data: Dict[str, Any],
        status_data: Dict[str, Any],
        project_config: Dict[str, Any],
        metrics_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建项目更新数据"""
        updates = {}
        
        # 从 config_data 提取信息
        if config_data:
            if config_data.get("description"):
                updates["description"] = config_data["description"]
            if config_data.get("version"):
                updates["version"] = config_data["version"]
        
        # 从 project_config 提取摘要信息
        if project_config:
            summary = project_config.get("summary", {})
            updates["config_summary"] = {
                "agent_scripts_count": summary.get("agent_scripts_count", 0),
                "prompt_files_count": summary.get("prompt_files_count", 0),
                "generated_tool_files_count": summary.get("generated_tool_files_count", 0),
                "all_scripts_valid": summary.get("all_scripts_valid", True),
                "all_tools_valid": summary.get("all_tools_valid", True),
                "all_prompts_valid": summary.get("all_prompts_valid", True)
            }
            updates["total_tools"] = project_config.get("total_tools", 0)
        
        # 从 metrics_data 提取工作流指标
        if metrics_data:
            updates["metrics"] = {
                "total_duration_seconds": metrics_data.get("total_duration_seconds", 0),
                "total_input_tokens": metrics_data.get("total_input_tokens", 0),
                "total_output_tokens": metrics_data.get("total_output_tokens", 0),
                "total_tool_calls": metrics_data.get("total_tool_calls", 0),
                "successful_stages": metrics_data.get("successful_stages", 0),
                "failed_stages": metrics_data.get("failed_stages", 0),
                "cost_estimation": {
                    "input_cost_usd": metrics_data.get("cost_input_usd", 0),
                    "output_cost_usd": metrics_data.get("cost_output_usd", 0),
                    "total_cost_usd": metrics_data.get("cost_total_usd", 0),
                    "pricing_model": metrics_data.get("pricing_model", "")
                }
            }
        
        return updates
    
    def _sync_stages(self, project_id: str, stages: List[Dict[str, Any]]) -> int:
        """同步阶段数据到 DynamoDB"""
        updated_count = 0
        
        # 阶段名称映射（从报告中的名称到数据库中的名称）
        stage_name_mapping = {
            "orchestrator": "orchestrator",
            "requirements_analyzer": "requirements_analysis",
            "system_architect": "system_architecture",
            "agent_designer": "agent_design",
            "tool_developer": "tools_developer",
            "prompt_engineer": "prompt_engineer",
            "agent_code_developer": "agent_code_developer",
            "agent_developer_manager": "agent_developer_manager",
            "agent_deployer": "agent_deployer"
        }
        
        for stage_data in stages:
            try:
                stage_name = stage_data.get("stage_name", "")
                db_stage_name = stage_name_mapping.get(stage_name, stage_name)
                
                updates = {
                    "duration_seconds": stage_data.get("duration_seconds", 0),
                    "input_tokens": stage_data.get("input_tokens", 0),
                    "output_tokens": stage_data.get("output_tokens", 0),
                    "tool_calls": stage_data.get("tool_calls", 0),
                    "efficiency_rating": stage_data.get("efficiency_rating", "")
                }
                
                # 检查阶段是否存在
                existing_stage = self.db_client.get_stage(project_id, db_stage_name)
                
                if existing_stage:
                    self.db_client.update_stage(project_id, db_stage_name, updates)
                    updated_count += 1
                else:
                    logger.debug(f"阶段 {db_stage_name} 不存在，跳过更新")
                    
            except Exception as e:
                logger.warning(f"更新阶段 {stage_data.get('stage_name')} 失败: {e}")
        
        return updated_count


def collect_project_info_after_workflow(
    project_name: str,
    project_id: Optional[str] = None,
    project_root_path: str = "./projects",
    workflow_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    工作流完成后采集项目信息的便捷函数
    
    Args:
        project_name: 项目名称（本地目录名）
        project_id: 数据库中的项目ID
        project_root_path: 项目根目录路径
        workflow_metrics: 工作流指标（可选）
    
    Returns:
        采集和同步结果
    """
    collector = ProjectInfoCollector(project_root_path)
    return collector.collect_and_sync(
        project_name=project_name,
        project_id=project_id,
        workflow_metrics=workflow_metrics
    )


def collect_from_workflow_summary(
    workflow_summary: Any,
    project_id: Optional[str] = None,
    project_root_path: str = "./projects"
) -> Dict[str, Any]:
    """
    从 WorkflowSummary 对象采集信息并同步
    
    Args:
        workflow_summary: WorkflowSummary 对象
        project_id: 数据库中的项目ID
        project_root_path: 项目根目录路径
    
    Returns:
        采集和同步结果
    """
    try:
        # 从 WorkflowSummary 提取指标
        metrics = {
            "total_duration_seconds": getattr(workflow_summary, 'total_duration', 0),
            "total_input_tokens": getattr(workflow_summary, 'total_input_tokens', 0),
            "total_output_tokens": getattr(workflow_summary, 'total_output_tokens', 0),
            "total_tool_calls": getattr(workflow_summary, 'total_tool_calls', 0),
            "total_tools": getattr(workflow_summary, 'total_tools', 0),
            "successful_stages": getattr(workflow_summary, 'successful_stages', 0),
            "failed_stages": getattr(workflow_summary, 'failed_stages', 0),
            "stages": []
        }
        
        # 提取成本估算
        cost_estimation = getattr(workflow_summary, 'cost_estimation', {})
        if cost_estimation:
            metrics["cost_input_usd"] = cost_estimation.get('input_cost_usd', 0)
            metrics["cost_output_usd"] = cost_estimation.get('output_cost_usd', 0)
            metrics["cost_total_usd"] = cost_estimation.get('total_cost_usd', 0)
            metrics["pricing_model"] = cost_estimation.get('pricing_model', '')
        
        # 提取阶段信息
        stages = getattr(workflow_summary, 'stages', [])
        for stage in stages:
            metrics["stages"].append({
                "stage_name": getattr(stage, 'stage_name', ''),
                "status": "completed" if getattr(stage, 'success', True) else "failed",
                "duration_seconds": getattr(stage, 'duration', 0) or 0,
                "input_tokens": getattr(stage, 'input_tokens', 0),
                "output_tokens": getattr(stage, 'output_tokens', 0),
                "tool_calls": getattr(stage, 'tool_calls', 0),
                "error_message": getattr(stage, 'error_message', None)
            })
        
        project_name = getattr(workflow_summary, 'project_name', 'unknown_project')
        
        return collect_project_info_after_workflow(
            project_name=project_name,
            project_id=project_id,
            project_root_path=project_root_path,
            workflow_metrics=metrics
        )
        
    except Exception as e:
        logger.error(f"从 WorkflowSummary 采集信息失败: {e}")
        return {
            "success": False,
            "errors": [str(e)]
        }


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description='项目信息采集模块测试')
    parser.add_argument('-p', '--project', type=str, required=True, help='项目名称')
    parser.add_argument('-i', '--project-id', type=str, help='数据库项目ID')
    parser.add_argument('--root', type=str, default='./projects', help='项目根目录')
    args = parser.parse_args()
    
    print(f"开始采集项目信息: {args.project}")
    
    result = collect_project_info_after_workflow(
        project_name=args.project,
        project_id=args.project_id,
        project_root_path=args.root
    )
    
    print(f"\n采集结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
