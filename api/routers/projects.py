"""
Projects API endpoints

提供项目管理的RESTful API，包括创建、查询、控制和删除项目
"""
from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timezone

from api.models.schemas import (
    APIResponse,
    ProjectStatus,
    BuildStage,
)
from api.core.exceptions import APIException, ResourceNotFoundError, ValidationError
from api.services import (
    ProjectService,
    project_service,
    StageService,
    stage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/stages")
async def list_project_stages(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取项目的所有阶段信息

    返回包含所有6个阶段的完整信息，包括子阶段、日志、输出数据等

    Requirements: 7.5
    """
    try:
        stages = stage_service.list_stages(project_id)

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "stages": stages,
                "total_stages": len(stages)
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list stages for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list stages: {str(e)}")


@router.get("/projects/{project_id}/stages/{stage_name}")
async def get_project_stage(
    project_id: str = Path(..., description="项目ID"),
    stage_name: str = Path(..., description="阶段名称")
):
    """
    获取项目特定阶段的详细信息

    返回指定阶段的详细信息，包括子阶段、日志、输出数据、错误信息等

    Requirements: 7.5
    """
    try:
        stage = stage_service.get_stage(project_id, stage_name)

        return {
            "success": True,
            "data": stage,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get stage {stage_name} for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stage: {str(e)}")


@router.post("/projects")
async def create_project(
    requirement: str = Body(..., description="项目需求描述"),
    user_id: Optional[str] = Body(None, description="用户ID"),
    project_name: Optional[str] = Body(None, description="项目名称"),
    agent_name_map: Optional[Dict[str, str]] = Body(None, description="Agent名称映射")
):
    """
    创建新项目

    根据用户需求创建新的项目，并自动初始化6个构建阶段

    Requirements: 3.1
    """
    try:
        # 生成项目ID
        import uuid
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        # 转换agent_name_map (如果提供)
        converted_agent_map = None
        if agent_name_map:
            converted_agent_map = {
                BuildStage(k): v for k, v in agent_name_map.items()
            }

        # 创建项目
        project = project_service.create_project(
            project_id=project_id,
            requirement=requirement,
            user_id=user_id,
            project_name=project_name,
            agent_name_map=converted_agent_map
        )

        # 触发异步构建任务
        from api.tasks.agent_build_tasks import build_agent
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        build_agent.delay(
            project_id=project_id,
            requirement=requirement,
            session_id=session_id,
            user_id=user_id,
            agent_name=project_name
        )

        logger.info(f"Triggered build task for project {project_id} with session {session_id}")

        return {
            "success": True,
            "data": project,
            "message": f"Project {project_id} created successfully and build started",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects")
async def list_projects(
    user_id: Optional[str] = Query(None, description="按用户ID过滤"),
    status: Optional[ProjectStatus] = Query(None, description="按状态过滤"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    last_key: Optional[str] = Query(None, description="分页游标")
):
    """
    获取项目列表

    支持按用户ID、状态过滤，支持分页

    Requirements: 3.3
    """
    try:
        result = project_service.list_projects(
            user_id=user_id,
            status=status,
            limit=limit,
            last_key=last_key
        )

        return {
            "success": True,
            "data": {
                "items": result["items"],
                "last_evaluated_key": result.get("last_evaluated_key"),
                "count": len(result["items"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except Exception as e:
        logger.error(f"Failed to list projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取项目详情

    返回完整的项目信息，包括阶段快照（stages_snapshot）

    Requirements: 3.2
    """
    try:
        project = project_service.get_project(project_id)

        return {
            "success": True,
            "data": project,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/projects/{project_id}/control")
async def control_project(
    project_id: str = Path(..., description="项目ID"),
    action: str = Body(..., description="操作：pause, resume, stop, restart"),
    reason: Optional[str] = Body(None, description="操作原因")
):
    """
    控制项目（暂停/恢复/停止/重启）

    支持的操作:
    - pause: 暂停构建
    - resume: 恢复构建
    - stop: 停止构建
    - restart: 重新开始构建

    Requirements: 3.4
    """
    try:
        project_service.control_project(project_id, action, reason)

        return {
            "success": True,
            "message": f"Project {project_id} {action} successfully",
            "data": {
                "project_id": project_id,
                "action": action,
                "reason": reason
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to control project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to control project: {str(e)}")


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str = Path(..., description="项目ID")
):
    """
    删除项目

    级联删除项目及其所有关联数据：
    - 项目记录
    - 关联的所有agents
    - 所有invocations（通过删除agents级联）
    - 所有sessions和messages（通过删除agents级联）

    Requirements: 3.5, 10.3
    """
    try:
        project_service.delete_project(project_id)

        return {
            "success": True,
            "message": f"Project {project_id} deleted successfully",
            "data": {
                "project_id": project_id,
                "deleted_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")
