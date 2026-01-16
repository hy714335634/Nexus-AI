#!/usr/bin/env python3
"""
浏览器自动化工具集

集成Amazon Bedrock AgentCore、Nova Act和Browser Use，提供AI驱动的
网页交互、数据采集和自动化操作能力。

工具列表：
1. browser_with_nova_act - 基础Nova Act浏览器自动化
2. browser_with_live_view_nova - Nova Act + 实时视图
3. browser_with_live_view_use - Browser Use AI驱动自动化
4. manage_browser_session - 浏览器会话管理器
5. batch_extract_from_urls - 批量网页数据采集
"""

from strands import tool
import json
import asyncio
from typing import Optional, List, Dict, Any
from bedrock_agentcore.tools.browser_client import BrowserClient
from nova_act import NovaAct
from browser_use import Agent
from browser_use.browser.session import BrowserSession
from browser_use.browser import BrowserProfile
from langchain_aws import ChatBedrockConverse
from rich.console import Console
from contextlib import suppress
from boto3.session import Session
import logging

# 导入本地模块
from session_manager import get_session_store
from browser_viewer import BrowserViewerServer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化Rich控制台
console = Console()


@tool
def browser_with_nova_act(
    prompt: str,
    starting_page: str,
    nova_act_key: str,
    region: str = "us-west-2"
) -> str:
    """
    使用Nova Act进行基础浏览器自动化操作
    
    通过CDP WebSocket连接执行自然语言指令，支持网页搜索、表单填写、
    数据提取等自动化任务。
    
    Args:
        prompt: 自然语言浏览器操作指令（如：'搜索Python教程并提取前5个结果'）
        starting_page: 起始URL地址（如：'https://www.google.com'）
        nova_act_key: Nova Act API密钥
        region: AWS区域，默认为'us-west-2'
        
    Returns:
        str: JSON字符串，包含操作结果和响应数据
            成功格式：{"status": "success", "response": "操作完成", "data": {...}}
            错误格式：{"status": "error", "error_type": "...", "message": "..."}
    
    Example:
        >>> result = browser_with_nova_act(
        ...     prompt="搜索'机器学习'",
        ...     starting_page="https://www.google.com",
        ...     nova_act_key="your-api-key"
        ... )
    """
    # 参数验证
    if not prompt or not prompt.strip():
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "prompt不能为空"
        }, ensure_ascii=False)
    
    if not starting_page or not starting_page.strip():
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "starting_page不能为空"
        }, ensure_ascii=False)
    
    if not nova_act_key or not nova_act_key.strip():
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "nova_act_key不能为空"
        }, ensure_ascii=False)
    
    client = None
    try:
        console.print(f"[cyan]🚀 启动浏览器会话 (region={region})...[/cyan]")
        
        # 创建浏览器客户端
        client = BrowserClient(region)
        client.start()
        
        # 获取WebSocket连接信息
        ws_url, headers = client.generate_ws_headers()
        console.print(f"[green]✅ WebSocket连接已建立[/green]")
        
        # 使用Nova Act执行操作
        console.print(f"[cyan]🤖 执行操作: {prompt}[/cyan]")
        with NovaAct(
            cdp_endpoint_url=ws_url,
            cdp_headers=headers,
            preview={"playwright_actuation": True},
            nova_act_api_key=nova_act_key,
            starting_page=starting_page
        ) as nova_act:
            result = nova_act.act(prompt)
        
        console.print(f"[green]✅ 操作完成[/green]")
        
        # 提取结果数据
        result_data = {
            "response": result.response if hasattr(result, 'response') else str(result),
            "status_code": getattr(result, 'status_code', None),
            "screenshots": getattr(result, 'screenshots', []),
            "metadata": getattr(result, 'metadata', {})
        }
        
        return json.dumps({
            "status": "success",
            "response": result_data["response"],
            "data": result_data
        }, ensure_ascii=False, indent=2)
    
    except ValueError as e:
        console.print(f"[red]❌ 参数错误: {e}[/red]")
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": str(e)
        }, ensure_ascii=False)
    
    except ConnectionError as e:
        console.print(f"[red]❌ 连接错误: {e}[/red]")
        return json.dumps({
            "status": "error",
            "error_type": "ConnectionError",
            "message": f"CDP连接失败: {str(e)}"
        }, ensure_ascii=False)
    
    except TimeoutError as e:
        console.print(f"[red]❌ 超时错误: {e}[/red]")
        return json.dumps({
            "status": "error",
            "error_type": "TimeoutError",
            "message": f"操作超时: {str(e)}"
        }, ensure_ascii=False)
    
    except Exception as e:
        console.print(f"[red]❌ 未知错误: {e}[/red]")
        logger.exception("Unexpected error in browser_with_nova_act")
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, ensure_ascii=False)
    
    finally:
        if client:
            try:
                client.stop()
                console.print("[yellow]🔌 浏览器会话已关闭[/yellow]")
            except Exception as e:
                logger.error(f"Error stopping client: {e}")


