"""
Agent Tools API Router

Agent 工具管理相关的 API 端点
支持查看工具列表、工具详情、MCP服务器管理和工具测试
"""
from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import Optional, List, Dict, Any
import logging
import os
import json
import ast
import subprocess
from datetime import datetime, timezone
import uuid
from pathlib import Path as FilePath
from pydantic import BaseModel

from api.v2.models.schemas import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Agent Tools"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


def _get_project_root() -> FilePath:
    """获取项目根目录"""
    current_file = FilePath(__file__).resolve()
    return current_file.parent.parent.parent.parent


# ============== 数据模型 ==============

class ToolParameter(BaseModel):
    """工具参数信息"""
    name: str
    type: str = "Any"
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    type: str  # builtin, generated, system, template, mcp
    category: Optional[str] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    parameters: List[ToolParameter] = []
    package: Optional[str] = None  # 内置工具的包名
    enabled: bool = True
    mcp_server: Optional[str] = None  # MCP工具所属服务器
    return_type: Optional[str] = None  # 返回值类型


class MCPServerInfo(BaseModel):
    """MCP服务器信息"""
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    disabled: bool = False
    auto_approve: List[str] = []
    tools: List[str] = []  # 该服务器提供的工具列表


class ToolTestRequest(BaseModel):
    """工具测试请求"""
    parameters: Dict[str, Any] = {}


