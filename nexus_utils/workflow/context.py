"""
工作流上下文管理

提供 WorkflowContext 类的 DynamoDB 集成功能，包括上下文加载、保存和格式化。

Requirements:
    - 1.2: 支持从任意阶段开始执行
    - 9.1: Stage_Context 包含基础工作流规则
    - 9.2: Stage_Context 包含所有已完成阶段的输出
    - 9.3: Stage_Context 包含原始用户需求
    - 9.4: Stage_Context 包含意图分析结果
    - 9.5: Stage_Context 包含本地文档内容
    - 9.6: 上下文大小限制处理
    - 9.7: 旧阶段输出摘要功能
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import (
    WorkflowContext,
    StageOutput,
    StageMetrics,
    FileMetadata,
    StageStatus,
    ControlStatus,
    IntentRecognitionResult,
    AggregatedMetrics,
)

logger = logging.getLogger(__name__)

# 上下文大小限制（默认 100K tokens，约 400KB 文本）
DEFAULT_MAX_CONTEXT_TOKENS = 100000
# 每个字符约 0.25 tokens（中英文混合估算）
CHARS_PER_TOKEN = 4


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量
    
    使用简单的字符数估算，中英文混合约 4 字符 = 1 token
    
    参数:
        text: 要估算的文本
        
    返回:
        int: 估算的 token 数量
    """
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """
    将文本截断到指定的 token 数量
    
    参数:
        text: 要截断的文本
        max_tokens: 最大 token 数量
        
    返回:
        str: 截断后的文本
    """
    if not text:
        return ""
    
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    
    # 截断并添加省略标记
    truncated = text[:max_chars - 50]
    return truncated + "\n\n... [内容已截断] ..."


def summarize_stage_output(content: str, max_tokens: int = 2000) -> str:
    """
    生成阶段输出的摘要
    
    对于较长的阶段输出，提取关键信息生成摘要。
    
    参数:
        content: 原始内容
        max_tokens: 摘要的最大 token 数量
        
    返回:
        str: 摘要内容
        
    Validates: Requirement 9.7 - 旧阶段输出摘要功能
    """
    if not content:
        return ""
    
    current_tokens = estimate_tokens(content)
    if current_tokens <= max_tokens:
        return content
    
    # 提取关键部分
    lines = content.split('\n')
    summary_parts = []
    
    # 1. 提取标题和章节头
    for line in lines:
        if line.startswith('#') or line.startswith('##'):
            summary_parts.append(line)
    
    # 2. 提取关键信息（JSON 块、代码块的开头）
    in_code_block = False
    code_block_lines = 0
    for line in lines:
        if line.startswith('```'):
            in_code_block = not in_code_block
            if in_code_block:
                summary_parts.append(line)
                code_block_lines = 0
            else:
                summary_parts.append('```')
        elif in_code_block and code_block_lines < 10:
            summary_parts.append(line)
            code_block_lines += 1
    
    # 3. 如果摘要仍然太长，进一步截断
    summary = '\n'.join(summary_parts)
    if estimate_tokens(summary) > max_tokens:
        summary = truncate_to_tokens(summary, max_tokens)
    
    return f"[摘要]\n{summary}"


