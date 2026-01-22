"""
Agent Files API Router

Agent 文件管理相关的 API 端点
支持查看和编辑 Agent 代码、提示词 YAML 和工具文件
"""
from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import Optional, List
import logging
import os
from datetime import datetime, timezone
import uuid
from pathlib import Path as FilePath
from pydantic import BaseModel

from api.v2.models.schemas import APIResponse
from api.v2.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agent Files"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


def _get_project_root() -> FilePath:
    """获取项目根目录"""
    current_file = FilePath(__file__).resolve()
    return current_file.parent.parent.parent.parent


def _get_language_from_extension(file_path: str) -> str:
    """根据文件扩展名获取语言类型"""
    ext_map = {
        '.py': 'python',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.md': 'markdown',
        '.txt': 'text',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.sh': 'bash',
    }
    ext = os.path.splitext(file_path)[1].lower()
    return ext_map.get(ext, 'text')


def _safe_read_file(file_path: FilePath) -> Optional[str]:
    """安全读取文件内容"""
    try:
        if file_path.exists() and file_path.is_file():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
    return None


def _safe_write_file(file_path: FilePath, content: str) -> bool:
    """安全写入文件内容"""
    try:
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False


class FileInfo(BaseModel):
    """文件信息"""
    path: str
    name: str
    language: str
    content: Optional[str] = None
    size: Optional[int] = None
    exists: bool = True


class ToolFileInfo(BaseModel):
    """工具文件信息"""
    path: str
    name: str
    language: str
    content: Optional[str] = None
    size: Optional[int] = None
    exists: bool = True


class AgentFilesResponse(BaseModel):
    """Agent 文件响应"""
    agent_id: str
    agent_name: Optional[str] = None
    code_file: Optional[FileInfo] = None
    prompt_file: Optional[FileInfo] = None
    tool_files: List[ToolFileInfo] = []


class SaveFileRequest(BaseModel):
    """保存文件请求"""
    content: str
    file_type: str  # 'code', 'prompt', 'tool'
    tool_path: Optional[str] = None  # 当 file_type 为 'tool' 时需要