class ToolTestResult(BaseModel):
    """工具测试结果"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ToolConfigRequest(BaseModel):
    """工具配置请求"""
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


# ============== 工具解析函数 ==============

def _get_builtin_tools_info() -> Dict[str, Dict[str, Any]]:
    """获取系统内置工具信息"""
    return {
        'retrieve': {'category': 'RAG & Memory', 'description': '从 Amazon Bedrock Knowledge Bases 语义检索数据', 'package': 'strands-agents-tools'},
        'memory': {'category': 'RAG & Memory', 'description': 'Agent 记忆持久化到 Amazon Bedrock Knowledge Bases', 'package': 'strands-agents-tools'},
        'mem0_memory': {'category': 'RAG & Memory', 'description': '基于 Mem0 的 Agent 记忆和个性化', 'package': 'strands-agents-tools[mem0_memory]'},
        'editor': {'category': 'File Operations', 'description': '文件编辑操作（行编辑、搜索、撤销）', 'package': 'strands-agents-tools'},
        'file_read': {'category': 'File Operations', 'description': '读取和解析文件', 'package': 'strands-agents-tools'},
        'file_write': {'category': 'File Operations', 'description': '创建和修改文件', 'package': 'strands-agents-tools'},
        'environment': {'category': 'Shell & System', 'description': '管理环境变量', 'package': 'strands-agents-tools'},
        'shell': {'category': 'Shell & System', 'description': '执行 Shell 命令', 'package': 'strands-agents-tools'},
        'cron': {'category': 'Shell & System', 'description': '使用 cron 任务调度', 'package': 'strands-agents-tools'},
        'python_repl': {'category': 'Code Interpretation', 'description': '运行 Python 代码', 'package': 'strands-agents-tools'},
        'http_request': {'category': 'Web & Network', 'description': 'API 调用、获取网页数据', 'package': 'strands-agents-tools'},
        'slack': {'category': 'Web & Network', 'description': 'Slack 集成（实时事件、API、消息发送）', 'package': 'strands-agents-tools'},
        'image_reader': {'category': 'Multi-modal', 'description': '处理和分析图像', 'package': 'strands-agents-tools'},
        'generate_image': {'category': 'Multi-modal', 'description': '使用 Amazon Bedrock 生成 AI 图像', 'package': 'strands-agents-tools'},
        'nova_reels': {'category': 'Multi-modal', 'description': '使用 Nova Reels 生成 AI 视频', 'package': 'strands-agents-tools'},
        'speak': {'category': 'Multi-modal', 'description': '文本转语音（macOS say 或 Amazon Polly）', 'package': 'strands-agents-tools'},
        'use_aws': {'category': 'AWS Services', 'description': '与 AWS 服务交互', 'package': 'strands-agents-tools'},
        'calculator': {'category': 'Utilities', 'description': '执行数学运算', 'package': 'strands-agents-tools'},
        'current_time': {'category': 'Utilities', 'description': '获取当前日期和时间', 'package': 'strands-agents-tools'},
        'load_tool': {'category': 'Utilities', 'description': '运行时动态加载更多工具', 'package': 'strands-agents-tools'},
        'agent_graph': {'category': 'Agents & Workflows', 'description': '创建和管理 Agent 图', 'package': 'strands-agents-tools'},
        'journal': {'category': 'Agents & Workflows', 'description': '创建结构化任务和日志', 'package': 'strands-agents-tools'},
        'swarm': {'category': 'Agents & Workflows', 'description': '协调多个 AI Agent 协作', 'package': 'strands-agents-tools'},
        'stop': {'category': 'Agents & Workflows', 'description': '强制停止 Agent 事件循环', 'package': 'strands-agents-tools'},
        'think': {'category': 'Agents & Workflows', 'description': '创建并行推理分支进行深度思考', 'package': 'strands-agents-tools'},
        'use_llm': {'category': 'Agents & Workflows', 'description': '使用自定义提示运行新的 AI 事件循环', 'package': 'strands-agents-tools'},
        'workflow': {'category': 'Agents & Workflows', 'description': '编排顺序工作流', 'package': 'strands-agents-tools'},
    }


def _parse_annotation(annotation) -> str:
    """解析类型注解为字符串"""
    if annotation is None:
        return 'Any'
    
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):
        return str(annotation.value)
    elif isinstance(annotation, ast.Subscript):
        # 处理 Optional[str], List[int], Dict[str, Any] 等泛型类型
        if isinstance(annotation.value, ast.Name):
            base_type = annotation.value.id
            # 解析泛型参数
            if isinstance(annotation.slice, ast.Tuple):
                # Dict[str, Any] 等多参数泛型
                args = [_parse_annotation(elt) for elt in annotation.slice.elts]
                return f"{base_type}[{', '.join(args)}]"
            else:
                # Optional[str], List[int] 等单参数泛型
                inner = _parse_annotation(annotation.slice)
                return f"{base_type}[{inner}]"
        elif isinstance(annotation.value, ast.Attribute):
            # typing.Optional 等
            return f"{annotation.value.attr}[{_parse_annotation(annotation.slice)}]"
    elif isinstance(annotation, ast.Attribute):
        # typing.Any 等
        return annotation.attr
    elif isinstance(annotation, ast.BinOp):
        # str | None 等 Union 类型 (Python 3.10+)
        left = _parse_annotation(annotation.left)
        right = _parse_annotation(annotation.right)
        return f"{left} | {right}"
    
    return 'Any'


def _parse_tool_file(file_path: FilePath) -> List[Dict[str, Any]]:
    """解析 Python 文件中的工具函数"""
    tools = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查是否有 @tool 装饰器
                has_tool_decorator = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                        has_tool_decorator = True
                        break
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == 'tool':
                        has_tool_decorator = True
                        break
                
                if has_tool_decorator:
                    # 提取函数信息
                    docstring = ast.get_docstring(node) or ""
                    
                    # 解析返回值类型
                    return_type = _parse_annotation(node.returns) if node.returns else None
                    
                    # 解析参数
                    parameters = []
                    defaults = node.args.defaults
                    num_defaults = len(defaults)
                    num_args = len(node.args.args)
                    
                    for i, arg in enumerate(node.args.args):
                        param_type = _parse_annotation(arg.annotation)
                        
                        # 判断是否有默认值
                        default_index = i - (num_args - num_defaults)
                        has_default = default_index >= 0
                        
                        parameters.append({
                            'name': arg.arg,
                            'type': param_type,
                            'required': not has_default,
                            'default': None
                        })
                    
                    tools.append({
                        'name': node.name,
                        'description': docstring.split('\n')[0] if docstring else "无描述",
                        'file_path': str(file_path),
                        'line_number': node.lineno,
                        'parameters': parameters,
                        'return_type': return_type
                    })
    
    except Exception as e:
        logger.warning(f"Failed to parse tool file {file_path}: {e}")
    
    return tools


def _get_mcp_servers() -> Dict[str, MCPServerInfo]:
    """获取 MCP 服务器配置"""
    project_root = _get_project_root()
    servers = {}
    
    # 读取系统 MCP 配置
    system_mcp_path = project_root / "mcp" / "system_mcp_server.json"
    if system_mcp_path.exists():
        try:
            with open(system_mcp_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            mcp_servers = config.get('mcpServers', {})
            for name, server_config in mcp_servers.items():
                if isinstance(server_config, dict) and 'command' in server_config:
                    servers[name] = MCPServerInfo(
                        name=name,
                        command=server_config.get('command', ''),
                        args=server_config.get('args', []),
                        env=server_config.get('env', {}),
                        disabled=server_config.get('disabled', False),
                        auto_approve=server_config.get('autoApprove', []),
                        tools=[]
                    )
        except Exception as e:
            logger.warning(f"Failed to load system MCP config: {e}")
    
    # 读取公共 MCP 配置
    public_mcp_path = project_root / "mcp" / "public_mcp_server.json"
    if public_mcp_path.exists():
        try:
            with open(public_mcp_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            mcp_servers = config.get('mcpServers', {})
            for name, server_config in mcp_servers.items():
                if isinstance(server_config, dict) and 'command' in server_config:
                    servers[name] = MCPServerInfo(
                        name=name,
                        command=server_config.get('command', ''),
                        args=server_config.get('args', []),
                        env=server_config.get('env', {}),
                        disabled=server_config.get('disabled', False),
                        auto_approve=server_config.get('autoApprove', []),
                        tools=[]
                    )
        except Exception as e:
            logger.warning(f"Failed to load public MCP config: {e}")
    
    return servers


def _scan_tools_directory(base_dir: FilePath, tool_type: str) -> List[ToolInfo]:
    """扫描工具目录"""
    tools = []
    
    if not base_dir.exists():
        return tools
    
    for file_path in base_dir.rglob("*.py"):
        if file_path.name.startswith('__'):
            continue
        
        parsed_tools = _parse_tool_file(file_path)
        for tool_data in parsed_tools:
            # 获取相对路径作为分类
            relative_path = file_path.relative_to(base_dir)
            category = str(relative_path.parent) if relative_path.parent != FilePath('.') else 'general'
            
            tools.append(ToolInfo(
                name=tool_data['name'],
                type=tool_type,
                category=category,
                description=tool_data['description'],
                file_path=str(file_path),
                parameters=[ToolParameter(**p) for p in tool_data['parameters']],
                return_type=tool_data.get('return_type'),
                enabled=True
            ))
    
    return tools


# ============== API 端点 ==============

@router.get("/categories", response_model=APIResponse)
async def get_tool_categories():
    """
    获取所有工具分类
    """
    try:
        builtin_tools = _get_builtin_tools_info()
        categories = set()
        
        for tool_info in builtin_tools.values():
            categories.add(tool_info['category'])
        
        # 添加自定义工具分类
        categories.add('Generated Tools')
        categories.add('System Tools')
        categories.add('Template Tools')
        categories.add('MCP Tools')
        
        return APIResponse(
            success=True,
            data={
                'categories': sorted(list(categories)),
                'total': len(categories)
            },
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get tool categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工具分类失败: {str(e)}")



@router.get("/list", response_model=APIResponse)
async def list_all_tools(
    type: Optional[str] = Query(None, description="工具类型: builtin, generated, system, template, mcp"),
    category: Optional[str] = Query(None, description="工具分类"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    获取所有工具列表
    
    支持按类型、分类筛选和关键词搜索
    """
    try:
        project_root = _get_project_root()
        all_tools = []
        
        # 1. 内置工具
        if not type or type == 'builtin':
            builtin_tools = _get_builtin_tools_info()
            for name, info in builtin_tools.items():
                all_tools.append(ToolInfo(
                    name=name,
                    type='builtin',
                    category=info['category'],
                    description=info['description'],
                    package=info['package'],
                    enabled=True
                ))
        
        # 2. 生成的工具
        if not type or type == 'generated':
            generated_dir = project_root / "tools" / "generated_tools"
            all_tools.extend(_scan_tools_directory(generated_dir, 'generated'))
        
        # 3. 系统工具
        if not type or type == 'system':
            system_dir = project_root / "tools" / "system_tools"
            all_tools.extend(_scan_tools_directory(system_dir, 'system'))
        
        # 4. 模板工具
        if not type or type == 'template':
            template_dir = project_root / "tools" / "template_tools"
            all_tools.extend(_scan_tools_directory(template_dir, 'template'))
        
        # 5. MCP 工具
        if not type or type == 'mcp':
            mcp_servers = _get_mcp_servers()
            for server_name, server_info in mcp_servers.items():
                if not server_info.disabled:
                    all_tools.append(ToolInfo(
                        name=server_name,
                        type='mcp',
                        category='MCP Tools',
                        description=f"MCP Server: {server_info.command} {' '.join(server_info.args)}",
                        mcp_server=server_name,
                        enabled=not server_info.disabled
                    ))
        
        # 按分类筛选
        if category:
            all_tools = [t for t in all_tools if t.category and category.lower() in t.category.lower()]
        
        # 关键词搜索
        if search:
            search_lower = search.lower()
            all_tools = [t for t in all_tools if 
                        search_lower in t.name.lower() or 
                        (t.description and search_lower in t.description.lower())]
        
        # 按类型和名称排序
        all_tools.sort(key=lambda x: (x.type, x.name))
        
        return APIResponse(
            success=True,
            data={
                'tools': [t.model_dump() for t in all_tools],
                'total': len(all_tools),
                'by_type': {
                    'builtin': len([t for t in all_tools if t.type == 'builtin']),
                    'generated': len([t for t in all_tools if t.type == 'generated']),
                    'system': len([t for t in all_tools if t.type == 'system']),
                    'template': len([t for t in all_tools if t.type == 'template']),
                    'mcp': len([t for t in all_tools if t.type == 'mcp']),
                }
            },
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to list tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")



@router.get("/{tool_name}", response_model=APIResponse)
async def get_tool_detail(
    tool_name: str = Path(..., description="工具名称"),
    type: Optional[str] = Query(None, description="工具类型")
):
    """
    获取工具详情
    """
    try:
        project_root = _get_project_root()
        
        # 先检查内置工具
        builtin_tools = _get_builtin_tools_info()
        if tool_name in builtin_tools:
            info = builtin_tools[tool_name]
            return APIResponse(
                success=True,
                data=ToolInfo(
                    name=tool_name,
                    type='builtin',
                    category=info['category'],
                    description=info['description'],
                    package=info['package'],
                    enabled=True
                ).model_dump(),
                timestamp=_now(),
                request_id=_request_id()
            )
        
        # 搜索自定义工具
        tool_dirs = {
            'generated': project_root / "tools" / "generated_tools",
            'system': project_root / "tools" / "system_tools",
            'template': project_root / "tools" / "template_tools",
        }
        
        for tool_type, tool_dir in tool_dirs.items():
            if type and type != tool_type:
                continue
            
            tools = _scan_tools_directory(tool_dir, tool_type)
            for tool in tools:
                if tool.name == tool_name:
                    # 读取源代码
                    if tool.file_path:
                        try:
                            with open(tool.file_path, 'r', encoding='utf-8') as f:
                                tool_data = tool.model_dump()
                                tool_data['source_code'] = f.read()
                                return APIResponse(
                                    success=True,
                                    data=tool_data,
                                    timestamp=_now(),
                                    request_id=_request_id()
                                )
                        except Exception as e:
                            logger.warning(f"Failed to read tool source: {e}")
                    
                    return APIResponse(
                        success=True,
                        data=tool.model_dump(),
                        timestamp=_now(),
                        request_id=_request_id()
                    )
        
        raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工具详情失败: {str(e)}")



@router.post("/{tool_name}/test", response_model=APIResponse)
async def test_tool(
    tool_name: str = Path(..., description="工具名称"),
    request: ToolTestRequest = Body(...)
):
    """
    测试工具执行
    
    注意：仅支持测试自定义工具，内置工具需要在 Agent 上下文中测试
    """
    try:
        import time
        start_time = time.time()
        
        project_root = _get_project_root()
        
        # 查找工具文件
        tool_file = None
        tool_func_name = tool_name
        
        tool_dirs = [
            project_root / "tools" / "generated_tools",
            project_root / "tools" / "system_tools",
            project_root / "tools" / "template_tools",
        ]
        
        for tool_dir in tool_dirs:
            if not tool_dir.exists():
                continue
            
            for file_path in tool_dir.rglob("*.py"):
                if file_path.name.startswith('__'):
                    continue
                
                parsed_tools = _parse_tool_file(file_path)
                for tool_data in parsed_tools:
                    if tool_data['name'] == tool_name:
                        tool_file = file_path
                        break
                
                if tool_file:
                    break
            
            if tool_file:
                break
        
        if not tool_file:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在或不支持测试")
        
        # 动态导入并执行工具
        import importlib.util
        spec = importlib.util.spec_from_file_location("tool_module", tool_file)
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            return APIResponse(
                success=True,
                data=ToolTestResult(
                    success=False,
                    error=f"加载工具模块失败: {str(e)}"
                ).model_dump(),
                timestamp=_now(),
                request_id=_request_id()
            )
        
        # 获取工具函数
        if not hasattr(module, tool_func_name):
            return APIResponse(
                success=True,
                data=ToolTestResult(
                    success=False,
                    error=f"工具函数 '{tool_func_name}' 不存在"
                ).model_dump(),
                timestamp=_now(),
                request_id=_request_id()
            )
        
        tool_func = getattr(module, tool_func_name)
        
        # 执行工具
        try:
            result = tool_func(**request.parameters)
            duration_ms = int((time.time() - start_time) * 1000)
            
            return APIResponse(
                success=True,
                data=ToolTestResult(
                    success=True,
                    output=str(result) if result else "执行成功（无返回值）",
                    duration_ms=duration_ms
                ).model_dump(),
                timestamp=_now(),
                request_id=_request_id()
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return APIResponse(
                success=True,
                data=ToolTestResult(
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms
                ).model_dump(),
                timestamp=_now(),
                request_id=_request_id()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"测试工具失败: {str(e)}")



# ============== MCP 服务器管理 ==============

@router.get("/mcp/servers", response_model=APIResponse)
async def list_mcp_servers():
    """
    获取所有 MCP 服务器配置
    """
    try:
        servers = _get_mcp_servers()
        
        return APIResponse(
            success=True,
            data={
                'servers': [s.model_dump() for s in servers.values()],
                'total': len(servers),
                'enabled': len([s for s in servers.values() if not s.disabled]),
                'disabled': len([s for s in servers.values() if s.disabled])
            },
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to list MCP servers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 MCP 服务器列表失败: {str(e)}")


@router.get("/mcp/servers/{server_name}", response_model=APIResponse)
async def get_mcp_server(
    server_name: str = Path(..., description="MCP 服务器名称")
):
    """
    获取 MCP 服务器详情
    """
    try:
        servers = _get_mcp_servers()
        
        if server_name not in servers:
            raise HTTPException(status_code=404, detail=f"MCP 服务器 '{server_name}' 不存在")
        
        return APIResponse(
            success=True,
            data=servers[server_name].model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 MCP 服务器详情失败: {str(e)}")


@router.put("/mcp/servers/{server_name}", response_model=APIResponse)
async def update_mcp_server(
    server_name: str = Path(..., description="MCP 服务器名称"),
    disabled: Optional[bool] = Body(None, description="是否禁用"),
    auto_approve: Optional[List[str]] = Body(None, description="自动批准的工具列表")
):
    """
    更新 MCP 服务器配置
    """
    try:
        project_root = _get_project_root()
        
        # 读取配置文件
        system_mcp_path = project_root / "mcp" / "system_mcp_server.json"
        public_mcp_path = project_root / "mcp" / "public_mcp_server.json"
        
        config_path = None
        config = None
        
        # 查找服务器所在的配置文件
        for path in [system_mcp_path, public_mcp_path]:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    temp_config = json.load(f)
                
                if server_name in temp_config.get('mcpServers', {}):
                    config_path = path
                    config = temp_config
                    break
        
        if not config_path or not config:
            raise HTTPException(status_code=404, detail=f"MCP 服务器 '{server_name}' 不存在")
        
        # 更新配置
        server_config = config['mcpServers'][server_name]
        
        if disabled is not None:
            server_config['disabled'] = disabled
        
        if auto_approve is not None:
            server_config['autoApprove'] = auto_approve
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return APIResponse(
            success=True,
            message=f"MCP 服务器 '{server_name}' 配置已更新",
            data={'server_name': server_name, 'disabled': server_config.get('disabled', False)},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MCP server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新 MCP 服务器配置失败: {str(e)}")