@tool
def browser_with_live_view_nova(
    prompt: str,
    starting_page: str,
    nova_act_key: str,
    region: str = "us-west-2",
    viewer_port: int = 8000,
    display_size: str = "900p",
    open_browser: bool = True
) -> str:
    """
    使用Nova Act进行浏览器自动化，并提供DCV实时视图
    
    在基础自动化功能基础上增加实时浏览器查看功能，支持多种显示尺寸
    和手动控制。
    
    Args:
        prompt: 自然语言浏览器操作指令
        starting_page: 起始URL地址
        nova_act_key: Nova Act API密钥
        region: AWS区域，默认为'us-west-2'
        viewer_port: DCV viewer服务器端口，默认8000
        display_size: 显示尺寸（720p/900p/1080p/1440p），默认'900p'
        open_browser: 是否自动打开浏览器查看，默认True
        
    Returns:
        str: JSON字符串，包含操作结果、响应数据和viewer URL
            成功格式：{"status": "success", "response": "...", "viewer_url": "...", "data": {...}}
    
    Example:
        >>> result = browser_with_live_view_nova(
        ...     prompt="访问亚马逊首页并截图",
        ...     starting_page="https://www.amazon.com",
        ...     nova_act_key="your-api-key",
        ...     display_size="1080p"
        ... )
    """
    # 参数验证
    if not prompt or not prompt.strip():
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "prompt不能为空"
        }, ensure_ascii=False)
    
    if display_size not in BrowserViewerServer.DISPLAY_SIZES:
        valid_sizes = ", ".join(BrowserViewerServer.DISPLAY_SIZES.keys())
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": f"display_size必须是以下之一: {valid_sizes}"
        }, ensure_ascii=False)
    
    client = None
    viewer = None
    
    try:
        console.print(f"[cyan]🚀 启动浏览器会话 (region={region})...[/cyan]")
        
        # 创建浏览器客户端
        client = BrowserClient(region)
        client.start()
        
        # 获取WebSocket连接信息
        ws_url, headers = client.generate_ws_headers()
        console.print(f"[green]✅ WebSocket连接已建立[/green]")
        
        # 启动viewer服务器
        console.print(f"[cyan]📺 启动实时视图服务器 (port={viewer_port}, size={display_size})...[/cyan]")
        viewer = BrowserViewerServer(client, port=viewer_port)
        viewer_url = viewer.start(open_browser=open_browser, display_size=display_size)
        console.print(f"[green]✅ 实时视图可访问: {viewer_url}[/green]")
        
        # 使用Nova Act执行操作
        console.print(f"[cyan]🤖 执行操作: {prompt}[/cyan]")
        with NovaAct(
            cdp_endpoint_url=ws_url,
            cdp_headers=headers,
            preview={"playwright_actuation": True},
            nova_act_api_key=nova_act_key,
            starting_page=starting_page
        ) as nova_act:
            result = nova_act.act(prompt)
        
        console.print(f"[green]✅ 操作完成[/green]")
        
        # 提取结果数据
        result_data = {
            "response": result.response if hasattr(result, 'response') else str(result),
            "status_code": getattr(result, 'status_code', None),
            "screenshots": getattr(result, 'screenshots', []),
            "metadata": getattr(result, 'metadata', {})
        }
        
        return json.dumps({
            "status": "success",
            "response": result_data["response"],
            "viewer_url": viewer_url,
            "data": result_data
        }, ensure_ascii=False, indent=2)
    
    except OSError as e:
        if "already in use" in str(e).lower():
            console.print(f"[red]❌ 端口冲突: {e}[/red]")
            return json.dumps({
                "status": "error",
                "error_type": "ResourceError",
                "message": f"端口 {viewer_port} 已被占用，请选择其他端口"
            }, ensure_ascii=False)
        raise
    
    except Exception as e:
        console.print(f"[red]❌ 错误: {e}[/red]")
        logger.exception("Error in browser_with_live_view_nova")
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, ensure_ascii=False)
    
    finally:
        if viewer:
            try:
                viewer.stop()
                console.print("[yellow]📺 实时视图服务器已关闭[/yellow]")
            except Exception as e:
                logger.error(f"Error stopping viewer: {e}")
        
        if client:
            try:
                client.stop()
                console.print("[yellow]🔌 浏览器会话已关闭[/yellow]")
            except Exception as e:
                logger.error(f"Error stopping client: {e}")