@router.get("/{agent_id}/files", response_model=APIResponse)
async def get_agent_files(
    agent_id: str = Path(..., description="Agent ID"),
    include_content: bool = Query(True, description="是否包含文件内容")
):
    """
    获取 Agent 的所有文件信息
    
    返回 Agent 的代码文件、提示词 YAML 文件和工具文件列表
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        project_root = _get_project_root()
        response = AgentFilesResponse(
            agent_id=agent_id,
            agent_name=agent.get('agent_name')
        )
        
        # 获取代码文件
        code_path = agent.get('code_path') or agent.get('agent_path')
        if code_path:
            full_code_path = project_root / code_path
            content = _safe_read_file(full_code_path) if include_content else None
            response.code_file = FileInfo(
                path=code_path,
                name=os.path.basename(code_path),
                language=_get_language_from_extension(code_path),
                content=content,
                size=full_code_path.stat().st_size if full_code_path.exists() else None,
                exists=full_code_path.exists()
            )
        
        # 获取提示词文件
        prompt_path = agent.get('prompt_path')
        if prompt_path:
            # 处理相对路径，添加 prompts/ 前缀
            if not prompt_path.startswith('prompts/'):
                prompt_path = f"prompts/{prompt_path}"
            full_prompt_path = project_root / prompt_path
            content = _safe_read_file(full_prompt_path) if include_content else None
            response.prompt_file = FileInfo(
                path=prompt_path,
                name=os.path.basename(prompt_path),
                language='yaml',
                content=content,
                size=full_prompt_path.stat().st_size if full_prompt_path.exists() else None,
                exists=full_prompt_path.exists()
            )
        
        # 获取工具文件
        tools_dependencies = agent.get('tools_dependencies', [])
        project_id = agent.get('project_id')
        agent_name = agent.get('agent_name')
        tools_path = agent.get('tools_path')
        
        # 从 tools_dependencies 中提取生成的工具
        tool_paths = set()
        for tool_dep in tools_dependencies:
            if tool_dep.startswith('generated_tools/'):
                # 提取工具文件路径
                parts = tool_dep.split('/')
                if len(parts) >= 3:
                    tool_dir = f"tools/generated_tools/{parts[1]}"
                    tool_file = f"{parts[2]}.py" if len(parts) == 3 else f"{parts[2]}.py"
                    tool_paths.add(f"{tool_dir}/{tool_file}")
        
        # 如果有 tools_path 字段，扫描其所在目录的所有工具文件
        if not tool_paths and tools_path:
            if tools_path.startswith('generated_tools/'):
                full_tools_path = project_root / "tools" / tools_path
                # 无论是文件还是目录，都扫描所在目录的所有 .py 文件
                if full_tools_path.is_file():
                    tools_dir = full_tools_path.parent
                elif full_tools_path.is_dir():
                    tools_dir = full_tools_path
                else:
                    tools_dir = full_tools_path.parent
                
                if tools_dir.exists():
                    for tool_file in tools_dir.glob("*.py"):
                        if not tool_file.name.startswith('__'):
                            tool_paths.add(str(tool_file.relative_to(project_root)))
        
        # 如果没有从 tools_dependencies 或 tools_path 获取到，尝试从项目目录扫描
        if not tool_paths:
            # 优先使用 agent_name 作为目录名，其次使用 project_id
            possible_dirs = []
            if agent_name:
                possible_dirs.append(project_root / "tools" / "generated_tools" / agent_name)
            if project_id:
                possible_dirs.append(project_root / "tools" / "generated_tools" / project_id)
            
            for tools_dir in possible_dirs:
                if tools_dir.exists():
                    for tool_file in tools_dir.glob("*.py"):
                        if not tool_file.name.startswith('__'):
                            tool_paths.add(str(tool_file.relative_to(project_root)))
                    if tool_paths:
                        break  # 找到工具文件后停止
        
        # 读取工具文件内容
        for tool_path in sorted(tool_paths):
            full_tool_path = project_root / tool_path
            content = _safe_read_file(full_tool_path) if include_content else None
            response.tool_files.append(ToolFileInfo(
                path=tool_path,
                name=os.path.basename(tool_path),
                language='python',
                content=content,
                size=full_tool_path.stat().st_size if full_tool_path.exists() else None,
                exists=full_tool_path.exists()
            ))
        
        return APIResponse(
            success=True,
            data=response.model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent files {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 文件失败: {str(e)}")


@router.get("/{agent_id}/files/code", response_model=APIResponse)
async def get_agent_code(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    获取 Agent 代码文件内容
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        code_path = agent.get('code_path') or agent.get('agent_path')
        if not code_path:
            raise HTTPException(status_code=404, detail="Agent 没有关联的代码文件")
        
        project_root = _get_project_root()
        full_path = project_root / code_path
        
        content = _safe_read_file(full_path)
        if content is None:
            raise HTTPException(status_code=404, detail=f"代码文件不存在: {code_path}")
        
        return APIResponse(
            success=True,
            data=FileInfo(
                path=code_path,
                name=os.path.basename(code_path),
                language='python',
                content=content,
                size=full_path.stat().st_size,
                exists=True
            ).model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent code {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 代码失败: {str(e)}")


@router.get("/{agent_id}/files/prompt", response_model=APIResponse)
async def get_agent_prompt(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    获取 Agent 提示词 YAML 文件内容
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        prompt_path = agent.get('prompt_path')
        if not prompt_path:
            raise HTTPException(status_code=404, detail="Agent 没有关联的提示词文件")
        
        # 处理相对路径
        if not prompt_path.startswith('prompts/'):
            prompt_path = f"prompts/{prompt_path}"
        
        project_root = _get_project_root()
        full_path = project_root / prompt_path
        
        content = _safe_read_file(full_path)
        if content is None:
            raise HTTPException(status_code=404, detail=f"提示词文件不存在: {prompt_path}")
        
        return APIResponse(
            success=True,
            data=FileInfo(
                path=prompt_path,
                name=os.path.basename(prompt_path),
                language='yaml',
                content=content,
                size=full_path.stat().st_size,
                exists=True
            ).model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent prompt {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 提示词失败: {str(e)}")


@router.get("/{agent_id}/files/tools", response_model=APIResponse)
async def get_agent_tools(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    获取 Agent 工具文件列表和内容
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        project_root = _get_project_root()
        tool_files = []
        
        # 从 tools_dependencies 中提取生成的工具
        tools_dependencies = agent.get('tools_dependencies', [])
        project_id = agent.get('project_id')
        agent_name = agent.get('agent_name')
        tools_path = agent.get('tools_path')
        
        tool_paths = set()
        for tool_dep in tools_dependencies:
            if tool_dep.startswith('generated_tools/'):
                parts = tool_dep.split('/')
                if len(parts) >= 3:
                    tool_dir = f"tools/generated_tools/{parts[1]}"
                    tool_file = f"{parts[2]}.py" if len(parts) == 3 else f"{parts[2]}.py"
                    tool_paths.add(f"{tool_dir}/{tool_file}")
        
        # 如果有 tools_path 字段，扫描其所在目录的所有工具文件
        if not tool_paths and tools_path:
            if tools_path.startswith('generated_tools/'):
                full_tools_path = project_root / "tools" / tools_path
                # 无论是文件还是目录，都扫描所在目录的所有 .py 文件
                if full_tools_path.is_file():
                    tools_dir = full_tools_path.parent
                elif full_tools_path.is_dir():
                    tools_dir = full_tools_path
                else:
                    tools_dir = full_tools_path.parent
                
                if tools_dir.exists():
                    for tool_file in tools_dir.glob("*.py"):
                        if not tool_file.name.startswith('__'):
                            tool_paths.add(str(tool_file.relative_to(project_root)))
        
        # 如果没有从 tools_dependencies 或 tools_path 获取到，尝试从项目目录扫描
        if not tool_paths:
            possible_dirs = []
            if agent_name:
                possible_dirs.append(project_root / "tools" / "generated_tools" / agent_name)
            if project_id:
                possible_dirs.append(project_root / "tools" / "generated_tools" / project_id)
            
            for tools_dir in possible_dirs:
                if tools_dir.exists():
                    for tool_file in tools_dir.glob("*.py"):
                        if not tool_file.name.startswith('__'):
                            tool_paths.add(str(tool_file.relative_to(project_root)))
                    if tool_paths:
                        break
        
        # 读取工具文件内容
        for tool_path in sorted(tool_paths):
            full_tool_path = project_root / tool_path
            content = _safe_read_file(full_tool_path)
            tool_files.append(ToolFileInfo(
                path=tool_path,
                name=os.path.basename(tool_path),
                language='python',
                content=content,
                size=full_tool_path.stat().st_size if full_tool_path.exists() else None,
                exists=full_tool_path.exists()
            ).model_dump())
        
        return APIResponse(
            success=True,
            data=tool_files,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent tools {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 工具失败: {str(e)}")


@router.put("/{agent_id}/files/code", response_model=APIResponse)
async def save_agent_code(
    agent_id: str = Path(..., description="Agent ID"),
    request: SaveFileRequest = Body(...)
):
    """
    保存 Agent 代码文件
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        code_path = agent.get('code_path') or agent.get('agent_path')
        if not code_path:
            raise HTTPException(status_code=404, detail="Agent 没有关联的代码文件")
        
        project_root = _get_project_root()
        full_path = project_root / code_path
        
        if not _safe_write_file(full_path, request.content):
            raise HTTPException(status_code=500, detail="保存代码文件失败")
        
        return APIResponse(
            success=True,
            message="代码文件保存成功",
            data={"path": code_path},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save agent code {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存 Agent 代码失败: {str(e)}")


@router.put("/{agent_id}/files/prompt", response_model=APIResponse)
async def save_agent_prompt(
    agent_id: str = Path(..., description="Agent ID"),
    request: SaveFileRequest = Body(...)
):
    """
    保存 Agent 提示词 YAML 文件
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        prompt_path = agent.get('prompt_path')
        if not prompt_path:
            raise HTTPException(status_code=404, detail="Agent 没有关联的提示词文件")
        
        # 处理相对路径
        if not prompt_path.startswith('prompts/'):
            prompt_path = f"prompts/{prompt_path}"
        
        project_root = _get_project_root()
        full_path = project_root / prompt_path
        
        if not _safe_write_file(full_path, request.content):
            raise HTTPException(status_code=500, detail="保存提示词文件失败")
        
        return APIResponse(
            success=True,
            message="提示词文件保存成功",
            data={"path": prompt_path},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save agent prompt {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存 Agent 提示词失败: {str(e)}")


@router.put("/{agent_id}/files/tools/{tool_name}", response_model=APIResponse)
async def save_agent_tool(
    agent_id: str = Path(..., description="Agent ID"),
    tool_name: str = Path(..., description="工具文件名"),
    request: SaveFileRequest = Body(...)
):
    """
    保存 Agent 工具文件
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        project_id = agent.get('project_id')
        if not project_id:
            raise HTTPException(status_code=400, detail="无法确定工具文件路径")
        
        # 构建工具文件路径
        tool_path = f"tools/generated_tools/{project_id}/{tool_name}"
        if not tool_path.endswith('.py'):
            tool_path += '.py'
        
        project_root = _get_project_root()
        full_path = project_root / tool_path
        
        if not _safe_write_file(full_path, request.content):
            raise HTTPException(status_code=500, detail="保存工具文件失败")
        
        return APIResponse(
            success=True,
            message="工具文件保存成功",
            data={"path": tool_path},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save agent tool {agent_id}/{tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存 Agent 工具失败: {str(e)}")