class WorkflowContextManager:
    """
    工作流上下文管理器
    
    负责从 DynamoDB 加载和保存工作流上下文，以及格式化阶段执行上下文。
    
    Validates:
        - Requirement 1.2: 支持从任意阶段开始执行
        - Requirement 9.1: 包含基础工作流规则
        - Requirement 9.2: 包含所有已完成阶段的输出
        - Requirement 9.3: 包含原始用户需求
        - Requirement 9.4: 包含意图分析结果
        - Requirement 9.5: 包含本地文档内容
    """
    
    def __init__(self, db_client=None):
        """
        初始化上下文管理器
        
        参数:
            db_client: DynamoDB 客户端实例，如果为 None 则延迟加载
        """
        self._db_client = db_client
        self._rules_cache: Optional[str] = None
    
    @property
    def db(self):
        """延迟加载 DynamoDB 客户端"""
        if self._db_client is None:
            from api.v2.database import db_client
            self._db_client = db_client
        return self._db_client
    
    def load_from_db(self, project_id: str) -> WorkflowContext:
        """
        从 DynamoDB 加载工作流上下文
        
        参数:
            project_id: 项目ID
            
        返回:
            WorkflowContext: 加载的上下文实例
            
        Validates:
            - Requirement 1.4: 自动加载前置阶段输出
            - Requirement 4.2: 从 DynamoDB 加载项目上下文
            - Requirement 9.2: 包含所有已完成阶段的输出
        """
        # 加载项目记录
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 加载所有阶段记录
        stages = self.db.list_stages(project_id)
        
        # 构建阶段输出字典
        stage_outputs: Dict[str, StageOutput] = {}
        for stage_data in stages:
            stage_name = stage_data.get('stage_name', '')
            
            # 解析指标
            metrics_data = stage_data.get('metrics', {})
            metrics = StageMetrics.from_dict(metrics_data) if metrics_data else StageMetrics()
            
            # 解析生成的文件
            files_data = stage_data.get('generated_files', [])
            generated_files = [FileMetadata.from_dict(f) for f in files_data]
            
            # 解析状态
            status_str = stage_data.get('status', 'pending')
            try:
                status = StageStatus(status_str)
            except ValueError:
                status = StageStatus.PENDING
            
            # 解析完成时间
            completed_at = None
            if stage_data.get('completed_at'):
                try:
                    completed_at = datetime.fromisoformat(
                        stage_data['completed_at'].replace('Z', '+00:00')
                    )
                except:
                    pass
            
            # 创建阶段输出
            stage_output = StageOutput(
                stage_name=stage_name,
                content=stage_data.get('agent_output_content', ''),
                metrics=metrics,
                generated_files=generated_files,
                document_content=stage_data.get('design_document', {}).get('content', ''),
                document_format=stage_data.get('design_document', {}).get('format', 'markdown'),
                completed_at=completed_at,
                status=status,
                error_message=stage_data.get('error_message'),
                s3_content_ref=stage_data.get('agent_output_s3_ref'),
            )
            
            stage_outputs[stage_name] = stage_output
        
        # 解析意图识别结果（从 orchestrator 阶段输出中提取）
        intent_result = None
        orchestrator_output = stage_outputs.get('orchestrator')
        if orchestrator_output and orchestrator_output.is_completed:
            intent_result = self._parse_intent_result(orchestrator_output.content)
        
        # 解析控制状态
        control_status_str = project.get('control_status', 'running')
        try:
            control_status = ControlStatus(control_status_str)
        except ValueError:
            control_status = ControlStatus.RUNNING
        
        # 解析聚合指标
        aggregated_data = project.get('aggregated_metrics', {})
        aggregated_metrics = AggregatedMetrics.from_dict(aggregated_data)
        
        # 解析时间字段
        created_at = None
        if project.get('created_at'):
            try:
                created_at = datetime.fromisoformat(
                    project['created_at'].replace('Z', '+00:00')
                )
            except:
                pass
        
        updated_at = None
        if project.get('updated_at'):
            try:
                updated_at = datetime.fromisoformat(
                    project['updated_at'].replace('Z', '+00:00')
                )
            except:
                pass
        
        pause_requested_at = None
        if project.get('pause_requested_at'):
            try:
                pause_requested_at = datetime.fromisoformat(
                    project['pause_requested_at'].replace('Z', '+00:00')
                )
            except:
                pass
        
        stop_requested_at = None
        if project.get('stop_requested_at'):
            try:
                stop_requested_at = datetime.fromisoformat(
                    project['stop_requested_at'].replace('Z', '+00:00')
                )
            except:
                pass
        
        # 加载工作流规则
        rules = self._load_workflow_rules()
        
        # 解析项目状态
        status_str = project.get('status', 'pending')
        try:
            status = StageStatus(status_str)
        except ValueError:
            status = StageStatus.PENDING
        
        # 获取工作流类型
        workflow_type = project.get('workflow_type', 'agent_build')
        
        # 创建上下文
        context = WorkflowContext(
            project_id=project_id,
            project_name=project.get('project_name', ''),
            requirement=project.get('requirement', ''),
            intent_result=intent_result,
            stage_outputs=stage_outputs,
            rules=rules,
            current_stage=project.get('current_stage', ''),
            status=status,
            aggregated_metrics=aggregated_metrics,
            created_at=created_at,
            updated_at=updated_at,
            control_status=control_status,
            pause_requested_at=pause_requested_at,
            stop_requested_at=stop_requested_at,
            resume_from_stage=project.get('resume_from_stage'),
            workflow_type=workflow_type,
        )
        
        return context
    
    def _parse_intent_result(self, orchestrator_content: str) -> Optional[IntentRecognitionResult]:
        """
        从编排器输出中解析意图识别结果
        
        参数:
            orchestrator_content: 编排器阶段的输出内容
            
        返回:
            IntentRecognitionResult: 解析的意图识别结果
        """
        if not orchestrator_content:
            return None
        
        # 简单解析，实际实现可能需要更复杂的解析逻辑
        result = IntentRecognitionResult(raw_analysis=orchestrator_content)
        
        # 尝试从内容中提取 agent 名称
        import re
        
        # 查找 agent 名称模式
        name_match = re.search(r'(?:agent[_\s]?name|名称)[:\s]*["\']?([a-zA-Z0-9_]+)["\']?', 
                               orchestrator_content, re.IGNORECASE)
        if name_match:
            result.agent_name = name_match.group(1)
        
        # 查找工作流类型
        if 'multi' in orchestrator_content.lower() and 'agent' in orchestrator_content.lower():
            result.workflow_type = 'multi_agent'
        else:
            result.workflow_type = 'single_agent'
        
        return result
    
    def _load_workflow_rules(self) -> str:
        """
        加载工作流规则
        
        返回:
            str: 工作流规则内容
            
        Validates: Requirement 9.1 - Stage_Context 包含基础工作流规则
        """
        if self._rules_cache is not None:
            return self._rules_cache
        
        project_root = _get_project_root()
        rules_path = project_root / "config" / "nexus_ai_base_rule.yaml"
        
        if rules_path.exists():
            try:
                with open(rules_path, 'r', encoding='utf-8') as f:
                    self._rules_cache = f.read()
                return self._rules_cache
            except Exception as e:
                logger.warning(f"Failed to load workflow rules: {e}")
        
        self._rules_cache = ""
        return self._rules_cache
    
    def save_to_db(self, context: WorkflowContext) -> None:
        """
        保存工作流上下文到 DynamoDB
        
        参数:
            context: 要保存的上下文
        """
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # 在保存前从数据库刷新控制状态，避免覆盖用户的暂停/停止操作
        try:
            project = self.db.get_project(context.project_id)
            if project:
                db_control_status = project.get('control_status', 'running')
                if db_control_status in ['paused', 'stopped']:
                    # 数据库中的控制状态优先
                    try:
                        context.control_status = ControlStatus(db_control_status)
                    except ValueError:
                        pass
        except Exception as e:
            logger.warning(f"Failed to refresh control status before save: {e}")
        
        # 将 StageStatus 映射到 ProjectStatus
        # StageStatus.RUNNING -> ProjectStatus.BUILDING
        # StageStatus.COMPLETED -> ProjectStatus.COMPLETED
        # StageStatus.FAILED -> ProjectStatus.FAILED
        # StageStatus.PAUSED -> ProjectStatus.PAUSED
        # StageStatus.PENDING -> ProjectStatus.BUILDING (如果有当前阶段)
        stage_to_project_status = {
            StageStatus.RUNNING: 'building',
            StageStatus.COMPLETED: 'completed',
            StageStatus.FAILED: 'failed',
            StageStatus.PAUSED: 'paused',
            StageStatus.PENDING: 'building' if context.current_stage else 'pending',
        }
        project_status = stage_to_project_status.get(context.status, 'building')
        
        # 如果控制状态是 paused 或 stopped，使用控制状态对应的项目状态
        # 避免覆盖用户的暂停/停止操作
        if context.control_status == ControlStatus.PAUSED:
            project_status = 'paused'
        elif context.control_status == ControlStatus.STOPPED:
            project_status = 'cancelled'
        
        # 更新项目记录
        project_updates = {
            'project_name': context.project_name,
            'current_stage': context.current_stage,
            'status': project_status,
            'control_status': context.control_status.value,
            'aggregated_metrics': context.aggregated_metrics.to_dict(),
            'updated_at': now,
        }
        
        if context.pause_requested_at:
            project_updates['pause_requested_at'] = context.pause_requested_at.isoformat()
        if context.stop_requested_at:
            project_updates['stop_requested_at'] = context.stop_requested_at.isoformat()
        if context.resume_from_stage:
            project_updates['resume_from_stage'] = context.resume_from_stage
        
        self.db.update_project(context.project_id, project_updates)
        
        # 如果当前阶段正在运行，使用 stage_service 更新状态
        # 这确保阶段名称被正确规范化
        if context.current_stage and context.status == StageStatus.RUNNING:
            current_stage = context.current_stage
            if current_stage not in context.stage_outputs:
                # 当前阶段还没有输出记录，说明正在运行中
                try:
                    from api.v2.services.stage_service import stage_service_v2
                    stage_service_v2.mark_stage_running(context.project_id, current_stage)
                    logger.info(f"Stage {current_stage} marked as running via stage_service for project {context.project_id}")
                except Exception as e:
                    # 回退到直接更新数据库
                    logger.warning(f"Could not use stage_service: {e}, falling back to direct update")
                    self.db.update_stage(context.project_id, current_stage, {
                        'status': 'running',
                        'started_at': now,
                    })
        
        # 更新已有输出的阶段记录
        for stage_name, output in context.stage_outputs.items():
            stage_updates = {
                'status': output.status.value,
                'agent_output_content': output.content if not output.s3_content_ref else '',
                'agent_output_s3_ref': output.s3_content_ref,
                'metrics': output.metrics.to_dict(),
                'generated_files': [f.to_dict() for f in output.generated_files],
                'error_message': output.error_message,
            }
            
            if output.document_content:
                stage_updates['design_document'] = {
                    'content': output.document_content,
                    'format': output.document_format,
                }
            
            if output.completed_at:
                stage_updates['completed_at'] = output.completed_at.isoformat()
            
            self.db.update_stage(context.project_id, stage_name, stage_updates)
    
    def get_stage_context(
        self, 
        context: WorkflowContext, 
        stage_name: str,
        include_rules: bool = True,
        include_local_docs: bool = True,
        max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    ) -> str:
        """
        获取指定阶段的执行上下文
        
        格式与旧版本 agent_build_workflow.py 保持一致：
        base_context + "\n===\n{Agent Name} Agent: " + content + "\n===\n"
        
        参数:
            context: 工作流上下文
            stage_name: 目标阶段名称
            include_rules: 是否包含工作流规则
            include_local_docs: 是否包含本地文档
            max_tokens: 最大 token 数量限制
            
        返回:
            str: 格式化的上下文字符串
            
        Validates:
            - Requirement 9.1: 包含基础工作流规则
            - Requirement 9.2: 包含所有已完成阶段的输出
            - Requirement 9.3: 包含原始用户需求
            - Requirement 9.4: 包含意图分析结果
            - Requirement 9.5: 包含本地文档内容
            - Requirement 9.6: 上下文大小限制处理
            - Requirement 9.7: 旧阶段输出摘要功能
        """
        import json
        
        # 从统一配置模块获取阶段名称到 Agent 显示名称的映射
        from api.v2.core.stage_config import STAGES
        STAGE_TO_AGENT_NAME = {
            name: config.agent_display_name for name, config in STAGES.items()
        }
        
        # 构建 base_context（与旧版本格式一致）
        base_parts = []
        
        # 1. 添加工作流规则（Requirement 9.1）
        if include_rules and context.rules:
            base_parts.append(f"# Build Workflow Kickoff\n## 必须严格遵守的规则:\n{context.rules}\n")
        
        # 2. 添加项目名称约束（如果有）
        if context.project_name:
            base_parts.append(
                f"## 项目名称约束\n"
                f"**重要**: 项目名称为 `{context.project_name}`，在调用 project_init 工具时必须使用此名称作为 project_name 参数。\n"
                f"不要自行生成或修改项目名称。\n\n"
            )
        
        # 3. 添加意图分析结果（Requirement 9.4）
        if context.intent_result:
            intent_dict = context.intent_result.to_dict()
            base_parts.append(f"## 意图识别结果\n{json.dumps(intent_dict, ensure_ascii=False, indent=2)}\n")
        
        # 4. 添加原始用户需求（Requirement 9.3）
        base_parts.append(f"## 用户原始输入\n{context.requirement}\n")
        base_parts.append("请按顺序完成构建流程，遵守以上规则。")
        
        base_context = "\n".join(base_parts)
        
        # 5. 添加已完成阶段的输出（Requirement 9.2）
        # 格式与旧版本一致：base_context + "\n===\n{Agent Name} Agent: " + content + "\n===\n"
        completed_stages = context.get_completed_stages()
        prerequisite_stages = context.get_prerequisite_stages(stage_name)
        
        # 只包含当前阶段的前置阶段输出
        relevant_stages = [s for s in completed_stages if s in prerequisite_stages]
        
        current_context = base_context
        
        # 计算每个阶段可用的 token 预算
        remaining_tokens = max_tokens - estimate_tokens(base_context)
        tokens_per_stage = remaining_tokens // len(relevant_stages) if relevant_stages else remaining_tokens
        
        for completed_stage in relevant_stages:
            output = context.get_stage_output(completed_stage)
            if output and output.content:
                content = output.content
                content_tokens = estimate_tokens(content)
                
                # 如果内容超过预算，生成摘要（Requirement 9.7）
                if content_tokens > tokens_per_stage:
                    content = summarize_stage_output(content, tokens_per_stage)
                    logger.info(
                        f"Stage {completed_stage} output summarized: "
                        f"{content_tokens} -> {estimate_tokens(content)} tokens"
                    )
                
                # 使用与旧版本一致的格式
                agent_name = STAGE_TO_AGENT_NAME.get(completed_stage, completed_stage)
                current_context = current_context + f"\n===\n{agent_name} Agent: " + content + "\n===\n"
        
        # 6. 添加本地文档内容（Requirement 9.5）
        if include_local_docs:
            remaining_tokens = max_tokens - estimate_tokens(current_context)
            if remaining_tokens > 1000:  # 至少需要 1000 tokens 才添加文档
                local_docs = self._load_local_documents(context.project_id, context.project_name)
                if local_docs:
                    doc_parts = ["\n## 本地文档\n"]
                    doc_budget = remaining_tokens // len(local_docs) if local_docs else 0
                    
                    for doc_name, doc_content in local_docs.items():
                        doc_tokens = estimate_tokens(doc_content)
                        if doc_tokens > doc_budget:
                            doc_content = truncate_to_tokens(doc_content, doc_budget)
                        
                        doc_parts.append(f"### {doc_name}\n")
                        doc_parts.append(doc_content)
                        doc_parts.append("\n")
                    
                    current_context = current_context + "\n".join(doc_parts)
        
        # 最终检查：如果仍然超过限制，进行截断（Requirement 9.6）
        final_tokens = estimate_tokens(current_context)
        if final_tokens > max_tokens:
            logger.warning(
                f"Context exceeded limit: {final_tokens} > {max_tokens} tokens, truncating"
            )
            current_context = truncate_to_tokens(current_context, max_tokens)
        
        return current_context
    
    def _load_local_documents(
        self, 
        project_id: str, 
        project_name: str
    ) -> Dict[str, str]:
        """
        加载本地项目文档
        
        参数:
            project_id: 项目ID
            project_name: 项目名称
            
        返回:
            Dict[str, str]: 文档名称到内容的映射
            
        Validates: Requirement 9.5 - Stage_Context 包含本地文档内容
        """
        docs = {}
        project_root = _get_project_root()
        
        # 尝试多个可能的项目目录
        possible_dirs = [
            project_root / "projects" / project_id,
            project_root / "projects" / project_name,
        ]
        
        for project_dir in possible_dirs:
            if not project_dir.exists():
                continue
            
            # 加载关键文档
            doc_files = [
                "requirements.md",
                "architecture.md",
                "design.md",
                "config.yaml",
            ]
            
            for doc_file in doc_files:
                doc_path = project_dir / doc_file
                if doc_path.exists():
                    try:
                        with open(doc_path, 'r', encoding='utf-8') as f:
                            docs[doc_file] = f.read()
                    except Exception as e:
                        logger.warning(f"Failed to load document {doc_path}: {e}")
            
            break  # 找到项目目录后停止
        
        return docs
    
    def update_stage_output(
        self, 
        context: WorkflowContext, 
        stage_name: str, 
        output: StageOutput
    ) -> None:
        """
        更新阶段输出并保存到 DynamoDB
        
        参数:
            context: 工作流上下文
            stage_name: 阶段名称
            output: 阶段输出
        """
        # 更新上下文中的阶段输出
        context.update_stage_output(stage_name, output)
        
        # 保存到 DynamoDB
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        stage_updates = {
            'status': output.status.value,
            'agent_output_content': output.content if not output.s3_content_ref else '',
            'agent_output_s3_ref': output.s3_content_ref,
            'metrics': output.metrics.to_dict(),
            'generated_files': [f.to_dict() for f in output.generated_files],
            'error_message': output.error_message,
        }
        
        if output.document_content:
            stage_updates['design_document'] = {
                'content': output.document_content,
                'format': output.document_format,
            }
        
        if output.completed_at:
            stage_updates['completed_at'] = output.completed_at.isoformat()
        
        self.db.update_stage(context.project_id, stage_name, stage_updates)
        
        # 更新项目聚合指标
        if output.is_completed:
            aggregated = context.aggregated_metrics.to_dict()
            self.db.update_project(context.project_id, {
                'aggregated_metrics': aggregated,
                'updated_at': now,
            })


# 全局单例
workflow_context_manager = WorkflowContextManager()


# 便捷函数
def load_workflow_context(project_id: str) -> WorkflowContext:
    """
    从 DynamoDB 加载工作流上下文
    
    参数:
        project_id: 项目ID
        
    返回:
        WorkflowContext: 加载的上下文
    """
    return workflow_context_manager.load_from_db(project_id)


def save_workflow_context(context: WorkflowContext) -> None:
    """
    保存工作流上下文到 DynamoDB
    
    参数:
        context: 要保存的上下文
    """
    workflow_context_manager.save_to_db(context)


def get_stage_context(
    context: WorkflowContext, 
    stage_name: str,
    include_rules: bool = True,
    include_local_docs: bool = True,
    max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
) -> str:
    """
    获取指定阶段的执行上下文
    
    参数:
        context: 工作流上下文
        stage_name: 目标阶段名称
        include_rules: 是否包含工作流规则
        include_local_docs: 是否包含本地文档
        max_tokens: 最大 token 数量限制
        
    返回:
        str: 格式化的上下文字符串
    """
    return workflow_context_manager.get_stage_context(
        context, stage_name, include_rules, include_local_docs, max_tokens
    )