# 异步实现函数（内部使用）
async def _async_browser_with_live_view_use(
    task: str,
    region: str,
    viewer_port: int,
    open_browser: bool,
    model_id: str,
    timeout: int
) -> dict:
    """
    Browser Use AI驱动自动化的异步实现
    
    Args:
        task: 自然语言任务描述
        region: AWS区域
        viewer_port: viewer端口
        open_browser: 是否自动打开浏览器
        model_id: Bedrock模型ID
        timeout: 超时时间（秒）
        
    Returns:
        dict: 执行结果字典
    """
    client = None
    viewer = None
    browser_session = None
    
    try:
        console.print(f"[cyan]🚀 启动浏览器会话 (region={region})...[/cyan]")
        
        # 创建浏览器客户端
        client = BrowserClient(region)
        client.start()
        
        # 获取WebSocket连接信息
        ws_url, headers = client.generate_ws_headers()
        console.print(f"[green]✅ WebSocket连接已建立[/green]")
        
        # 启动viewer服务器
        console.print(f"[cyan]📺 启动实时视图服务器 (port={viewer_port})...[/cyan]")
        viewer = BrowserViewerServer(client, port=viewer_port)
        viewer_url = viewer.start(open_browser=open_browser)
        console.print(f"[green]✅ 实时视图可访问: {viewer_url}[/green]")
        
        # 创建浏览器配置和会话
        console.print("[cyan]🔄 初始化浏览器会话...[/cyan]")
        browser_profile = BrowserProfile(
            headers=headers,
            timeout=timeout * 1000  # 转换为毫秒
        )
        
        browser_session = BrowserSession(
            cdp_url=ws_url,
            browser_profile=browser_profile,
            keep_alive=True  # 持久化会话
        )
        
        await browser_session.start()
        console.print("[green]✅ 浏览器会话已初始化[/green]")
        
        # 创建Bedrock模型
        console.print(f"[cyan]🤖 创建AI模型 ({model_id})...[/cyan]")
        bedrock_chat = ChatBedrockConverse(
            model_id=model_id,
            region_name=region
        )
        
        # 创建Agent并执行任务
        console.print(f"[cyan]🎯 执行任务: {task}[/cyan]")
        agent = Agent(
            task=task,
            llm=bedrock_chat,
            browser_session=browser_session
        )
        
        # 执行任务（带超时控制）
        await asyncio.wait_for(agent.run(), timeout=timeout)
        console.print("[green]✅ 任务完成[/green]")
        
        return {
            "status": "success",
            "task": task,
            "viewer_url": viewer_url,
            "message": "任务执行成功"
        }
    
    finally:
        # 清理资源
        if browser_session:
            with suppress(Exception):
                await browser_session.close()
                console.print("[yellow]🔌 浏览器会话已关闭[/yellow]")
        
        if viewer:
            with suppress(Exception):
                viewer.stop()
                console.print("[yellow]📺 实时视图服务器已关闭[/yellow]")
        
        if client:
            with suppress(Exception):
                client.stop()
                console.print("[yellow]🔌 客户端已关闭[/yellow]")


