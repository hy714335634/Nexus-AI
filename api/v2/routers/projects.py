"""
Projects API Router

项目管理相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
import logging
from datetime import datetime, timezone
import uuid
import os
import json
import yaml

from api.v2.models.schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectControlRequest,
    BuildDashboardResponse,
    StageListResponse,
    APIResponse,
)
from api.v2.services import project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])

# 项目目录路径
def _get_projects_dir() -> str:
    from pathlib import Path as PathLib
    current_file = PathLib(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent
    return str(project_root / "projects")


def _get_tools_dir() -> str:
    """获取工具生成目录路径"""
    from pathlib import Path as PathLib
    current_file = PathLib(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent
    return str(project_root / "tools" / "generated_tools")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


@router.post("", response_model=CreateProjectResponse)
async def create_project(request: CreateProjectRequest):
    """
    创建新项目
    
    接收需求描述，创建项目并提交构建任务到队列
    """
    try:
        result = project_service.create_project(request)
        
        return CreateProjectResponse(
            success=True,
            message="项目创建成功",
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[str] = Query(None, description="按状态筛选"),
    user_id: Optional[str] = Query(None, description="按用户筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取项目列表
    """
    try:
        result = project_service.list_projects(
            status=status,
            user_id=user_id,
            page=page,
            limit=limit
        )
        
        return ProjectListResponse(
            success=True,
            data=result.get('items', []),
            pagination=result.get('pagination'),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取项目详情
    """
    try:
        project = project_service.get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
        
        return ProjectDetailResponse(
            success=True,
            data=project,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目详情失败: {str(e)}")


@router.get("/{project_id}/build", response_model=BuildDashboardResponse)
async def get_build_dashboard(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取构建仪表板数据
    
    返回项目的构建进度、阶段状态、指标等信息
    """
    try:
        dashboard = project_service.get_build_dashboard(project_id)
        
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
        
        return BuildDashboardResponse(
            success=True,
            data=dashboard,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get build dashboard for {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取构建仪表板失败: {str(e)}")


@router.get("/{project_id}/stages", response_model=StageListResponse)
async def list_project_stages(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取项目的所有阶段信息
    """
    try:
        project = project_service.get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
        
        stages = project.get('stages', [])
        
        return StageListResponse(
            success=True,
            data=stages,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list stages for {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取阶段列表失败: {str(e)}")


@router.post("/{project_id}/control", response_model=APIResponse)
async def control_project(
    project_id: str = Path(..., description="项目ID"),
    request: ProjectControlRequest = None
):
    """
    控制项目状态
    
    支持的操作:
    - pause: 暂停构建
    - resume: 恢复构建
    - stop: 停止构建
    - cancel: 取消构建
    """
    try:
        result = project_service.control_project(
            project_id=project_id,
            action=request.action,
            reason=request.reason
        )
        
        return APIResponse(
            success=True,
            message=result.get('message'),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to control project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"控制项目失败: {str(e)}")


@router.delete("/{project_id}", response_model=APIResponse)
async def delete_project(
    project_id: str = Path(..., description="项目ID")
):
    """
    删除项目
    
    会同时删除关联的阶段数据
    """
    try:
        success = project_service.delete_project(project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
        
        return APIResponse(
            success=True,
            message="项目删除成功",
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


# ============== 项目文件相关端点 ==============

@router.get("/{project_id}/files", response_model=APIResponse)
async def list_project_files(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取项目目录下的所有文件列表
    """
    try:
        projects_dir = _get_projects_dir()
        project_path = os.path.join(projects_dir, project_id)
        
        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail=f"项目目录 {project_id} 不存在")
        
        files = []
        for root, dirs, filenames in os.walk(project_path):
            # 跳过 __pycache__ 目录
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                    
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, project_path)
                stat = os.stat(filepath)
                
                # 确定文件类型
                file_type = 'unknown'
                if filename.endswith(('.yaml', '.yml')):
                    file_type = 'yaml'
                elif filename.endswith('.json'):
                    file_type = 'json'
                elif filename.endswith('.md'):
                    file_type = 'markdown'
                elif filename.endswith('.py'):
                    file_type = 'python'
                elif filename.endswith('.txt'):
                    file_type = 'text'
                
                files.append({
                    'name': filename,
                    'path': rel_path,
                    'size': stat.st_size,
                    'type': file_type,
                    'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                })
        
        return APIResponse(
            success=True,
            data={'files': files, 'project_path': project_path},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list project files for {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目文件列表失败: {str(e)}")


@router.get("/{project_id}/files/{file_path:path}", response_model=APIResponse)
async def get_project_file(
    project_id: str = Path(..., description="项目ID"),
    file_path: str = Path(..., description="文件路径")
):
    """
    获取项目文件内容
    """
    try:
        projects_dir = _get_projects_dir()
        project_path = os.path.join(projects_dir, project_id)
        filepath = os.path.join(project_path, file_path)
        
        # 安全检查
        real_path = os.path.realpath(filepath)
        real_project_path = os.path.realpath(project_path)
        if not real_path.startswith(real_project_path):
            raise HTTPException(status_code=400, detail="非法的文件路径")
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"文件 {file_path} 不存在")
        
        # 读取文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试解析结构化内容
        parsed_content = None
        file_type = 'text'
        
        if file_path.endswith(('.yaml', '.yml')):
            file_type = 'yaml'
            try:
                parsed_content = yaml.safe_load(content)
            except:
                pass
        elif file_path.endswith('.json'):
            file_type = 'json'
            try:
                parsed_content = json.loads(content)
            except:
                pass
        elif file_path.endswith('.md'):
            file_type = 'markdown'
        elif file_path.endswith('.py'):
            file_type = 'python'
        
        return APIResponse(
            success=True,
            data={
                'filename': os.path.basename(file_path),
                'path': file_path,
                'type': file_type,
                'content': content,
                'parsed_content': parsed_content
            },
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project file {file_path} for {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目文件失败: {str(e)}")


@router.get("/{project_id}/workflow-report", response_model=APIResponse)
async def get_workflow_report(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取项目的 workflow 报告
    """
    try:
        projects_dir = _get_projects_dir()
        report_path = os.path.join(projects_dir, project_id, 'workflow_summary_report.md')
        
        if not os.path.exists(report_path):
            return APIResponse(
                success=True,
                data={'exists': False, 'content': None},
                timestamp=_now(),
                request_id=_request_id()
            )
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return APIResponse(
            success=True,
            data={
                'exists': True,
                'content': content,
                'path': 'workflow_summary_report.md'
            },
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get workflow report for {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 workflow 报告失败: {str(e)}")


# BuildStage 枚举值到实际文件名的映射
STAGE_NAME_TO_FILE_NAME = {
    "orchestrator": "orchestrator",
    "requirements_analysis": "requirements_analyzer",
    "system_architecture": "system_architect",
    "agent_design": "agent_designer",
    "prompt_engineer": "prompt_engineer",
    "tools_developer": "tools_developer",
    "agent_code_developer": "agent_code_developer",
    "agent_developer_manager": "agent_developer_manager",
    "agent_deployer": "agent_deployer",
}


def _try_extract_json_from_raw_content(raw_content: str) -> Optional[dict]:
    """
    尝试从 raw_content 中提取 JSON 数据
    
    当数据库中的 output_data 只包含 raw_content 时，
    尝试从中提取有效的 JSON 结构。
    
    Args:
        raw_content: 原始内容字符串
        
    Returns:
        提取到的 JSON 对象，如果无法提取则返回 None
    """
    if not raw_content:
        return None
    
    # 1. 尝试从 markdown 代码块中提取 JSON
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
    ]
    
    for pattern in json_patterns:
        import re
        matches = re.findall(pattern, raw_content)
        for match in matches:
            try:
                cleaned = match.strip()
                if cleaned.startswith('{') or cleaned.startswith('['):
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict) and len(parsed) > 0:
                        # 检查是否包含有意义的键
                        meaningful_keys = [k for k in parsed.keys() if k not in ['raw_content']]
                        if meaningful_keys:
                            return parsed
            except json.JSONDecodeError:
                continue
    
    # 2. 尝试查找最大的 JSON 对象
    json_objects = []
    i = 0
    while i < len(raw_content):
        if raw_content[i] == '{':
            depth = 0
            start = i
            in_string = False
            escape_next = False
            
            for j in range(i, min(i + 50000, len(raw_content))):  # 限制搜索范围
                char = raw_content[j]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if in_string:
                    continue
                
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = raw_content[start:j+1]
                        try:
                            obj = json.loads(json_str)
                            if isinstance(obj, dict) and len(obj) > 0:
                                meaningful_keys = [k for k in obj.keys() if k not in ['raw_content']]
                                if meaningful_keys:
                                    json_objects.append(obj)
                        except json.JSONDecodeError:
                            pass
                        break
            
            i = j + 1 if depth == 0 else i + 1
        else:
            i += 1
        
        # 限制搜索次数
        if len(json_objects) >= 5:
            break
    
    if json_objects:
        # 返回最大的有效 JSON 对象
        return max(json_objects, key=lambda x: len(json.dumps(x, ensure_ascii=False)))
    
    return None


@router.get("/{project_id}/stage-docs/{stage_name}", response_model=APIResponse)
async def get_stage_document(
    project_id: str = Path(..., description="项目ID"),
    stage_name: str = Path(..., description="阶段名称")
):
    """
    获取特定阶段的设计文档
    
    根据工作流类型在不同目录查找：
    - agent_build/agent_update: projects/<project>/agents/<agent>/<stage>.json
    - tool_build: tools/generated_tools/tool_build_<tool_name>/<stage>.json
    
    如果文件不存在，再回退到数据库的 output_data
    """
    try:
        from pathlib import Path as PathLib
        project_root = PathLib(__file__).resolve().parent.parent.parent.parent
        projects_dir = _get_projects_dir()
        tools_dir = _get_tools_dir()
        
        # 将 BuildStage 枚举值映射到实际文件名
        file_stage_name = STAGE_NAME_TO_FILE_NAME.get(stage_name, stage_name)
        
        # 获取项目信息
        db_project = project_service.db.get_project(project_id)
        
        # 获取工作流类型
        workflow_type = db_project.get('workflow_type', 'agent_build') if db_project else 'agent_build'
        
        # 尝试从数据库 stage 记录获取 doc_path
        db_stage = project_service.db.get_stage(project_id, stage_name)
        doc_path_from_db = db_stage.get('doc_path') if db_stage else None
        
        # 如果数据库中有 doc_path，优先使用
        if doc_path_from_db and os.path.exists(os.path.join(str(project_root), doc_path_from_db)):
            doc_path = os.path.join(str(project_root), doc_path_from_db)
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed_content = None
            try:
                parsed_content = json.loads(content)
            except:
                pass
            
            return APIResponse(
                success=True,
                data={
                    'exists': True,
                    'stage_name': stage_name,
                    'content': content,
                    'parsed_content': parsed_content,
                    'path': doc_path_from_db,
                    'source': 'file'
                },
                timestamp=_now(),
                request_id=_request_id()
            )
        
        # 根据工作流类型确定搜索目录
        project_path = None
        possible_project_names = []
        
        if workflow_type == 'tool_build':
            # 工具构建：在 tools/generated_tools 目录下查找
            if db_project:
                metadata = db_project.get('metadata', {})
                tool_name = metadata.get('tool_name') or db_project.get('project_name')
                if tool_name:
                    # 尝试多种可能的目录名
                    possible_names = [
                        f"tool_build_{tool_name}",
                        tool_name,
                    ]
                    for name in possible_names:
                        candidate_path = os.path.join(tools_dir, name)
                        if os.path.exists(candidate_path):
                            project_path = candidate_path
                            logger.info(f"Found tool build directory: {candidate_path}")
                            break
            
            # 如果还没找到，扫描 tools/generated_tools 目录
            if not project_path and os.path.exists(tools_dir):
                for item in os.listdir(tools_dir):
                    if item.startswith('tool_build_'):
                        item_path = os.path.join(tools_dir, item)
                        if os.path.isdir(item_path):
                            # 检查是否有 status.yaml 或 config.yaml 匹配
                            status_file = os.path.join(item_path, 'status.yaml')
                            if os.path.exists(status_file):
                                try:
                                    with open(status_file, 'r', encoding='utf-8') as f:
                                        status_data = yaml.safe_load(f)
                                    if status_data.get('project_id') == project_id:
                                        project_path = item_path
                                        logger.info(f"Found tool build via status.yaml: {item_path}")
                                        break
                                except Exception as e:
                                    logger.warning(f"Failed to parse status.yaml in {item_path}: {e}")
        else:
            # Agent 构建/更新：在 projects 目录下查找
            # 1. 首先尝试直接使用 project_id 作为目录名（适用于本地项目）
            possible_project_names.append(project_id)
            
            # 2. 如果有数据库项目，尝试使用 local_project_dir 和 project_name
            if db_project:
                # 优先使用 local_project_dir（本地项目目录名）
                local_dir = db_project.get('local_project_dir')
                if local_dir:
                    possible_project_names.insert(0, local_dir)  # 插入到最前面
                
                project_name = db_project.get('project_name')
                if project_name:
                    possible_project_names.append(project_name)
            
            # 尝试每个可能的项目名
            for name in possible_project_names:
                candidate_path = os.path.join(projects_dir, name)
                if os.path.exists(candidate_path):
                    project_path = candidate_path
                    logger.info(f"Found project directory: {candidate_path}")
                    break
        
            # 如果还没找到，扫描 projects 目录查找匹配的项目
            if not project_path and os.path.exists(projects_dir):
                for item in os.listdir(projects_dir):
                    item_path = os.path.join(projects_dir, item)
                    if os.path.isdir(item_path):
                        # 检查 status.yaml 中的 project 字段或 project_id
                        status_file = os.path.join(item_path, 'status.yaml')
                        config_file = os.path.join(item_path, 'config.yaml')
                        project_config_file = os.path.join(item_path, 'project_config.json')
                        
                        if os.path.exists(status_file):
                            try:
                                with open(status_file, 'r', encoding='utf-8') as f:
                                    status_data = yaml.safe_load(f)
                                # 检查 project 字段（目录名）或 project_id
                                if status_data.get('project') == project_id or status_data.get('project_id') == project_id:
                                    project_path = item_path
                                    logger.info(f"Found project via status.yaml: {item_path}")
                                    break
                            except Exception as e:
                                logger.warning(f"Failed to parse status.yaml in {item_path}: {e}")
                        
                        if not project_path and os.path.exists(config_file):
                            try:
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    config_data = yaml.safe_load(f)
                                # 检查 project.name 或 project_id
                                project_section = config_data.get('project', {})
                                if isinstance(project_section, dict):
                                    if project_section.get('name') == project_id or config_data.get('project_id') == project_id:
                                        project_path = item_path
                                        logger.info(f"Found project via config.yaml: {item_path}")
                                        break
                            except Exception as e:
                                logger.warning(f"Failed to parse config.yaml in {item_path}: {e}")
                        
                        if not project_path and os.path.exists(project_config_file):
                            try:
                                with open(project_config_file, 'r', encoding='utf-8') as f:
                                    project_config_data = json.load(f)
                                if project_config_data.get('project_id') == project_id:
                                    project_path = item_path
                                    logger.info(f"Found project via project_config.json: {item_path}")
                                    break
                            except Exception as e:
                                logger.warning(f"Failed to parse project_config.json in {item_path}: {e}")
        
        # 尝试从文件系统读取阶段文档
        doc_path = None
        agent_name = None
        
        if project_path and os.path.exists(project_path):
            # 首先尝试从 status.yaml 获取 agent_name 和 doc_path
            status_file = os.path.join(project_path, 'status.yaml')
            doc_path_from_status = None
            
            if os.path.exists(status_file):
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status_data = yaml.safe_load(f)
                    
                    project_info = status_data.get('project_info', [])
                    if project_info and len(project_info) > 0:
                        info = project_info[0]
                        agents_list = info.get('agents', [])
                        if agents_list and len(agents_list) > 0:
                            agent_info = agents_list[0]
                            agent_name = agent_info.get('name')
                            pipeline = agent_info.get('pipeline', [])
                            for stage_data in pipeline:
                                if stage_data.get('stage') in [stage_name, file_stage_name]:
                                    doc_path_from_status = stage_data.get('doc_path')
                                    break
                except Exception as e:
                    logger.warning(f"Failed to parse status.yaml: {e}")
            
            # 构建可能的文档路径列表
            possible_paths = []
            
            # 如果从 status.yaml 获取到了 doc_path，优先使用
            if doc_path_from_status:
                possible_paths.append(os.path.join(str(project_root), doc_path_from_status))
            
            if workflow_type == 'tool_build':
                # 工具构建：文档在 stages 子目录下或直接在工具目录下
                possible_paths.extend([
                    os.path.join(project_path, 'stages', f'{file_stage_name}.json'),
                    os.path.join(project_path, 'stages', f'{stage_name}.json'),
                    os.path.join(project_path, f'{file_stage_name}.json'),
                    os.path.join(project_path, f'{stage_name}.json'),
                    os.path.join(project_path, 'docs', f'{file_stage_name}.json'),
                    os.path.join(project_path, 'docs', f'{stage_name}.json'),
                ])
            else:
                # Agent 构建/更新：文档在 agents/{agent_name}/ 目录下
                # 如果有 agent_name，尝试在 agents/{agent_name}/ 目录下查找
                if agent_name:
                    possible_paths.append(os.path.join(project_path, 'agents', agent_name, f'{file_stage_name}.json'))
                    if file_stage_name != stage_name:
                        possible_paths.append(os.path.join(project_path, 'agents', agent_name, f'{stage_name}.json'))
                
                # 尝试扫描 agents 目录下的所有子目录
                agents_dir = os.path.join(project_path, 'agents')
                if os.path.exists(agents_dir):
                    for item in os.listdir(agents_dir):
                        item_path = os.path.join(agents_dir, item)
                        if os.path.isdir(item_path):
                            possible_paths.append(os.path.join(item_path, f'{file_stage_name}.json'))
                            if file_stage_name != stage_name:
                                possible_paths.append(os.path.join(item_path, f'{stage_name}.json'))
                
                # 添加其他可能的路径
                possible_paths.extend([
                    os.path.join(project_path, 'agents', f'{file_stage_name}.json'),
                    os.path.join(project_path, f'{file_stage_name}.json'),
                ])
            
            # 查找第一个存在的文件
            for path in possible_paths:
                if path and os.path.exists(path):
                    doc_path = path
                    break
        
        # 如果找到了文件，读取并返回
        if doc_path:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed_content = None
            try:
                parsed_content = json.loads(content)
            except:
                pass
            
            return APIResponse(
                success=True,
                data={
                    'exists': True,
                    'stage_name': stage_name,
                    'content': content,
                    'parsed_content': parsed_content,
                    'path': os.path.relpath(doc_path, project_path) if doc_path.startswith(project_path) else doc_path,
                    'source': 'file'
                },
                timestamp=_now(),
                request_id=_request_id()
            )
        
        # 如果文件不存在，回退到数据库的 output_data
        db_stage = project_service.db.get_stage(project_id, stage_name)
        if db_stage and db_stage.get('output_data'):
            output_data = db_stage.get('output_data')
            if isinstance(output_data, str):
                try:
                    parsed_content = json.loads(output_data)
                except:
                    parsed_content = None
                content = output_data
            else:
                parsed_content = output_data
                content = json.dumps(output_data, ensure_ascii=False, indent=2)
            
            # 如果 parsed_content 只包含 raw_content，尝试从中提取 JSON
            if parsed_content and isinstance(parsed_content, dict) and 'raw_content' in parsed_content and len(parsed_content) == 1:
                raw_content = parsed_content.get('raw_content', '')
                extracted_json = _try_extract_json_from_raw_content(raw_content)
                if extracted_json:
                    parsed_content = extracted_json
                    content = json.dumps(extracted_json, ensure_ascii=False, indent=2)
            
            return APIResponse(
                success=True,
                data={
                    'exists': True,
                    'stage_name': stage_name,
                    'content': content,
                    'parsed_content': parsed_content,
                    'path': 'database',
                    'source': 'database'
                },
                timestamp=_now(),
                request_id=_request_id()
            )
        
        # 都没有找到
        return APIResponse(
            success=True,
            data={'exists': False, 'content': None, 'stage_name': stage_name},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get stage document {stage_name} for {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取阶段文档失败: {str(e)}")
