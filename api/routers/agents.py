"""
Agent management API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List, Dict, Any
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

from api.models.schemas import (
    CreateAgentRequest,
    CreateAgentResponse,
    ProjectStatusResponse,
    StagesResponse,
    AgentListResponse,
    AgentDetailsResponse,
    BuildControlRequest,
    APIResponse,
)
from api.core.exceptions import ValidationError, ResourceNotFoundError
from celery.result import AsyncResult

from api.core.celery_app import celery_app
from api.database.dynamodb_client import DynamoDBClient
from api.tasks.agent_build_tasks import build_agent
from api.models.schemas import TaskStatusResponse, TaskStatusData
from tools.system_tools.agent_build_workflow.stage_tracker import initialize_project_record

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/agents/create", response_model=CreateAgentResponse)
async def create_agent(request: CreateAgentRequest):
    """
    创建新的代理构建任务
    
    接收自然语言需求描述，启动代理构建工作流
    """
    try:
        session_id = f"job_{uuid.uuid4().hex}"
        project_id = session_id

        initialize_project_record(
            project_id,
            requirement=request.requirement,
            user_id=request.user_id,
            user_name=request.user_name,
        )

        task = build_agent.delay(
            project_id=project_id,
            requirement=request.requirement,
            session_id=session_id,
            user_id=request.user_id,
            user_name=request.user_name,
        )

        return CreateAgentResponse(
            success=True,
            data={
                "task_id": task.id,
                "session_id": session_id,
                "project_id": project_id,
                "status": "queued",
                "message": "代理构建任务已提交，正在排队执行",
            },
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4()),
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": "请检查输入参数",
                "suggestion": "确保需求描述完整且符合要求",
            },
        )
    except Exception as e:  # pragma: no cover - API surface
        logger.error("Error creating agent workflow: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "AGENT_CREATION_FAILED",
                "message": "代理创建失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持",
            },
        )

def _normalize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


@router.get("/agents/{task_id}/status", response_model=TaskStatusResponse)
async def get_agent_status(task_id: str = Path(..., description="Celery任务ID")):
    """查询异步构建任务状态。"""
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        status = async_result.state.lower()

        result_payload: Optional[Dict[str, Any]] = None
        error_message = None

        if async_result.successful():
            task_result = async_result.result or {}
            if isinstance(task_result, dict):
                result_payload = task_result
        elif async_result.failed():
            error_message = str(async_result.result)

        project_id = None
        if isinstance(result_payload, dict):
            project_id = result_payload.get("project_id")
        project_id = project_id or task_id

        # Enrich with latest stage snapshot from DynamoDB if available.
        project_item = None
        try:
            project_item = (
                DynamoDBClient()
                .projects_table
                .get_item(Key={"project_id": project_id})
                .get("Item")
            )
        except Exception:
            project_item = None

        if project_item:
            snapshot = _normalize(project_item.get("stages_snapshot"))
            progress = project_item.get("progress_percentage", 0)
            project_status = project_item.get("status")
            if result_payload is None:
                result_payload = {}
            if snapshot:
                result_payload["stages_snapshot"] = snapshot
            result_payload["progress_percentage"] = (
                float(progress) if isinstance(progress, (Decimal, int, float)) else 0.0
            )
            result_payload["project_status"] = project_status
            result_payload.setdefault("project_id", project_id)

        status_data = TaskStatusData(
            task_id=task_id,
            status=status,
            result=result_payload,
            error=error_message,
            date_done=async_result.date_done,
        )

        return TaskStatusResponse(
            success=True,
            data=status_data,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4()),
        )

    except Exception as e:
        logger.error("Error querying task status: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "STATUS_QUERY_FAILED",
                "message": "任务状态查询失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持",
            },
        )

@router.get("/agents/{project_id}/stages", response_model=StagesResponse)
async def get_build_stages(
    project_id: str = Path(..., description="项目ID")
):
    """
    查询构建阶段详情
    
    返回所有8个构建阶段的详细状态信息
    """
    try:
        db_client = DynamoDBClient()

        project_data = db_client.get_project(project_id)
        if not project_data:
            raise ResourceNotFoundError("Project", project_id)

        snapshot = project_data.get("stages_snapshot") or {}
        stages = snapshot.get("stages", [])
        normalized_stages = []

        for stage in stages:
            normalized_stage = {
                "name": stage.get("name"),
                "display_name": stage.get("display_name"),
                "order": stage.get("order"),
                "status": stage.get("status"),
                "started_at": stage.get("started_at"),
                "completed_at": stage.get("completed_at"),
                "error": stage.get("error"),
            }
            normalized_stages.append(normalized_stage)

        response_data = {
            "project_id": project_id,
            "total_stages": snapshot.get("total", len(normalized_stages)),
            "completed_stages": snapshot.get("completed", 0),
            "stages": normalized_stages,
            "overall_progress": project_data.get("progress_percentage", 0.0),
        }

        return StagesResponse(
            success=True,
            data=response_data,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4()),
        )

    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在",
                "details": "请检查项目ID是否正确",
                "suggestion": "使用有效的项目ID或创建新项目"
            }
        )
    except Exception as e:
        logger.error(f"Error getting project stages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "STAGES_QUERY_FAILED",
                "message": "阶段查询失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )

@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    category: Optional[str] = Query(None, description="类别过滤"),
    user_id: Optional[str] = Query(None, description="用户过滤"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    列出所有代理
    
    支持分页、过滤和搜索功能
    """
    try:
        # Import dependencies
        from api.models.schemas import AgentListData, AgentSummary, AgentStatus
        
        # Initialize database client
        db_client = DynamoDBClient()
        
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Get agents based on filters
        agents_data = []
        total_count = 0
        
        if user_id:
            # Filter by user - get projects first, then agents
            projects_result = db_client.list_projects_by_user(user_id, limit=1000)
            project_ids = [p['project_id'] for p in projects_result.get('items', [])]
            
            # Get agents for these projects
            for project_id in project_ids:
                try:
                    agents = db_client.list_agents_by_project(project_id)
                    agents_data.extend(agents)
                except Exception:
                    continue  # Skip if project has no agents
        else:
            # Get all agents (this would need a scan operation in real implementation)
            # For now, we'll return empty results as this requires more complex querying
            pass
        
        # Apply additional filters
        if status:
            try:
                status_enum = AgentStatus(status)
                agents_data = [a for a in agents_data if a.get('status') == status_enum.value]
            except ValueError:
                # Invalid status, return empty results
                agents_data = []
        
        if category:
            agents_data = [a for a in agents_data if a.get('category') == category]
        
        if search:
            search_lower = search.lower()
            agents_data = [
                a for a in agents_data 
                if (search_lower in a.get('agent_name', '').lower() or 
                    search_lower in a.get('description', '').lower())
            ]
        
        # Apply pagination
        total_count = len(agents_data)
        paginated_agents = agents_data[offset:offset + limit]
        
        # Convert to AgentSummary objects
        agent_summaries = []
        for agent_data in paginated_agents:
            try:
                # Parse timestamps
                created_at = datetime.now(timezone.utc)
                if agent_data.get('created_at'):
                    try:
                        created_at = datetime.fromisoformat(agent_data['created_at'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
                
                # Create agent summary
                agent_summary = AgentSummary(
                    agent_id=agent_data.get('agent_id', ''),
                    project_id=agent_data.get('project_id', ''),
                    agent_name=agent_data.get('agent_name', ''),
                    category=agent_data.get('category'),
                    status=AgentStatus(agent_data.get('status', 'offline')),
                    version=agent_data.get('version', 'v1.0.0'),
                    created_at=created_at,
                    call_count=agent_data.get('call_count', 0),
                    success_rate=agent_data.get('success_rate', 0.0)
                )
                agent_summaries.append(agent_summary)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid agent data: {str(e)}")
                continue
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        # Create response data
        list_data = AgentListData(
            agents=agent_summaries,
            pagination={
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )
        
        return AgentListResponse(
            success=True,
            data=list_data,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "AGENT_LIST_FAILED",
                "message": "代理列表查询失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )

@router.get("/agents/{agent_id}", response_model=AgentDetailsResponse)
async def get_agent_details(
    agent_id: str = Path(..., description="代理ID")
):
    """
    获取代理详细信息
    
    返回代理的完整配置和运行时统计信息
    """
    try:
        # Import dependencies
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import AgentDetails, AgentStatus
        
        # Initialize database client
        db_client = DynamoDBClient()
        
        # Get agent from database
        agent_data = db_client.get_agent(agent_id)
        
        if not agent_data:
            raise ResourceNotFoundError("Agent", agent_id)
        
        # Parse timestamps
        created_at = datetime.now(timezone.utc)
        last_called_at = None
        
        if agent_data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(agent_data['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        if agent_data.get('last_called_at'):
            try:
                last_called_at = datetime.fromisoformat(agent_data['last_called_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Parse lists
        dependencies = agent_data.get('dependencies', [])
        if isinstance(dependencies, str):
            try:
                import json
                dependencies = json.loads(dependencies)
            except json.JSONDecodeError:
                dependencies = [dependencies]
        
        supported_models = agent_data.get('supported_models', [])
        if isinstance(supported_models, str):
            try:
                import json
                supported_models = json.loads(supported_models)
            except json.JSONDecodeError:
                supported_models = [supported_models]
        
        tags = agent_data.get('tags', [])
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = [tags]
        
        # Create agent details
        agent_details = AgentDetails(
            agent_id=agent_id,
            project_id=agent_data.get('project_id', ''),
            agent_name=agent_data.get('agent_name', ''),
            description=agent_data.get('description'),
            category=agent_data.get('category'),
            version=agent_data.get('version', 'v1.0.0'),
            status=AgentStatus(agent_data.get('status', 'offline')),
            script_path=agent_data.get('script_path'),
            prompt_path=agent_data.get('prompt_path'),
            tools_count=agent_data.get('tools_count', 0),
            dependencies=dependencies,
            supported_models=supported_models,
            tags=tags,
            call_count=agent_data.get('call_count', 0),
            success_rate=agent_data.get('success_rate', 0.0),
            last_called_at=last_called_at,
            created_at=created_at
        )
        
        return AgentDetailsResponse(
            success=True,
            data=agent_details,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )
        
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "AGENT_NOT_FOUND",
                "message": f"代理 {agent_id} 不存在",
                "details": "请检查代理ID是否正确",
                "suggestion": "使用有效的代理ID或查看代理列表"
            }
        )
    except Exception as e:
        logger.error(f"Error getting agent details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "AGENT_DETAILS_FAILED",
                "message": "代理详情查询失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )

@router.post("/agents/{project_id}/pause", response_model=APIResponse)
async def pause_build(
    project_id: str = Path(..., description="项目ID"),
    request: BuildControlRequest = None
):
    """暂停构建任务"""
    try:
        # Import dependencies
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import ProjectStatus
        
        # Initialize database client
        db_client = DynamoDBClient()
        
        # Check if project exists
        project_data = db_client.get_project(project_id)
        if not project_data:
            raise ResourceNotFoundError("Project", project_id)
        
        # Check current project status
        current_status = project_data.get('status')
        if current_status not in ['building', 'running']:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_PROJECT_STATE",
                    "message": f"项目当前状态为 {current_status}，无法暂停",
                    "details": "只有正在构建或运行中的项目才能暂停",
                    "suggestion": "请检查项目状态后重试"
                }
            )
        
        # Update project status to paused
        db_client.update_project_status(
            project_id,
            ProjectStatus.PAUSED,
            updated_at=datetime.now(timezone.utc)
        )
        
        # Log the pause action
        reason = request.reason if request else "用户手动暂停"
        logger.info(f"Project {project_id} paused. Reason: {reason}")
        
        return APIResponse(
            success=True,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在",
                "details": "请检查项目ID是否正确",
                "suggestion": "使用有效的项目ID"
            }
        )
    except Exception as e:
        logger.error(f"Error pausing build for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PAUSE_FAILED",
                "message": "暂停构建失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )

@router.post("/agents/{project_id}/resume", response_model=APIResponse)
async def resume_build(
    project_id: str = Path(..., description="项目ID"),
    request: BuildControlRequest = None
):
    """恢复构建任务"""
    try:
        # Import dependencies
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import ProjectStatus
        
        # Initialize database client
        db_client = DynamoDBClient()
        
        # Check if project exists
        project_data = db_client.get_project(project_id)
        if not project_data:
            raise ResourceNotFoundError("Project", project_id)
        
        # Check current project status
        current_status = project_data.get('status')
        if current_status != 'paused':
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_PROJECT_STATE",
                    "message": f"项目当前状态为 {current_status}，无法恢复",
                    "details": "只有暂停状态的项目才能恢复",
                    "suggestion": "请检查项目状态后重试"
                }
            )
        
        # Update project status to building
        db_client.update_project_status(
            project_id,
            ProjectStatus.BUILDING,
            updated_at=datetime.now(timezone.utc)
        )
        
        # Log the resume action
        reason = request.reason if request else "用户手动恢复"
        logger.info(f"Project {project_id} resumed. Reason: {reason}")
        
        # TODO: In a real implementation, we would restart the workflow engine
        # For now, we just update the status
        
        return APIResponse(
            success=True,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在",
                "details": "请检查项目ID是否正确",
                "suggestion": "使用有效的项目ID"
            }
        )
    except Exception as e:
        logger.error(f"Error resuming build for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RESUME_FAILED",
                "message": "恢复构建失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )

@router.post("/agents/{project_id}/stop", response_model=APIResponse)
async def stop_build(
    project_id: str = Path(..., description="项目ID"),
    request: BuildControlRequest = None
):
    """停止构建任务"""
    try:
        # Import dependencies
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import ProjectStatus
        
        # Initialize database client
        db_client = DynamoDBClient()
        
        # Check if project exists
        project_data = db_client.get_project(project_id)
        if not project_data:
            raise ResourceNotFoundError("Project", project_id)
        
        # Check current project status
        current_status = project_data.get('status')
        if current_status in ['completed', 'failed', 'stopped']:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_PROJECT_STATE",
                    "message": f"项目当前状态为 {current_status}，无法停止",
                    "details": "项目已经处于终止状态",
                    "suggestion": "请检查项目状态"
                }
            )
        
        # Update project status to failed (stopped)
        stop_reason = request.reason if request else "用户手动停止"
        db_client.update_project_status(
            project_id,
            ProjectStatus.FAILED,
            updated_at=datetime.now(timezone.utc),
            error_info={
                "type": "user_stopped",
                "reason": stop_reason,
                "stopped_at": datetime.now(timezone.utc).isoformat() + "Z"
            }
        )
        
        # Log the stop action
        logger.info(f"Project {project_id} stopped. Reason: {stop_reason}")
        
        # TODO: In a real implementation, we would:
        # 1. Cancel any running Celery tasks
        # 2. Clean up resources
        # 3. Update all pending stages to cancelled
        
        return APIResponse(
            success=True,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在",
                "details": "请检查项目ID是否正确",
                "suggestion": "使用有效的项目ID"
            }
        )
    except Exception as e:
        logger.error(f"Error stopping build for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "STOP_FAILED",
                "message": "停止构建失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )

@router.post("/agents/{project_id}/restart", response_model=APIResponse)
async def restart_build(
    project_id: str = Path(..., description="项目ID"),
    request: BuildControlRequest = None
):
    """重新开始构建任务"""
    try:
        # Import dependencies
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import ProjectStatus, StageStatus, BuildStage, get_all_stages
        from api.tasks.agent_build_tasks import build_agent
        
        # Initialize database client
        db_client = DynamoDBClient()
        
        # Check if project exists
        project_data = db_client.get_project(project_id)
        if not project_data:
            raise ResourceNotFoundError("Project", project_id)
        
        # Check current project status
        current_status = project_data.get('status')
        if current_status == 'building':
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_PROJECT_STATE",
                    "message": f"项目当前状态为 {current_status}，无法重启",
                    "details": "正在构建中的项目无法重启，请先停止后再重启",
                    "suggestion": "请先停止项目，然后重新启动"
                }
            )
        
        # Reset project status and progress
        db_client.update_project_status(
            project_id,
            ProjectStatus.BUILDING,
            progress_percentage=0.0,
            current_stage=BuildStage.REQUIREMENTS_ANALYSIS,
            current_stage_number=1,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            error_info=None
        )
        
        # Reset all stage statuses to pending
        for stage in get_all_stages():
            stage_number = BuildStage.get_stage_number(stage)
            db_client.update_stage_status(
                project_id,
                stage_number,
                StageStatus.PENDING,
                started_at=None,
                completed_at=None,
                duration_seconds=None,
                output_data=None,
                error_message=None,
                logs=[]
            )
        
        # Start new build task
        task = build_agent.delay(
            project_id=project_id,
            requirement=project_data.get('original_requirement', ''),
            user_id=project_data.get('user_id', ''),
            user_name=project_data.get('user_name'),
            priority=project_data.get('priority', 3),
            tags=project_data.get('tags', [])
        )
        
        # Log the restart action
        restart_reason = request.reason if request else "用户手动重启"
        logger.info(f"Project {project_id} restarted. Reason: {restart_reason}. New task ID: {task.id}")
        
        return APIResponse(
            success=True,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": f"项目 {project_id} 不存在",
                "details": "请检查项目ID是否正确",
                "suggestion": "使用有效的项目ID"
            }
        )
    except Exception as e:
        logger.error(f"Error restarting build for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RESTART_FAILED",
                "message": "重启构建失败",
                "details": str(e),
                "suggestion": "请稍后重试或联系技术支持"
            }
        )