@tool
def browser_with_live_view_use(
    task: str,
    region: str = "us-west-2",
    viewer_port: int = 8000,
    open_browser: bool = True,
    model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
    timeout: int = 1500
) -> str:
    """
    使用Browser Use和Claude 3.5 Sonnet进行AI驱动的浏览器自动化
    
    支持复杂的多步骤任务执行，AI会自动决策和导航。提供实时视图功能。
    
    Args:
        task: 自然语言任务描述（如：'在亚马逊搜索笔记本电脑并比较前5个产品的价格和评分'）
        region: AWS区域，默认'us-west-2'
        viewer_port: DCV viewer服务器端口，默认8000
        open_browser: 是否自动打开浏览器查看，默认True
        model_id: Bedrock模型ID，默认'anthropic.claude-3-5-sonnet-20240620-v1:0'
        timeout: 浏览器超时时间（秒），默认1500
        
    Returns:
        str: JSON字符串，包含AI执行结果和viewer URL
            成功格式：{"status": "success", "task_result": {...}, "viewer_url": "..."}
    
    Example:
        >>> result = browser_with_live_view_use(
        ...     task="在维基百科搜索'人工智能'并提取定义",
        ...     model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"
        ... )
    """
    # 参数验证
    if not task or not task.strip():
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "task不能为空"
        }, ensure_ascii=False)
    
    if timeout <= 0:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "timeout必须大于0"
        }, ensure_ascii=False)
    
    try:
        # 执行异步任务
        result = asyncio.run(_async_browser_with_live_view_use(
            task, region, viewer_port, open_browser, model_id, timeout
        ))
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except asyncio.TimeoutError:
        console.print(f"[red]❌ 任务超时 (timeout={timeout}s)[/red]")
        return json.dumps({
            "status": "error",
            "error_type": "TimeoutError",
            "message": f"任务执行超时（{timeout}秒）"
        }, ensure_ascii=False)
    
    except Exception as e:
        console.print(f"[red]❌ 错误: {e}[/red]")
        logger.exception("Error in browser_with_live_view_use")
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, ensure_ascii=False)


@tool
def manage_browser_session(
    action: str,
    region: str = "us-west-2",
    session_id: Optional[str] = None
) -> str:
    """
    浏览器会话管理器
    
    提供统一的会话创建、查询、销毁等操作。
    
    Args:
        action: 操作类型，可选值：
            - 'create': 创建新会话
            - 'stop': 停止会话
            - 'get_ws_headers': 获取WebSocket连接信息
            - 'get_status': 查询会话状态
            - 'list_all': 列出所有会话
        region: AWS区域，默认'us-west-2'
        session_id: 会话ID（create操作会自动生成，其他操作需要提供）
        
    Returns:
        str: JSON字符串，包含操作结果和会话信息
            成功格式：{"status": "success", "action": "...", "session_id": "...", ...}
    
    Example:
        >>> # 创建会话
        >>> result = manage_browser_session(action="create", region="us-west-2")
        >>> # 停止会话
        >>> result = manage_browser_session(action="stop", session_id="xxx-xxx-xxx")
    """
    # 参数验证
    valid_actions = ["create", "stop", "get_ws_headers", "get_status", "list_all"]
    if action not in valid_actions:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": f"action必须是以下之一: {', '.join(valid_actions)}"
        }, ensure_ascii=False)
    
    # 获取全局会话存储
    session_store = get_session_store()
    
    try:
        # 执行不同的操作
        if action == "create":
            console.print(f"[cyan]🆕 创建新会话 (region={region})...[/cyan]")
            
            # 创建浏览器客户端
            client = BrowserClient(region)
            client.start()
            
            # 添加到会话存储
            new_session_id = session_store.add_session(client)
            
            # 获取连接信息
            ws_url, headers = client.generate_ws_headers()
            
            console.print(f"[green]✅ 会话创建成功: {new_session_id}[/green]")
            
            return json.dumps({
                "status": "success",
                "action": "create",
                "session_id": new_session_id,
                "ws_url": ws_url,
                "headers": headers,
                "region": region
            }, ensure_ascii=False, indent=2)
        
        elif action == "get_ws_headers":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "error_type": "ValidationError",
                    "message": "get_ws_headers操作需要提供session_id"
                }, ensure_ascii=False)
            
            client = session_store.get_session(session_id)
            if not client:
                return json.dumps({
                    "status": "error",
                    "error_type": "ResourceError",
                    "message": f"会话不存在: {session_id}"
                }, ensure_ascii=False)
            
            ws_url, headers = client.generate_ws_headers()
            
            return json.dumps({
                "status": "success",
                "action": "get_ws_headers",
                "session_id": session_id,
                "ws_url": ws_url,
                "headers": headers
            }, ensure_ascii=False, indent=2)
        
        elif action == "get_status":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "error_type": "ValidationError",
                    "message": "get_status操作需要提供session_id"
                }, ensure_ascii=False)
            
            client = session_store.get_session(session_id)
            exists = client is not None
            
            return json.dumps({
                "status": "success",
                "action": "get_status",
                "session_id": session_id,
                "exists": exists,
                "session_status": "active" if exists else "not_found"
            }, ensure_ascii=False, indent=2)
        
        elif action == "stop":
            if not session_id:
                return json.dumps({
                    "status": "error",
                    "error_type": "ValidationError",
                    "message": "stop操作需要提供session_id"
                }, ensure_ascii=False)
            
            console.print(f"[cyan]🛑 停止会话: {session_id}...[/cyan]")
            
            success = session_store.remove_session(session_id)
            
            if not success:
                return json.dumps({
                    "status": "error",
                    "error_type": "ResourceError",
                    "message": f"会话不存在或已停止: {session_id}"
                }, ensure_ascii=False)
            
            console.print(f"[green]✅ 会话已停止: {session_id}[/green]")
            
            return json.dumps({
                "status": "success",
                "action": "stop",
                "session_id": session_id,
                "message": "会话已成功停止"
            }, ensure_ascii=False, indent=2)
        
        elif action == "list_all":
            all_sessions = session_store.get_all_sessions()
            
            return json.dumps({
                "status": "success",
                "action": "list_all",
                "total_sessions": len(all_sessions),
                "sessions": all_sessions
            }, ensure_ascii=False, indent=2)
    
    except ValueError as e:
        console.print(f"[red]❌ 验证错误: {e}[/red]")
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        console.print(f"[red]❌ 错误: {e}[/red]")
        logger.exception(f"Error in manage_browser_session (action={action})")
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, ensure_ascii=False)


