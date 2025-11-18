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
    BuildDashboardResponse,
    ProjectListResponse,
    ProjectListData,
    ProjectListItem,
    ProjectStatus,
)
from api.core.exceptions import ValidationError, ResourceNotFoundError
from celery.result import AsyncResult

from api.core.celery_app import celery_app
from api.database.dynamodb_client import DynamoDBClient
from api.tasks.agent_build_tasks import build_agent
from api.models.schemas import TaskStatusResponse, TaskStatusData
from api.services import BuildDashboardService
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

        derived_agent_name = _derive_agent_name(request.agent_name, request.requirement, project_id)

        initialize_project_record(
            project_id,
            requirement=request.requirement,
            user_id=request.user_id,
            user_name=request.user_name,
            project_name=derived_agent_name,
            tags=request.tags,
        )

        task = build_agent.delay(
            project_id=project_id,
            requirement=request.requirement,
            session_id=session_id,
            user_id=request.user_id,
            user_name=request.user_name,
            agent_name=derived_agent_name,
        )

        return CreateAgentResponse(
            success=True,
            data={
                "task_id": task.id,
                "session_id": session_id,
                "project_id": project_id,
                "agent_name": derived_agent_name,
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


def _derive_agent_name(provided: Optional[str], requirement: str, project_id: str) -> Optional[str]:
    if provided and provided.strip():
        name = provided.strip()
        if not name.startswith("job_"):
            return name

    candidate = requirement.strip().splitlines()[0].strip() if requirement else ""
    if candidate and not candidate.startswith("job_"):
        if len(candidate) > 80:
            candidate = candidate[:77].rstrip() + "…"
        return candidate

    return f"构建任务 {project_id[-6:]}"


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


@router.get("/projects/{project_id}/build", response_model=BuildDashboardResponse)
async def get_project_build_dashboard(
    project_id: str = Path(..., description="项目ID"),
):
    """聚合项目构建进度、阶段与最新任务信息。"""
    service = BuildDashboardService()
    try:
        dashboard = service.get_build_dashboard(project_id)
        return BuildDashboardResponse(
            success=True,
            data=dashboard,
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
                "suggestion": "使用有效的项目ID或创建新项目",
            },
        )
    except Exception as exc:
        logger.error("Error building dashboard for project %s: %s", project_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "BUILD_DASHBOARD_FAILED",
                "message": "构建进度查询失败",
                "details": str(exc),
                "suggestion": "请稍后重试或联系技术支持",
            },
        )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=500, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    user_id: Optional[str] = Query(None, description="用户过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
):
    """列表构建项目记录。"""

    try:
        db_client = DynamoDBClient()

        filters: Dict[str, Any] = {}

        if status:
            try:
                filters['status'] = ProjectStatus(status)
            except ValueError:
                return ProjectListResponse(
                    success=True,
                    data=ProjectListData(
                        projects=[],
                        pagination={
                            "page": page,
                            "limit": limit,
                            "total": 0,
                            "pages": 0,
                            "has_next": False,
                            "has_prev": page > 1,
                        },
                    ),
                    timestamp=datetime.now(timezone.utc),
                    request_id=str(uuid.uuid4()),
                )

        if user_id:
            filters['user_id'] = user_id

        if search:
            filters['search'] = search

        projects_batch: List[Dict[str, Any]] = []
        has_next = False
        last_key: Optional[str] = None

        for current_page in range(1, page + 1):
            result = db_client.list_projects(limit=limit, last_key=last_key, filters=filters)
            batch = result.get('items', [])
            last_key = result.get('last_key')

            if current_page == page:
                projects_batch = batch
                has_next = bool(last_key)

            if not last_key:
                if current_page < page:
                    projects_batch = []
                break

        approx_total = (page - 1) * limit + len(projects_batch)
        if has_next:
            approx_total += 1
        total_pages = max(page, (approx_total + limit - 1) // limit) if approx_total else page

        def _parse_datetime(value: Any) -> Optional[datetime]:
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, (int, float)):
                try:
                    return datetime.fromtimestamp(value, tz=timezone.utc)
                except (OverflowError, ValueError):
                    return None
            if isinstance(value, str):
                try:
                    normalized = value.replace('Z', '+00:00') if value.endswith('Z') else value
                    return datetime.fromisoformat(normalized)
                except ValueError:
                    return None
            return None

        def _as_float(value: Any) -> float:
            if value is None:
                return 0.0
            if isinstance(value, Decimal):
                return float(value)
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(str(value))
            except (TypeError, ValueError):
                return 0.0

        def _as_int(value: Any) -> int:
            if value is None:
                return 0
            if isinstance(value, Decimal):
                return int(value)
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            try:
                return int(float(str(value)))
            except (TypeError, ValueError):
                return 0

        def _normalize_tags(value: Any) -> List[str]:
            if value is None:
                return []
            if isinstance(value, list):
                return [str(item) for item in value]
            return [str(value)]

        project_items: List[ProjectListItem] = []
        for project in projects_batch:
            project_id = str(project.get('project_id', ''))
            if not project_id:
                continue

            status_value = project.get('status') or ProjectStatus.BUILDING.value
            try:
                project_status = ProjectStatus(status_value)
            except ValueError:
                project_status = ProjectStatus.BUILDING

            progress = _as_float(project.get('progress_percentage'))
            progress = max(0.0, min(100.0, progress))

            current_stage = project.get('current_stage')
            if not current_stage:
                snapshot = project.get('stages_snapshot') or {}
                stages_info = snapshot.get('stages') or []
                running_stage = next((stage for stage in stages_info if stage.get('status') == 'running'), None)
                pending_stage = next((stage for stage in stages_info if stage.get('status') == 'pending'), None)
                if running_stage:
                    current_stage = running_stage.get('name')
                elif pending_stage:
                    current_stage = pending_stage.get('name')

            project_items.append(
                ProjectListItem(
                    project_id=project_id,
                    project_name=project.get('project_name'),
                    status=project_status,
                    progress_percentage=progress,
                    current_stage=current_stage,
                    updated_at=_parse_datetime(project.get('updated_at')),
                    created_at=_parse_datetime(project.get('created_at')),
                    user_id=project.get('user_id'),
                    user_name=project.get('user_name'),
                    agent_count=_as_int(project.get('agent_count')),
                    tags=_normalize_tags(project.get('tags')),
                )
            )

        list_data = ProjectListData(
            projects=project_items,
            pagination={
                "page": page,
                "limit": limit,
                "total": approx_total,
                "pages": total_pages,
                "has_next": has_next,
                "has_prev": page > 1,
            },
        )

        return ProjectListResponse(
            success=True,
            data=list_data,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4()),
        )

    except Exception as exc:
        logger.error("Error listing projects: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PROJECT_LIST_FAILED",
                "message": "项目列表查询失败",
                "details": str(exc),
                "suggestion": "请稍后重试或联系技术支持",
            },
        )


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=500, description="每页数量"),
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

        filters: Dict[str, Any] = {}

        if status:
            try:
                filters['status'] = AgentStatus(status)
            except ValueError:
                return AgentListResponse(
                    success=True,
                    data=AgentListData(
                        agents=[],
                        pagination={
                            "page": page,
                            "limit": limit,
                            "total": 0,
                            "pages": 0,
                            "has_next": False,
                            "has_prev": page > 1,
                        },
                    ),
                    timestamp=datetime.now(timezone.utc),
                    request_id=str(uuid.uuid4()),
                )

        if category:
            filters['category'] = category

        if search:
            filters['search'] = search

        agents_data: List[Dict[str, Any]] = []
        paginated_agents: List[Dict[str, Any]] = []
        total_count = 0
        has_next = False

        if user_id:
            projects_result = db_client.list_projects_by_user(user_id, limit=1000)
            project_ids = [p['project_id'] for p in projects_result.get('items', [])]

            for project_id in project_ids:
                try:
                    agents = db_client.list_agents_by_project(project_id)
                    agents_data.extend(agents)
                except Exception:
                    continue

            status_filter = filters.get('status')
            if status_filter:
                target_status = status_filter.value if isinstance(status_filter, AgentStatus) else status_filter
                agents_data = [a for a in agents_data if a.get('status') == target_status]

            category_filter = filters.get('category')
            if category_filter:
                agents_data = [a for a in agents_data if a.get('category') == category_filter]

            search_filter = str(filters.get('search', '')).lower()
            if search_filter:
                agents_data = [
                    a for a in agents_data
                    if search_filter in str(a.get('agent_name', '')).lower()
                    or search_filter in str(a.get('description', '')).lower()
                    or search_filter in str(a.get('project_id', '')).lower()
                ]

            total_count = len(agents_data)
            start = max(0, (page - 1) * limit)
            paginated_agents = agents_data[start:start + limit]
            has_next = total_count > start + len(paginated_agents)
        else:
            last_key: Optional[str] = None
            fetched_items: List[Dict[str, Any]] = []

            for current_page in range(1, page + 1):
                scan_result = db_client.list_agents(
                    limit=limit,
                    last_key=last_key,
                    filters=filters,
                )
                batch = scan_result.get('items', [])
                last_key = scan_result.get('last_key')

                if current_page == page:
                    fetched_items = batch
                    has_next = bool(last_key)

                if not last_key:
                    if current_page < page:
                        fetched_items = []
                    break

            paginated_agents = fetched_items
            total_count = (page - 1) * limit + len(paginated_agents)
            if has_next:
                total_count += 1
        
        # Convert to AgentSummary objects
        agent_summaries = []
        for agent_data in paginated_agents:
            try:
                # Parse timestamps
                created_at = datetime.now(timezone.utc)
                if agent_data.get('created_at'):
                    try:
                        ca = agent_data['created_at']
                        if isinstance(ca, datetime):
                            created_at = ca
                        elif isinstance(ca, str):
                            created_at = datetime.fromisoformat(ca.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass

                # Create agent summary
                raw_status = agent_data.get('status', 'offline')
                try:
                    agent_status = AgentStatus(raw_status)
                except ValueError:
                    agent_status = AgentStatus.BUILDING if raw_status == 'building' else AgentStatus.OFFLINE

                # Handle call_count and success_rate - ensure they are numbers
                call_count = agent_data.get('call_count', 0)
                if isinstance(call_count, str):
                    try:
                        call_count = int(call_count)
                    except (ValueError, TypeError):
                        call_count = 0
                
                success_rate = agent_data.get('success_rate', 0.0)
                if isinstance(success_rate, str):
                    try:
                        success_rate = float(success_rate)
                    except (ValueError, TypeError):
                        success_rate = 0.0

                agent_summary = AgentSummary(
                    agent_id=agent_data.get('agent_id', ''),
                    project_id=agent_data.get('project_id', ''),
                    agent_name=agent_data.get('agent_name', ''),
                    category=agent_data.get('category'),
                    status=agent_status,
                    version=agent_data.get('version', 'v1.0.0'),
                    created_at=created_at,
                    call_count=call_count,
                    success_rate=success_rate
                )
                agent_summaries.append(agent_summary)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid agent data: {str(e)}")
                continue
        
        approx_total = max(total_count, (page - 1) * limit + len(paginated_agents))
        total_pages = max(page, (approx_total + limit - 1) // limit) if approx_total else page
        
        # Create response data
        list_data = AgentListData(
            agents=agent_summaries,
            pagination={
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": total_pages,
                "has_next": has_next,
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
                ca = agent_data['created_at']
                if isinstance(ca, datetime):
                    created_at = ca
                elif isinstance(ca, str):
                    created_at = datetime.fromisoformat(ca.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        if agent_data.get('last_called_at'):
            try:
                lca = agent_data['last_called_at']
                if isinstance(lca, datetime):
                    last_called_at = lca
                elif isinstance(lca, str):
                    last_called_at = datetime.fromisoformat(lca.replace('Z', '+00:00'))
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
        
        # Handle call_count and success_rate - ensure they are numbers
        call_count = agent_data.get('call_count', 0)
        if isinstance(call_count, str):
            try:
                call_count = int(call_count)
            except (ValueError, TypeError):
                call_count = 0
        
        success_rate = agent_data.get('success_rate', 0.0)
        if isinstance(success_rate, str):
            try:
                success_rate = float(success_rate)
            except (ValueError, TypeError):
                success_rate = 0.0
        
        tools_count = agent_data.get('tools_count', 0)
        if isinstance(tools_count, str):
            try:
                tools_count = int(tools_count)
            except (ValueError, TypeError):
                tools_count = 0
        
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
            tools_count=tools_count,
            dependencies=dependencies,
            supported_models=supported_models,
            tags=tags,
            call_count=call_count,
            success_rate=success_rate,
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
