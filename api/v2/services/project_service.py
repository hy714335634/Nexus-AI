"""
Project Service - 项目管理服务

职责:
- 创建项目并提交构建任务到 SQS
- 查询项目详情和列表
- 更新项目状态
- 项目控制操作
- 扫描本地项目目录
"""
import uuid
import logging
import os
import re
import yaml
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from api.v2.database import db_client, sqs_client
from api.v2.models.schemas import (
    ProjectStatus,
    TaskStatus,
    TaskType,
    BuildStage,
    CreateProjectRequest,
)
from api.v2.config import settings

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent.parent


class ProjectService:
    """项目管理服务"""
    
    def __init__(self):
        self.db = db_client
        self.sqs = sqs_client
        self._local_projects_cache = None
        self._cache_time = None
    
    def _scan_local_projects(self) -> List[Dict[str, Any]]:
        """扫描本地项目目录"""
        projects = []
        project_root = _get_project_root()
        projects_dir = project_root / "projects"
        
        if not projects_dir.exists():
            return projects
        
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith('.'):
                project_info = self._parse_local_project(project_dir)
                if project_info:
                    projects.append(project_info)
        
        return projects
    
    def _parse_local_project(self, project_dir: Path) -> Optional[Dict[str, Any]]:
        """解析本地项目目录"""
        try:
            project_id = project_dir.name
            status_file = project_dir / "status.yaml"
            config_file = project_dir / "config.yaml"
            
            project_name = project_id
            description = ""
            status = ProjectStatus.COMPLETED.value
            progress = 100.0
            stages = []
            metrics = {}
            
            # 解析 status.yaml
            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = yaml.safe_load(f)
                
                project_info_list = status_data.get('project_info', [])
                if project_info_list and len(project_info_list) > 0:
                    info = project_info_list[0]
                    project_name = info.get('name', project_id)
                    description = info.get('description', '')
                    
                    # 解析进度
                    progress_info = info.get('progress', [])
                    if progress_info and len(progress_info) > 0:
                        completed = progress_info[0].get('completed', 0)
                        total = progress_info[0].get('total', 1)
                        progress = (completed / total) * 100 if total > 0 else 0
                        
                        if completed < total:
                            status = ProjectStatus.BUILDING.value
                    
                    # 解析阶段信息
                    agents_list = info.get('agents', [])
                    if agents_list and len(agents_list) > 0:
                        agent_info = agents_list[0]
                        pipeline = agent_info.get('pipeline', [])
                        
                        stage_order = 1
                        for stage_data in pipeline:
                            stage_name = stage_data.get('stage', '')
                            stage_status = 'completed' if stage_data.get('status', False) else 'pending'
                            doc_path = stage_data.get('doc_path', '')
                            artifact_paths = stage_data.get('agent_artifact_path', [])
                            
                            stages.append({
                                'name': stage_name,
                                'display_name': self._get_stage_display_name(stage_name),
                                'order': stage_order,
                                'status': stage_status,
                                'started_at': stage_data.get('updated_date'),
                                'completed_at': stage_data.get('updated_date') if stage_status == 'completed' else None,
                                'doc_path': doc_path,
                                'artifact_paths': artifact_paths,
                            })
                            stage_order += 1
            
            # 解析 config.yaml
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    if not description:
                        description = config_data.get('description', '')
                except:
                    pass
            
            # 检查 workflow_summary_report.md
            report_file = project_dir / "workflow_summary_report.md"
            has_report = report_file.exists()
            
            # 获取文件时间
            created_at = datetime.fromtimestamp(project_dir.stat().st_ctime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
            updated_at = datetime.fromtimestamp(project_dir.stat().st_mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
            
            return {
                'project_id': project_id,
                'project_name': project_name,
                'status': status,
                'requirement': description,
                'progress': progress,
                'current_stage': stages[-1]['name'] if stages else None,
                'stages': stages,
                'completed_stages': sum(1 for s in stages if s.get('status') == 'completed'),
                'total_stages': len(stages),
                'created_at': created_at,
                'updated_at': updated_at,
                'has_workflow_report': has_report,
                'source': 'local',
                'metrics': metrics,
            }
        except Exception as e:
            logger.warning(f"Failed to parse local project {project_dir.name}: {e}")
            return None
    
    def _get_stage_display_name(self, stage_name: str, workflow_type: str = "agent_build") -> str:
        """
        获取阶段显示名称
        
        使用统一配置模块 api.v2.core.stage_config
        
        Args:
            stage_name: 阶段名称
            workflow_type: 工作流类型，默认为 'agent_build'
        """
        from api.v2.core.stage_config import get_stage_display_name
        return get_stage_display_name(stage_name, workflow_type)
    
    def _get_local_projects(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """获取本地项目（带缓存）"""
        now = datetime.now(timezone.utc)
        
        # 缓存 60 秒
        if not force_refresh and self._local_projects_cache is not None and self._cache_time is not None:
            if (now - self._cache_time).total_seconds() < 60:
                return self._local_projects_cache
        
        self._local_projects_cache = self._scan_local_projects()
        self._cache_time = now
        return self._local_projects_cache
    
    def create_project(self, request: CreateProjectRequest) -> Dict[str, Any]:
        """
        创建项目并提交构建任务
        
        流程:
        1. 生成项目ID和任务ID
        2. 创建项目记录 (status=pending)
        3. 初始化所有阶段记录
        4. 创建任务记录 (status=pending)
        5. 发送消息到 SQS 构建队列
        6. 更新项目和任务状态为 queued
        
        Returns:
            包含 project_id, task_id 等信息的字典
        """
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # 生成项目名称
        project_name = request.project_name or self._generate_project_name(request.requirement)
        
        # 1. 创建项目记录
        project_data = {
            'project_id': project_id,
            'project_name': project_name,
            'status': ProjectStatus.PENDING.value,
            'requirement': request.requirement,
            'user_id': request.user_id or 'anonymous',
            'user_name': request.user_name,
            'priority': request.priority,
            'tags': request.tags or [],
            'progress': 0.0,
            'current_stage': None,
            'error_info': None,
            'started_at': None,
            'completed_at': None,
            'metrics': {}
        }
        
        self.db.create_project(project_data)
        logger.info(f"Created project {project_id}")
        
        # 2. 初始化阶段记录
        self._initialize_stages(project_id)
        logger.info(f"Initialized stages for project {project_id}")
        
        # 3. 创建任务记录
        task_data = {
            'task_id': task_id,
            'task_type': TaskType.BUILD_AGENT.value,
            'project_id': project_id,
            'status': TaskStatus.PENDING.value,
            'priority': request.priority,
            'payload': {
                'requirement': request.requirement,
                'user_id': request.user_id,
                'user_name': request.user_name,
                'project_name': project_name,
                'tags': request.tags or []
            },
            'result': None,
            'error_message': None,
            'retry_count': 0,
            'started_at': None,
            'completed_at': None,
            'worker_id': None
        }
        
        self.db.create_task(task_data)
        logger.info(f"Created task {task_id} for project {project_id}")
        
        # 4. 发送消息到 SQS
        try:
            self.sqs.send_build_task(
                task_id=task_id,
                project_id=project_id,
                requirement=request.requirement,
                user_id=request.user_id,
                priority=request.priority,
                metadata={
                    'project_name': project_name,
                    'user_name': request.user_name,
                    'tags': request.tags or []
                }
            )
            logger.info(f"Sent build task {task_id} to SQS")
            
            # 5. 更新状态为 queued
            self.db.update_project(project_id, {'status': ProjectStatus.QUEUED.value})
            self.db.update_task(task_id, {'status': TaskStatus.QUEUED.value})
            
        except Exception as e:
            logger.error(f"Failed to send task to SQS: {e}")
            # 更新状态为失败
            self.db.update_project(project_id, {
                'status': ProjectStatus.FAILED.value,
                'error_info': {'message': f'Failed to queue task: {str(e)}'}
            })
            self.db.update_task(task_id, {
                'status': TaskStatus.FAILED.value,
                'error_message': str(e)
            })
            raise
        
        return {
            'project_id': project_id,
            'task_id': task_id,
            'project_name': project_name,
            'status': ProjectStatus.QUEUED.value,
            'message': '项目已创建，构建任务已提交到队列'
        }
    
    def _initialize_stages(self, project_id: str):
        """
        初始化项目的所有阶段
        
        使用统一配置模块的阶段顺序，确保 stage_number 与配置一致
        """
        from api.v2.core.stage_config import STAGES, STAGE_SEQUENCE
        
        for stage_name in STAGE_SEQUENCE:
            stage_config = STAGES.get(stage_name)
            if not stage_config:
                continue
            
            stage_data = {
                'project_id': project_id,
                'stage_name': stage_name,
                'stage_number': stage_config.order,
                'display_name': stage_config.display_name,
                'status': 'pending',
                'agent_name': None,
                'started_at': None,
                'completed_at': None,
                'duration_seconds': None,
                'input_tokens': None,
                'output_tokens': None,
                'tool_calls': None,
                'output_data': None,
                'error_message': None,
                'logs': []
            }
            self.db.create_stage(stage_data)
    
    def _generate_project_name(self, requirement: str) -> str:
        """
        从需求描述生成项目名称
        
        当用户未指定项目名称时，生成一个临时名称。
        实际的项目目录名称将由 Agent 在 project_init 时决定。
        """
        import hashlib
        from datetime import datetime
        
        # 生成一个基于时间和需求的短哈希作为临时标识
        timestamp = datetime.now().strftime('%m%d%H%M')
        req_hash = hashlib.md5(requirement.encode()).hexdigest()[:6]
        
        # 返回一个临时名称，格式：agent_MMDDHHMMSS_hash
        return f"agent_{timestamp}_{req_hash}"
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目详情 - 先从数据库查找，再从本地目录查找"""
        # 先从数据库查找
        project = self.db.get_project(project_id)
        if project:
            # 获取阶段信息
            stages = self.db.list_stages(project_id)
            project['stages'] = stages
            
            # 计算完成的阶段数
            completed_stages = sum(1 for s in stages if s.get('status') == 'completed')
            project['completed_stages'] = completed_stages
            project['total_stages'] = len(stages)
            project['source'] = 'database'
            return project
        
        # 从本地项目查找
        local_projects = self._get_local_projects()
        for local_project in local_projects:
            if local_project['project_id'] == project_id:
                return local_project
        
        return None
    
    def list_projects(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """列表项目 - 合并数据库和本地项目"""
        # 从数据库获取
        db_result = self.db.list_projects(
            status=status,
            user_id=user_id,
            limit=limit
        )
        
        db_projects = db_result.get('items', [])
        db_project_ids = {p.get('project_id') for p in db_projects}
        
        # 获取本地项目
        local_projects = self._get_local_projects()
        
        # 合并，避免重复
        all_projects = list(db_projects)
        for local_project in local_projects:
            if local_project['project_id'] not in db_project_ids:
                # 应用筛选条件
                if status and local_project.get('status') != status:
                    continue
                # 转换为摘要格式
                all_projects.append({
                    'project_id': local_project['project_id'],
                    'project_name': local_project.get('project_name'),
                    'status': local_project.get('status'),
                    'progress': local_project.get('progress', 0),
                    'current_stage': local_project.get('current_stage'),
                    'created_at': local_project.get('created_at'),
                    'updated_at': local_project.get('updated_at'),
                })
        
        total = len(all_projects)
        pages = (total + limit - 1) // limit if total > 0 else 0
        
        # 分页
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_projects = all_projects[start_idx:end_idx]
        
        return {
            'items': paginated_projects,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': pages,
                'has_next': end_idx < total,
                'has_prev': page > 1
            }
        }
    
    def get_build_dashboard(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取构建仪表板数据 - 支持数据库和本地项目
        
        根据 workflow_type 确定产物目录：
        - agent_build: projects/{project_name}
        - agent_update: projects/{project_name}  
        - tool_build: tools/generated_tools/tool_build_{tool_name}
        """
        # 先从数据库获取
        project = self.db.get_project(project_id)
        
        if project:
            stages = self.db.list_stages(project_id)
            workflow_type = project.get('workflow_type', 'agent_build')
            
            # 根据工作流类型确定本地项目目录
            local_project_dir = self._get_workflow_artifact_dir(project, workflow_type)
            
            # 转换阶段数据格式
            dashboard_stages = []
            for stage in stages:
                stage_name = stage.get('stage_name', '')
                # 确保 display_name 不为 None，使用阶段名称作为默认值
                display_name = stage.get('display_name') or self._get_stage_display_name(stage_name, workflow_type) or stage_name
                dashboard_stages.append({
                    'name': stage_name,
                    'display_name': display_name,
                    'order': stage.get('stage_number', 0),
                    'status': stage.get('status', 'pending'),
                    'started_at': stage.get('started_at'),
                    'completed_at': stage.get('completed_at'),
                    'duration_seconds': stage.get('duration_seconds'),
                    'error': stage.get('error_message'),
                    'input_tokens': stage.get('input_tokens'),
                    'output_tokens': stage.get('output_tokens'),
                    'tool_calls': stage.get('tool_calls'),
                    'doc_path': stage.get('doc_path'),
                    'artifact_paths': stage.get('artifact_paths', []),
                    'efficiency_rating': stage.get('efficiency_rating'),
                })
            
            completed_stages = sum(1 for s in stages if s.get('status') == 'completed')
            
            # 构建指标数据
            raw_metrics = project.get('metrics', {})
            metrics = None
            if raw_metrics:
                cost_estimation = raw_metrics.get('cost_estimation', {})
                metrics = {
                    'total_duration_seconds': raw_metrics.get('total_duration_seconds'),
                    'input_tokens': raw_metrics.get('total_input_tokens'),
                    'output_tokens': raw_metrics.get('total_output_tokens'),
                    'tool_calls': raw_metrics.get('total_tool_calls'),
                    'total_tools': project.get('total_tools'),
                    'cost_input_usd': cost_estimation.get('input_cost_usd'),
                    'cost_output_usd': cost_estimation.get('output_cost_usd'),
                    'cost_total_usd': cost_estimation.get('total_cost_usd'),
                    'pricing_model': cost_estimation.get('pricing_model'),
                    'successful_stages': raw_metrics.get('successful_stages'),
                    'failed_stages': raw_metrics.get('failed_stages'),
                }
            
            return {
                'project_id': project_id,
                'project_name': project.get('project_name'),
                'workflow_type': workflow_type,
                'local_project_dir': local_project_dir,
                'status': project.get('status'),
                'progress': project.get('progress', 0.0),
                'requirement': project.get('requirement'),
                'stages': dashboard_stages,
                'total_stages': len(stages),
                'completed_stages': completed_stages,
                'updated_at': project.get('updated_at'),
                'metrics': metrics,
                'config_summary': project.get('config_summary'),
                'error_info': project.get('error_info'),
                'source': 'database'
            }
        
        # 从本地项目获取
        local_projects = self._get_local_projects()
        for local_project in local_projects:
            if local_project['project_id'] == project_id:
                # 尝试从本地文件读取指标
                metrics = self._load_local_project_metrics(project_id)
                
                return {
                    'project_id': project_id,
                    'project_name': local_project.get('project_name'),
                    'workflow_type': local_project.get('workflow_type', 'agent_build'),
                    'status': local_project.get('status'),
                    'progress': local_project.get('progress', 0.0),
                    'requirement': local_project.get('requirement'),
                    'stages': local_project.get('stages', []),
                    'total_stages': local_project.get('total_stages', 0),
                    'completed_stages': local_project.get('completed_stages', 0),
                    'updated_at': local_project.get('updated_at'),
                    'metrics': metrics,
                    'error_info': None,
                    'has_workflow_report': local_project.get('has_workflow_report', False),
                    'source': 'local'
                }
        
        return None
    
    def _get_workflow_artifact_dir(self, project: Dict[str, Any], workflow_type: str) -> Optional[str]:
        """
        根据工作流类型获取产物目录路径
        
        Args:
            project: 项目数据
            workflow_type: 工作流类型
            
        Returns:
            产物目录的相对路径
        """
        project_name = project.get('project_name', '')
        metadata = project.get('metadata', {})
        
        if workflow_type == 'tool_build':
            # 工具构建：产物在 tools/generated_tools/tool_build_{tool_name}
            tool_name = metadata.get('tool_name') or project_name
            # 确保目录名以 tool_build_ 开头
            if tool_name and not tool_name.startswith('tool_build_'):
                tool_name = f"tool_build_{tool_name}"
            return f"tools/generated_tools/{tool_name}" if tool_name else None
        elif workflow_type == 'agent_update':
            # Agent 更新：产物在原 Agent 的项目目录
            agent_name = metadata.get('agent_name')
            original_project_id = metadata.get('original_project_id')
            # 优先使用原项目目录
            if original_project_id:
                return f"projects/{original_project_id}"
            elif agent_name:
                return f"projects/{agent_name}"
            return None
        else:
            # Agent 构建：产物在 projects/{project_name}
            local_dir = project.get('local_project_dir') or project_name
            return f"projects/{local_dir}" if local_dir else None
    
    def _load_local_project_metrics(self, project_id: str) -> Optional[Dict[str, Any]]:
        """从本地项目文件加载指标数据"""
        try:
            project_root = _get_project_root()
            project_dir = project_root / "projects" / project_id
            
            # 读取 project_config.json
            config_path = project_dir / "project_config.json"
            total_tools = 0
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                total_tools = config.get('total_tools', 0)
            
            # 读取 workflow_summary_report.md 并解析指标
            report_path = project_dir / "workflow_summary_report.md"
            if not report_path.exists():
                return None
            
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            metrics = {
                'total_tools': total_tools
            }
            
            # 解析总执行时间
            duration_match = re.search(r'\*\*总执行时间\*\*:\s*([\d.]+)\s*秒', content)
            if duration_match:
                metrics['total_duration_seconds'] = float(duration_match.group(1))
            
            # 解析Token
            input_match = re.search(r'\*\*总输入Token\*\*:\s*([\d.]+)K?', content)
            if input_match:
                value = float(input_match.group(1))
                if 'K' in content[input_match.start():input_match.end() + 5]:
                    value *= 1000
                metrics['input_tokens'] = int(value)
            
            output_match = re.search(r'\*\*总输出Token\*\*:\s*([\d.]+)K?', content)
            if output_match:
                value = float(output_match.group(1))
                if 'K' in content[output_match.start():output_match.end() + 5]:
                    value *= 1000
                metrics['output_tokens'] = int(value)
            
            # 解析工具调用
            tool_calls_match = re.search(r'\*\*总工具调用次数\*\*:\s*(\d+)', content)
            if tool_calls_match:
                metrics['tool_calls'] = int(tool_calls_match.group(1))
            
            # 解析成本
            total_cost_match = re.search(r'\*\*总成本\*\*:\s*\$([\d.]+)', content)
            if total_cost_match:
                metrics['cost_total_usd'] = float(total_cost_match.group(1))
            
            input_cost_match = re.search(r'\*\*输入成本\*\*:\s*\$([\d.]+)', content)
            if input_cost_match:
                metrics['cost_input_usd'] = float(input_cost_match.group(1))
            
            output_cost_match = re.search(r'\*\*输出成本\*\*:\s*\$([\d.]+)', content)
            if output_cost_match:
                metrics['cost_output_usd'] = float(output_cost_match.group(1))
            
            pricing_match = re.search(r'\*\*定价模型\*\*:\s*(.+)', content)
            if pricing_match:
                metrics['pricing_model'] = pricing_match.group(1).strip()
            
            # 解析阶段统计
            stages_match = re.search(r'\*\*成功阶段数\*\*:\s*(\d+)/(\d+)', content)
            if stages_match:
                metrics['successful_stages'] = int(stages_match.group(1))
                total = int(stages_match.group(2))
                metrics['failed_stages'] = total - metrics['successful_stages']
            
            return metrics
            
        except Exception as e:
            logger.warning(f"加载本地项目指标失败: {e}")
            return None
    
    def control_project(self, project_id: str, action: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        控制项目状态
        
        支持的操作:
        - pause: 暂停构建（完成当前阶段后停止）
        - resume: 恢复构建
        - stop: 停止构建（完成当前 LLM 调用后停止）
        - cancel: 取消构建
        - restart: 从指定阶段重新开始
        
        Validates:
            - Requirement 3.1: 支持暂停控制
            - Requirement 3.2: 支持停止控制
            - Requirement 3.3: 支持恢复执行
            - Requirement 3.4: 支持从指定阶段重新开始
        """
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        current_status = project.get('status')
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        new_status = None
        updates = {}
        
        if action == 'pause':
            if current_status in [ProjectStatus.BUILDING.value, ProjectStatus.QUEUED.value]:
                new_status = ProjectStatus.PAUSED.value
                updates['control_status'] = 'paused'
                updates['pause_requested_at'] = now
                updates['last_control_action'] = 'pause'
            else:
                raise ValueError(f"Cannot pause project in {current_status} status")
        
        elif action == 'resume':
            if current_status == ProjectStatus.PAUSED.value:
                # 获取当前阶段，从下一个待执行阶段恢复
                current_stage = project.get('current_stage')
                resume_from_stage = project.get('resume_from_stage')
                
                # 确定恢复的起始阶段
                target_stage = resume_from_stage or current_stage
                
                # 如果没有指定阶段，查找下一个待执行阶段
                if not target_stage:
                    stages = self.db.list_stages(project_id)
                    for stage in sorted(stages, key=lambda x: x.get('stage_number', 0)):
                        if stage.get('status') != 'completed':
                            target_stage = stage.get('stage_name')
                            break
                
                new_status = ProjectStatus.QUEUED.value
                updates['control_status'] = 'running'
                updates['pause_requested_at'] = None
                updates['stop_requested_at'] = None
                updates['last_control_action'] = 'resume'
                
                # 更新状态
                updates['status'] = new_status
                if reason:
                    updates['control_action_reason'] = reason
                
                self.db.update_project(project_id, updates)
                
                # 创建新任务并发送到 SQS
                task_id = f"task_{uuid.uuid4().hex[:12]}"
                task_data = {
                    'task_id': task_id,
                    'task_type': TaskType.BUILD_AGENT.value,
                    'project_id': project_id,
                    'status': TaskStatus.PENDING.value,
                    'priority': project.get('priority', 3),
                    'payload': {
                        'requirement': project.get('requirement'),
                        'project_name': project.get('project_name'),
                        'from_stage': target_stage,
                        'action': 'resume',
                    },
                    'result': None,
                    'error_message': None,
                    'retry_count': 0,
                    'started_at': None,
                    'completed_at': None,
                    'worker_id': None
                }
                self.db.create_task(task_data)
                
                # 发送到 SQS
                self.sqs.send_build_task(
                    task_id=task_id,
                    project_id=project_id,
                    requirement=project.get('requirement'),
                    priority=project.get('priority', 3),
                    metadata={
                        'project_name': project.get('project_name'),
                    },
                    target_stage=target_stage,
                    action='resume'
                )
                
                self.db.update_task(task_id, {'status': TaskStatus.QUEUED.value})
                
                return {
                    'project_id': project_id,
                    'task_id': task_id,
                    'action': action,
                    'previous_status': current_status,
                    'new_status': new_status,
                    'resume_from_stage': target_stage,
                    'message': f'Project resume from stage {target_stage} queued successfully'
                }
            else:
                raise ValueError(f"Cannot resume project in {current_status} status")
        
        elif action == 'stop':
            if current_status in [ProjectStatus.BUILDING.value, ProjectStatus.QUEUED.value, ProjectStatus.PAUSED.value]:
                new_status = ProjectStatus.CANCELLED.value
                updates['control_status'] = 'stopped'
                updates['stop_requested_at'] = now
                updates['last_control_action'] = 'stop'
                updates['completed_at'] = now
            else:
                raise ValueError(f"Cannot stop project in {current_status} status")
        
        elif action == 'cancel':
            if current_status in [ProjectStatus.BUILDING.value, ProjectStatus.QUEUED.value, ProjectStatus.PAUSED.value]:
                new_status = ProjectStatus.CANCELLED.value
                updates['control_status'] = 'cancelled'
                updates['last_control_action'] = 'cancel'
                updates['completed_at'] = now
            else:
                raise ValueError(f"Cannot cancel project in {current_status} status")
        
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # 更新状态
        updates['status'] = new_status
        if reason:
            updates['control_action_reason'] = reason
        
        self.db.update_project(project_id, updates)
        
        return {
            'project_id': project_id,
            'action': action,
            'previous_status': current_status,
            'new_status': new_status,
            'message': f'Project {action} successfully'
        }
    
    def restart_from_stage(
        self, 
        project_id: str, 
        from_stage: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从指定阶段重新开始构建
        
        Args:
            project_id: 项目ID
            from_stage: 起始阶段名称
            user_id: 操作用户ID
            
        Returns:
            操作结果
            
        Validates: Requirement 3.4 - 支持从指定阶段重新开始
        """
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        current_status = project.get('status')
        
        # 只有已完成、失败或已取消的项目可以重新开始
        if current_status not in [
            ProjectStatus.COMPLETED.value, 
            ProjectStatus.FAILED.value, 
            ProjectStatus.CANCELLED.value,
            ProjectStatus.PAUSED.value
        ]:
            raise ValueError(f"Cannot restart project in {current_status} status")
        
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        # 更新项目状态
        updates = {
            'status': ProjectStatus.QUEUED.value,
            'control_status': 'running',
            'resume_from_stage': from_stage,
            'last_control_action': 'restart',
            'control_action_by': user_id,
            'completed_at': None,
            'error_info': None,
        }
        self.db.update_project(project_id, updates)
        
        # 重置从指定阶段开始的所有阶段状态
        stages = self.db.list_stages(project_id)
        stage_order = [s.get('stage_name') for s in sorted(stages, key=lambda x: x.get('stage_number', 0))]
        
        if from_stage not in stage_order:
            raise ValueError(f"Unknown stage: {from_stage}")
        
        start_index = stage_order.index(from_stage)
        for stage_name in stage_order[start_index:]:
            self.db.update_stage(project_id, stage_name, {
                'status': 'pending',
                'started_at': None,
                'completed_at': None,
                'duration_seconds': None,
                'error_message': None,
                'agent_output_content': None,
                'agent_output_s3_ref': None,
                'metrics': None,
                'generated_files': None,
                'design_document': None,
            })
        
        # 创建新任务
        task_data = {
            'task_id': task_id,
            'task_type': TaskType.BUILD_AGENT.value,
            'project_id': project_id,
            'status': TaskStatus.PENDING.value,
            'priority': project.get('priority', 3),
            'payload': {
                'requirement': project.get('requirement'),
                'user_id': user_id,
                'project_name': project.get('project_name'),
                'from_stage': from_stage,
                'action': 'restart',
            },
            'result': None,
            'error_message': None,
            'retry_count': 0,
            'started_at': None,
            'completed_at': None,
            'worker_id': None
        }
        self.db.create_task(task_data)
        
        # 发送到 SQS
        try:
            self.sqs.send_build_task(
                task_id=task_id,
                project_id=project_id,
                requirement=project.get('requirement'),
                user_id=user_id,
                priority=project.get('priority', 3),
                metadata={
                    'project_name': project.get('project_name'),
                },
                target_stage=from_stage,
                action='restart'
            )
            
            self.db.update_task(task_id, {'status': TaskStatus.QUEUED.value})
            
        except Exception as e:
            logger.error(f"Failed to send restart task to SQS: {e}")
            self.db.update_project(project_id, {
                'status': ProjectStatus.FAILED.value,
                'error_info': {'message': f'Failed to queue restart task: {str(e)}'}
            })
            raise
        
        return {
            'project_id': project_id,
            'task_id': task_id,
            'from_stage': from_stage,
            'status': ProjectStatus.QUEUED.value,
            'message': f'Project restart from stage {from_stage} queued successfully'
        }
    
    def get_control_status(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目控制状态
        
        Args:
            project_id: 项目ID
            
        Returns:
            控制状态信息
            
        Validates: Requirement 3.5 - 支持查询控制状态
        """
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        return {
            'project_id': project_id,
            'status': project.get('status'),
            'control_status': project.get('control_status', 'running'),
            'current_stage': project.get('current_stage'),
            'progress': project.get('progress', 0.0),
            'pause_requested_at': project.get('pause_requested_at'),
            'stop_requested_at': project.get('stop_requested_at'),
            'resume_from_stage': project.get('resume_from_stage'),
            'last_control_action': project.get('last_control_action'),
            'control_action_by': project.get('control_action_by'),
        }
    
    def get_aggregated_metrics(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取项目聚合指标
        
        Args:
            project_id: 项目ID
            
        Returns:
            聚合指标数据
            
        Validates: Requirement 2.5 - 支持查询聚合指标
        """
        project = self.db.get_project(project_id)
        if not project:
            return None
        
        return project.get('aggregated_metrics', {
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'total_execution_time': 0.0,
            'total_tool_calls': 0,
        })
    
    def delete_project(self, project_id: str, delete_local_files: bool = True) -> bool:
        """
        删除项目及其关联数据
        
        Args:
            project_id: 项目ID
            delete_local_files: 是否删除本地文件，默认为True
            
        Returns:
            是否删除成功
        """
        import shutil
        
        project_root = _get_project_root()
        deleted_paths = []
        errors = []
        
        # 获取项目信息，用于确定本地目录名
        project = self.db.get_project(project_id)
        local_project_dir = None
        
        if project:
            # 优先使用 local_project_dir，否则使用 project_name
            local_project_dir = project.get('local_project_dir') or project.get('project_name')
        
        # 如果数据库中没有项目记录，尝试从本地项目查找
        if not local_project_dir:
            local_projects = self._get_local_projects()
            for local_project in local_projects:
                if local_project['project_id'] == project_id:
                    local_project_dir = project_id
                    break
        
        # 删除本地文件
        if delete_local_files and local_project_dir:
            # 需要删除的目录列表
            dirs_to_delete = [
                project_root / "projects" / local_project_dir,
                project_root / "agents" / "generated_agents" / local_project_dir,
                project_root / "prompts" / "generated_agents_prompts" / local_project_dir,
                project_root / "tools" / "generated_tools" / local_project_dir,
            ]
            
            for dir_path in dirs_to_delete:
                if dir_path.exists() and dir_path.is_dir():
                    try:
                        shutil.rmtree(dir_path)
                        deleted_paths.append(str(dir_path))
                        logger.info(f"Deleted directory: {dir_path}")
                    except Exception as e:
                        error_msg = f"Failed to delete {dir_path}: {e}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
        
        # 删除 DynamoDB 中的阶段记录
        stages = self.db.list_stages(project_id)
        for stage in stages:
            stage_name = stage.get('stage_name')
            if stage_name:
                try:
                    self.db.delete_stage(project_id, stage_name)
                    logger.info(f"Deleted stage: {project_id}/{stage_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete stage {stage_name}: {e}")
        
        # 删除 DynamoDB 中的项目记录
        result = self.db.delete_project(project_id)
        
        # 清除本地项目缓存
        self._local_projects_cache = None
        self._cache_time = None
        
        if deleted_paths:
            logger.info(f"Project {project_id} deleted. Removed directories: {deleted_paths}")
        if errors:
            logger.warning(f"Project {project_id} deleted with errors: {errors}")
        
        return result


# 全局单例
project_service = ProjectService()