# 异步批量采集实现（内部使用）
async def _async_batch_extract(
    urls: List[str],
    extraction_prompt: str,
    method: str,
    nova_act_key: Optional[str],
    region: str,
    max_concurrent: int
) -> dict:
    """
    批量URL采集的异步实现
    
    Args:
        urls: URL列表
        extraction_prompt: 提取指令
        method: 采集方法（nova_act/browser_use）
        nova_act_key: Nova Act API密钥
        region: AWS区域
        max_concurrent: 最大并发数
        
    Returns:
        dict: 采集结果字典
    """
    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_url(url: str) -> dict:
        """处理单个URL"""
        async with semaphore:
            try:
                console.print(f"[cyan]📥 处理URL: {url}[/cyan]")
                
                if method == "nova_act":
                    # 使用Nova Act（同步调用，在executor中运行）
                    loop = asyncio.get_event_loop()
                    result_str = await loop.run_in_executor(
                        None,
                        browser_with_nova_act,
                        extraction_prompt,
                        url,
                        nova_act_key,
                        region
                    )
                    result = json.loads(result_str)
                else:
                    # 使用Browser Use（异步调用）
                    result_str = await asyncio.wait_for(
                        asyncio.to_thread(
                            browser_with_live_view_use,
                            extraction_prompt,
                            region,
                            8000,
                            False,  # 批量处理时不自动打开浏览器
                            "anthropic.claude-3-5-sonnet-20240620-v1:0",
                            60  # 单个URL超时60秒
                        ),
                        timeout=60
                    )
                    result = json.loads(result_str)
                
                if result.get("status") == "success":
                    console.print(f"[green]✅ 完成: {url}[/green]")
                    return {
                        "url": url,
                        "status": "success",
                        "data": result.get("data") or result.get("task_result"),
                        "error": None
                    }
                else:
                    console.print(f"[yellow]⚠️  失败: {url}[/yellow]")
                    return {
                        "url": url,
                        "status": "failed",
                        "data": None,
                        "error": result.get("message", "未知错误")
                    }
            
            except asyncio.TimeoutError:
                console.print(f"[red]⏱️  超时: {url}[/red]")
                return {
                    "url": url,
                    "status": "failed",
                    "data": None,
                    "error": "处理超时（60秒）"
                }
            
            except Exception as e:
                console.print(f"[red]❌ 错误: {url} - {e}[/red]")
                return {
                    "url": url,
                    "status": "failed",
                    "data": None,
                    "error": str(e)
                }
    
    # 并发处理所有URL
    console.print(f"[cyan]🚀 开始批量处理 {len(urls)} 个URL (并发数={max_concurrent})...[/cyan]")
    results = await asyncio.gather(*[process_url(url) for url in urls], return_exceptions=True)
    
    # 处理异常结果
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "url": urls[i],
                "status": "failed",
                "data": None,
                "error": str(result)
            })
        else:
            processed_results.append(result)
    
    # 统计结果
    success_count = sum(1 for r in processed_results if r["status"] == "success")
    failed_count = len(processed_results) - success_count
    
    console.print(f"[green]✅ 批量处理完成: {success_count} 成功, {failed_count} 失败[/green]")
    
    return {
        "status": "success",
        "total": len(urls),
        "success": success_count,
        "failed": failed_count,
        "results": processed_results
    }


