"""
工作流控制 API

提供工作流暂停、恢复、停止、重启等控制功能的 API 端点。

Requirements:
    - 3.1: 支持暂停控制
    - 3.2: 支持停止控制
    - 3.3: 支持恢复执行
    - 3.4: 支持从指定阶段重启
    - 3.5: 阶段状态查询
    - 3.6: Metrics 查询
    - 3.7: 阶段输出查看
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

from api.v2.database import db_client
from api.v2.services.project_service import ProjectService
from api.v2.services.stage_service import StageServiceV2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow-control"])


# ============== 请求/响应模型 ==============

class PauseRequest(BaseModel):
    """暂停请求"""
    reason: Optional[str] = Field(None, description="暂停原因")


class ResumeRequest(BaseModel):
    """恢复请求"""
    from_stage: Optional[str] = Field(None, description="从指定阶段恢复")


class RestartRequest(BaseModel):
    """重启请求"""
    from_stage: str = Field(..., description="从指定阶段重启")
    clear_subsequent: bool = Field(True, description="是否清除后续阶段数据")


class ControlResponse(BaseModel):
    """控制操作响应"""
    success: bool
    message: str
    project_id: str
    control_status: str
    timestamp: str


class StageStatusResponse(BaseModel):
    """阶段状态响应"""
    project_id: str
    stage_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""
    project_id: str
    project_name: str
    status: str
    control_status: str
    current_stage: Optional[str] = None
    completed_stages: List[str]
    pending_stages: List[str]
    aggregated_metrics: Optional[Dict[str, Any]] = None


class StageOutputResponse(BaseModel):
    """阶段输出响应"""
    project_id: str
    stage_name: str
    content: str
    document_content: Optional[str] = None
    document_format: Optional[str] = None
    generated_files: List[Dict[str, Any]] = []


class MetricsResponse(BaseModel):
    """指标响应"""
    project_id: str
    stage_metrics: Dict[str, Dict[str, Any]]
    aggregated_metrics: Dict[str, Any]


class MultiAgentProgressResponse(BaseModel):
    """多 Agent 进度响应"""
    project_id: str
    is_multi_agent: bool
    agent_count: int
    orchestration_pattern: Optional[str] = None
    main_agent: Optional[str] = None
    agents: List[Dict[str, Any]] = []
    progress: Dict[str, Dict[str, Any]] = {}


class AgentProgressResponse(BaseModel):
    """单个 Agent 进度响应"""
    project_id: str
    agent_name: str
    agent_type: str
    description: str
    current_stage: Optional[str] = None
    completed_stages: int
    total_stages: int
    progress_percentage: float
    stage_statuses: Dict[str, str] = {}


# ============== 控制端点 ==============

@router.post("/{project_id}/pause", response_model=ControlResponse)
async def pause_workflow(
    project_id: str = Path(..., description="项目ID"),
    request: PauseRequest = None,
):
    """
    暂停工作流执行
    
    Validates: Requirement 3.1 - 支持暂停控制
    """
    try:
        project_service = ProjectService()
        
        # 检查项目是否存在
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # 检查当前状态
        current_status = project.get('control_status', 'running')
        if current_status == 'paused':
            return ControlResponse(
                success=True,
                message="Workflow is already paused",
                project_id=project_id,
                control_status='paused',
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        
        if current_status == 'stopped':
            raise HTTPException(
                status_code=400, 
                detail="Cannot pause a stopped workflow"
            )
        
        # 更新控制状态
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        updates = {
            'control_status': 'paused',
            'pause_requested_at': now,
            'updated_at': now,
        }
        
        db_client.update_project(project_id, updates)
        
        logger.info(f"Workflow paused for project: {project_id}")
        
        return ControlResponse(
            success=True,
            message="Workflow paused successfully",
            project_id=project_id,
            control_status='paused',
            timestamp=now,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/resume", response_model=ControlResponse)
async def resume_workflow(
    project_id: str = Path(..., description="项目ID"),
    request: ResumeRequest = None,
):
    """
    恢复工作流执行
    
    通过 project_service.control_project 方法恢复工作流，
    该方法会创建新任务并发送到 SQS 队列，由 worker 继续执行。
    
    Validates: Requirement 3.3 - 支持恢复执行
    """
    try:
        project_service = ProjectService()
        
        # 检查项目是否存在
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # 检查当前状态
        current_status = project.get('status', 'pending')
        control_status = project.get('control_status', 'running')
        
        # 如果工作流正在运行，直接返回
        if control_status == 'running' and current_status == 'building':
            return ControlResponse(
                success=True,
                message="Workflow is already running",
                project_id=project_id,
                control_status='running',
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        
        # 如果项目状态不是 paused，不能恢复
        if current_status != 'paused':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume workflow in {current_status} status. Only paused workflows can be resumed."
            )
        
        # 如果指定了起始阶段，先更新 resume_from_stage
        if request and request.from_stage:
            db_client.update_project(project_id, {'resume_from_stage': request.from_stage})
        
        # 调用 project_service.control_project 来恢复工作流
        # 这会创建新任务并发送到 SQS
        result = project_service.control_project(project_id, 'resume')
        
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Workflow resumed for project: {project_id}, task_id: {result.get('task_id')}")
        
        return ControlResponse(
            success=True,
            message=result.get('message', 'Workflow resumed successfully'),
            project_id=project_id,
            control_status='running',
            timestamp=now,
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Failed to resume workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resume workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/stop", response_model=ControlResponse)
async def stop_workflow(
    project_id: str = Path(..., description="项目ID"),
):
    """
    停止工作流执行
    
    Validates: Requirement 3.2 - 支持停止控制
    """
    try:
        project_service = ProjectService()
        
        # 检查项目是否存在
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # 检查当前状态
        current_status = project.get('control_status', 'running')
        if current_status == 'stopped':
            return ControlResponse(
                success=True,
                message="Workflow is already stopped",
                project_id=project_id,
                control_status='stopped',
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        
        # 更新控制状态
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        updates = {
            'control_status': 'stopped',
            'stop_requested_at': now,
            'updated_at': now,
        }
        
        db_client.update_project(project_id, updates)
        
        logger.info(f"Workflow stopped for project: {project_id}")
        
        return ControlResponse(
            success=True,
            message="Workflow stopped successfully",
            project_id=project_id,
            control_status='stopped',
            timestamp=now,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/restart", response_model=ControlResponse)
async def restart_workflow(
    project_id: str = Path(..., description="项目ID"),
    request: RestartRequest = None,
):
    """
    从指定阶段重启工作流
    
    Validates: Requirement 3.4 - 支持从指定阶段重启
    """
    try:
        project_service = ProjectService()
        stage_service = StageServiceV2()
        
        # 检查项目是否存在
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        from_stage = request.from_stage if request else None
        if not from_stage:
            raise HTTPException(status_code=400, detail="from_stage is required")
        
        # 验证阶段名称 - 使用 BuildStage 枚举值
        valid_stages = [
            'orchestrator', 'requirements_analysis', 'system_architecture',
            'agent_design', 'tools_developer', 'prompt_engineer',
            'agent_code_developer', 'agent_developer_manager', 'agent_deployer'
        ]
        
        # 标准化阶段名称（支持旧名称输入）
        normalized_from_stage = stage_service._normalize_stage_name(from_stage)
        if not normalized_from_stage or normalized_from_stage not in valid_stages:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid stage name: {from_stage}"
            )
        
        # 如果需要清除后续阶段数据
        if request and request.clear_subsequent:
            stage_index = valid_stages.index(normalized_from_stage)
            stages_to_clear = valid_stages[stage_index:]
            
            for stage_name in stages_to_clear:
                db_client.update_stage(project_id, stage_name, {
                    'status': 'pending',
                    'agent_output_content': '',
                    'agent_output_s3_ref': None,
                    'metrics': {},
                    'generated_files': [],
                    'error_message': None,
                    'completed_at': None,
                })
        
        # 更新项目状态
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        updates = {
            'control_status': 'running',
            'status': 'building',  # 使用正确的 ProjectStatus 值
            'current_stage': normalized_from_stage,
            'resume_from_stage': normalized_from_stage,
            'pause_requested_at': None,
            'stop_requested_at': None,
            'updated_at': now,
        }
        
        db_client.update_project(project_id, updates)
        
        logger.info(f"Workflow restarted from stage {normalized_from_stage} for project: {project_id}")
        
        return ControlResponse(
            success=True,
            message=f"Workflow restarted from stage: {normalized_from_stage}",
            project_id=project_id,
            control_status='running',
            timestamp=now,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 状态查询端点 ==============

@router.get("/{project_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    project_id: str = Path(..., description="项目ID"),
):
    """
    获取工作流状态
    
    Validates: Requirement 3.5 - 阶段状态查询
    """
    try:
        project_service = ProjectService()
        stage_service = StageServiceV2()
        
        # 获取项目
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # 获取所有阶段
        stages = stage_service.list_stages(project_id)
        
        # 分类阶段
        completed_stages = []
        pending_stages = []
        
        for stage in stages:
            stage_name = stage.get('stage_name', '')
            status = stage.get('status', 'pending')
            
            if status == 'completed':
                completed_stages.append(stage_name)
            elif status in ['pending', 'running']:
                pending_stages.append(stage_name)
        
        return WorkflowStatusResponse(
            project_id=project_id,
            project_name=project.get('project_name', ''),
            status=project.get('status', 'pending'),
            control_status=project.get('control_status', 'running'),
            current_stage=project.get('current_stage'),
            completed_stages=completed_stages,
            pending_stages=pending_stages,
            aggregated_metrics=project.get('aggregated_metrics'),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/stages/{stage_name}", response_model=StageStatusResponse)
async def get_stage_status(
    project_id: str = Path(..., description="项目ID"),
    stage_name: str = Path(..., description="阶段名称"),
):
    """
    获取指定阶段的状态
    
    Validates: Requirement 3.5 - 阶段状态查询
    """
    try:
        stage_service = StageServiceV2()
        
        # 获取阶段
        stage = stage_service.get_stage(project_id, stage_name)
        if not stage:
            raise HTTPException(
                status_code=404, 
                detail=f"Stage {stage_name} not found for project {project_id}"
            )
        
        return StageStatusResponse(
            project_id=project_id,
            stage_name=stage_name,
            status=stage.get('status', 'pending'),
            started_at=stage.get('started_at'),
            completed_at=stage.get('completed_at'),
            error_message=stage.get('error_message'),
            metrics=stage.get('metrics'),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stage status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/metrics", response_model=MetricsResponse)
async def get_workflow_metrics(
    project_id: str = Path(..., description="项目ID"),
):
    """
    获取工作流指标
    
    Validates: Requirement 3.6 - Metrics 查询
    """
    try:
        project_service = ProjectService()
        stage_service = StageServiceV2()
        
        # 获取项目
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # 获取所有阶段的指标
        stages = stage_service.list_stages(project_id)
        
        stage_metrics = {}
        for stage in stages:
            stage_name = stage.get('stage_name', '')
            metrics = stage.get('metrics', {})
            if metrics:
                stage_metrics[stage_name] = metrics
        
        return MetricsResponse(
            project_id=project_id,
            stage_metrics=stage_metrics,
            aggregated_metrics=project.get('aggregated_metrics', {}),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/stages/{stage_name}/output", response_model=StageOutputResponse)
async def get_stage_output(
    project_id: str = Path(..., description="项目ID"),
    stage_name: str = Path(..., description="阶段名称"),
):
    """
    获取阶段输出内容
    
    Validates: Requirement 3.7 - 阶段输出查看
    """
    try:
        stage_service = StageServiceV2()
        
        # 获取阶段
        stage = stage_service.get_stage(project_id, stage_name)
        if not stage:
            raise HTTPException(
                status_code=404, 
                detail=f"Stage {stage_name} not found for project {project_id}"
            )
        
        # 获取输出内容
        content = stage.get('agent_output_content', '')
        
        # 如果内容存储在 S3，从 S3 获取
        s3_ref = stage.get('agent_output_s3_ref')
        if s3_ref and not content:
            content = stage_service._load_content_from_s3(s3_ref)
        
        # 获取设计文档
        design_doc = stage.get('design_document', {})
        
        return StageOutputResponse(
            project_id=project_id,
            stage_name=stage_name,
            content=content,
            document_content=design_doc.get('content'),
            document_format=design_doc.get('format'),
            generated_files=stage.get('generated_files', []),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stage output: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 多 Agent 进度端点 ==============

@router.get("/{project_id}/multi-agent/progress", response_model=MultiAgentProgressResponse)
async def get_multi_agent_progress(
    project_id: str = Path(..., description="项目ID"),
):
    """
    获取多 Agent 项目的进度
    
    Validates: Requirement 6.7 - 多 Agent 进度跟踪
    """
    try:
        project_service = ProjectService()
        
        # 获取项目
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # 尝试加载工作流上下文并解析多 Agent 架构
        try:
            from nexus_utils.workflow import (
                load_workflow_context,
                MultiAgentIterator,
            )
            
            context = load_workflow_context(project_id)
            iterator = MultiAgentIterator(context)
            
            if not iterator.is_multi_agent:
                return MultiAgentProgressResponse(
                    project_id=project_id,
                    is_multi_agent=False,
                    agent_count=1,
                    orchestration_pattern=None,
                    main_agent=None,
                    agents=[],
                    progress={},
                )
            
            # 获取架构信息
            architecture = iterator.architecture
            
            # 获取所有 Agent 的进度
            progress = iterator.get_all_progress()
            
            # 构建 Agent 列表
            agents = []
            if architecture:
                for agent in architecture.agents:
                    agents.append({
                        'name': agent.name,
                        'type': agent.agent_type,
                        'description': agent.description,
                        'orchestration_pattern': agent.orchestration_pattern,
                        'dependencies': agent.dependencies,
                        'tools': agent.tools,
                    })
            
            return MultiAgentProgressResponse(
                project_id=project_id,
                is_multi_agent=True,
                agent_count=architecture.agent_count if architecture else 0,
                orchestration_pattern=architecture.orchestration_pattern if architecture else None,
                main_agent=architecture.main_agent if architecture else None,
                agents=agents,
                progress=progress,
            )
            
        except ImportError:
            logger.warning("Workflow module not available")
            return MultiAgentProgressResponse(
                project_id=project_id,
                is_multi_agent=False,
                agent_count=1,
                orchestration_pattern=None,
                main_agent=None,
                agents=[],
                progress={},
            )
        except ValueError as e:
            # 项目不存在或无法加载上下文
            logger.warning(f"Failed to load workflow context: {e}")
            return MultiAgentProgressResponse(
                project_id=project_id,
                is_multi_agent=False,
                agent_count=1,
                orchestration_pattern=None,
                main_agent=None,
                agents=[],
                progress={},
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get multi-agent progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/multi-agent/agents/{agent_name}/progress", response_model=AgentProgressResponse)
async def get_agent_progress(
    project_id: str = Path(..., description="项目ID"),
    agent_name: str = Path(..., description="Agent名称"),
):
    """
    获取指定 Agent 的进度
    
    Validates: Requirement 6.7 - 多 Agent 进度跟踪
    """
    try:
        project_service = ProjectService()
        
        # 获取项目
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        try:
            from nexus_utils.workflow import (
                load_workflow_context,
                MultiAgentIterator,
            )
            
            context = load_workflow_context(project_id)
            iterator = MultiAgentIterator(context)
            
            if not iterator.is_multi_agent:
                raise HTTPException(
                    status_code=400, 
                    detail="This is not a multi-agent project"
                )
            
            # 查找指定的 Agent
            architecture = iterator.architecture
            agent_def = architecture.get_agent(agent_name) if architecture else None
            
            if not agent_def:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Agent {agent_name} not found"
                )
            
            # 获取进度
            progress = iterator.get_progress(agent_name)
            
            return AgentProgressResponse(
                project_id=project_id,
                agent_name=agent_name,
                agent_type=agent_def.agent_type,
                description=agent_def.description,
                current_stage=progress.current_stage,
                completed_stages=progress.completed_stages,
                total_stages=progress.total_stages,
                progress_percentage=progress.progress_percentage,
                stage_statuses={k: v.value for k, v in progress.stage_statuses.items()},
            )
            
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Workflow module not available"
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ============== 文件同步端点 ==============

class FileListResponse(BaseModel):
    """文件列表响应"""
    project_id: str
    files: List[Dict[str, Any]]
    total_count: int


class FileContentResponse(BaseModel):
    """文件内容响应"""
    project_id: str
    file_path: str
    content: Optional[str] = None
    size: int = 0
    checksum: Optional[str] = None
    last_modified: Optional[str] = None


@router.get("/{project_id}/files", response_model=FileListResponse)
async def list_project_files(
    project_id: str = Path(..., description="项目ID"),
    stage_name: Optional[str] = Query(None, description="阶段名称（可选）"),
):
    """
    列出项目的所有文件
    
    Validates: Requirement 10.3 - 文件列表查询
    """
    try:
        project_service = ProjectService()
        
        # 获取项目
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        try:
            from nexus_utils.workflow import FileMetadataManager
            
            manager = FileMetadataManager()
            files = manager.get_file_metadata(project_id, stage_name)
            
            return FileListResponse(
                project_id=project_id,
                files=[f.to_dict() for f in files],
                total_count=len(files),
            )
            
        except ImportError:
            return FileListResponse(
                project_id=project_id,
                files=[],
                total_count=0,
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list project files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/files/{file_path:path}", response_model=FileContentResponse)
async def get_file_content_api(
    project_id: str = Path(..., description="项目ID"),
    file_path: str = Path(..., description="文件路径"),
):
    """
    获取文件内容
    
    Validates: Requirement 10.5 - 文件内容 API
    """
    try:
        project_service = ProjectService()
        
        # 获取项目
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        project_name = project.get('project_name', '')
        
        try:
            from nexus_utils.workflow import FileMetadataManager, get_file_content
            
            manager = FileMetadataManager()
            
            # 获取文件内容
            content = get_file_content(project_id, file_path, project_name)
            
            if content is None:
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found: {file_path}"
                )
            
            # 获取文件元数据
            files = manager.get_file_metadata(project_id)
            file_meta = None
            for f in files:
                if f.path == file_path:
                    file_meta = f
                    break
            
            return FileContentResponse(
                project_id=project_id,
                file_path=file_path,
                content=content,
                size=file_meta.size if file_meta else len(content),
                checksum=file_meta.checksum if file_meta else None,
                last_modified=file_meta.last_modified.isoformat() if file_meta and file_meta.last_modified else None,
            )
            
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="Workflow module not available"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