@tool
def batch_extract_from_urls(
    urls: str,
    extraction_prompt: str,
    method: str = "browser_use",
    nova_act_key: Optional[str] = None,
    region: str = "us-west-2",
    max_concurrent: int = 3
) -> str:
    """
    批量从多个URL采集数据
    
    支持并发控制和两种采集方法（Nova Act和Browser Use），单个URL失败
    不影响其他URL的处理。
    
    Args:
        urls: 待采集的URL列表，JSON数组字符串格式
            （如：'["https://example1.com", "https://example2.com"]'）
        extraction_prompt: 数据提取指令（如：'提取产品名称、价格和评分'）
        method: 采集方法，可选'nova_act'或'browser_use'，默认'browser_use'
        nova_act_key: Nova Act API密钥（method='nova_act'时必需）
        region: AWS区域，默认'us-west-2'
        max_concurrent: 最大并发数，默认3
        
    Returns:
        str: JSON字符串，包含所有URL的采集结果
            成功格式：{"status": "success", "total": 10, "success": 9, "failed": 1, "results": [...]}
    
    Example:
        >>> urls_json = '["https://example1.com", "https://example2.com"]'
        >>> result = batch_extract_from_urls(
        ...     urls=urls_json,
        ...     extraction_prompt="提取页面标题",
        ...     method="browser_use",
        ...     max_concurrent=2
        ... )
    """
    # 参数验证
    try:
        urls_list = json.loads(urls)
        if not isinstance(urls_list, list):
            raise ValueError("urls必须是JSON数组字符串")
        if not urls_list:
            raise ValueError("urls列表不能为空")
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": f"urls格式无效（必须是JSON数组字符串）: {str(e)}"
        }, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": str(e)
        }, ensure_ascii=False)
    
    if not extraction_prompt or not extraction_prompt.strip():
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "extraction_prompt不能为空"
        }, ensure_ascii=False)
    
    if method not in ["nova_act", "browser_use"]:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "method必须是'nova_act'或'browser_use'"
        }, ensure_ascii=False)
    
    if method == "nova_act" and not nova_act_key:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "使用nova_act方法时必须提供nova_act_key"
        }, ensure_ascii=False)
    
    if max_concurrent <= 0:
        return json.dumps({
            "status": "error",
            "error_type": "ValidationError",
            "message": "max_concurrent必须大于0"
        }, ensure_ascii=False)
    
    try:
        # 执行异步批量采集
        result = asyncio.run(_async_batch_extract(
            urls_list,
            extraction_prompt,
            method,
            nova_act_key,
            region,
            max_concurrent
        ))
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        console.print(f"[red]❌ 批量采集错误: {e}[/red]")
        logger.exception("Error in batch_extract_from_urls")
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, ensure_ascii=False)


if __name__ == "__main__":
    # 测试代码
    print("浏览器自动化工具集已加载")
    print("可用工具：")
    print("1. browser_with_nova_act")
    print("2. browser_with_live_view_nova")
    print("3. browser_with_live_view_use")
    print("4. manage_browser_session")
    print("5. batch_extract_from_urls")
