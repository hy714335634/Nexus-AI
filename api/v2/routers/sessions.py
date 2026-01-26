"""
Sessions API Router

会话管理相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Path, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging
from datetime import datetime, timezone
import uuid
import json
import asyncio
import base64

from api.v2.models.schemas import (
    CreateSessionRequest,
    SessionListResponse,
    SessionDetailResponse,
    SendMessageRequest,
    SendMessageResponse,
    MessageListResponse,
    APIResponse,
    FileUploadResponse,
)
from api.v2.services import session_service, agent_service
from api.v2.services.agent_runtime_service import (
    invoke_agentcore_stream,
    invoke_local_agent_stream,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sessions"])

# 工具调用数据大小限制（字符数）
TOOL_INPUT_MAX_LENGTH = 2000
TOOL_RESULT_MAX_LENGTH = 5000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


def _truncate_tool_calls(tool_calls: List[dict]) -> List[dict]:
    """
    截断工具调用数据，防止超过 DynamoDB 大小限制
    
    参数:
        tool_calls: 工具调用列表
    
    返回:
        截断后的工具调用列表
    """
    if not tool_calls:
        return tool_calls
    
    truncated = []
    for tc in tool_calls:
        truncated_tc = tc.copy()
        
        # 截断 input
        if truncated_tc.get("input") and len(truncated_tc["input"]) > TOOL_INPUT_MAX_LENGTH:
            truncated_tc["input"] = truncated_tc["input"][:TOOL_INPUT_MAX_LENGTH] + f"... [truncated, total {len(tc['input'])} chars]"
        
        # 截断 result
        if truncated_tc.get("result") and len(truncated_tc["result"]) > TOOL_RESULT_MAX_LENGTH:
            truncated_tc["result"] = truncated_tc["result"][:TOOL_RESULT_MAX_LENGTH] + f"... [truncated, total {len(tc['result'])} chars]"
        
        truncated.append(truncated_tc)
    
    return truncated


# ============== Agent Sessions ==============

@router.post("/agents/{agent_id}/sessions", response_model=SessionDetailResponse)
async def create_session(
    agent_id: str = Path(..., description="Agent ID"),
    request: CreateSessionRequest = None
):
    """
    为 Agent 创建新会话
    """
    try:
        agent = agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        session = session_service.create_session(
            agent_id=agent_id,
            user_id=request.user_id if request else None,
            display_name=request.display_name if request else None,
            metadata=request.metadata if request else None
        )
        
        return SessionDetailResponse(
            success=True,
            data=session,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/agents/{agent_id}/sessions", response_model=SessionListResponse)
async def list_agent_sessions(
    agent_id: str = Path(..., description="Agent ID"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """
    获取 Agent 的会话列表
    """
    try:
        agent = agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        sessions = session_service.list_sessions(agent_id, limit=limit)
        
        return SessionListResponse(
            success=True,
            data=sessions,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


# ============== Session Operations ==============

@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    获取会话详情
    """
    try:
        session = session_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        
        return SessionDetailResponse(
            success=True,
            data=session,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: str = Path(..., description="会话ID"),
    limit: int = Query(100, ge=1, le=500, description="返回数量")
):
    """
    获取会话消息列表
    """
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        
        messages = session_service.list_messages(session_id, limit=limit)
        
        return MessageListResponse(
            success=True,
            data=messages,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list messages for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取消息列表失败: {str(e)}")


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str = Path(..., description="会话ID"),
    request: SendMessageRequest = None
):
    """
    发送消息到会话
    """
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        
        # 处理文件信息
        metadata = request.metadata or {}
        if request.files:
            metadata['files_count'] = len(request.files)
            metadata['files'] = [
                {'filename': f.filename, 'content_type': f.content_type, 'size': f.size}
                for f in request.files
            ]
        
        message = session_service.add_message(
            session_id=session_id,
            role=request.role,
            content=request.content,
            metadata=metadata
        )
        
        return SendMessageResponse(
            success=True,
            data=message,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message to session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/sessions/{session_id}/upload", response_model=APIResponse)
async def upload_files_to_session(
    session_id: str = Path(..., description="会话ID"),
    files: List[UploadFile] = File(..., description="上传的文件列表"),
):
    """
    上传文件到会话，返回文件信息供后续消息使用
    """
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        
        uploaded_files = []
        
        for file in files:
            try:
                # 读取文件内容
                content = await file.read()
                
                # 转换为base64
                base64_content = base64.b64encode(content).decode('utf-8')
                
                # 构建文件信息
                file_info = {
                    "filename": file.filename,
                    "content_type": file.content_type or "application/octet-stream",
                    "size": len(content),
                    "data": base64_content,
                    "file_id": uuid.uuid4().hex,
                }
                
                uploaded_files.append(file_info)
                logger.info(f"Uploaded file: {file.filename}, size: {len(content)} bytes")
                
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file {file.filename}: {str(e)}"
                )
        
        return APIResponse(
            success=True,
            data=FileUploadResponse(
                files=uploaded_files,
                count=len(uploaded_files),
                session_id=session_id,
            ).model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload files to session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@router.post("/sessions/{session_id}/stream")
async def stream_chat(
    session_id: str = Path(..., description="会话ID"),
    request: SendMessageRequest = None
):
    """
    流式对话
    
    使用 Server-Sent Events (SSE) 返回流式响应
    支持 AgentCore 运行时和本地 Agent
    支持文件上传（图片、文档等）
    """
    logger.info(f"Stream chat request: session_id={session_id}, content={request.content if request else 'None'}")
    
    try:
        session = session_service.get_session(session_id)
        logger.info(f"Session lookup result: {session is not None}, session={session}")
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        
        agent_id = session.get('agent_id')
        logger.info(f"Agent ID from session: {agent_id}")
        agent = agent_service.get_agent(agent_id)
        logger.info(f"Agent lookup result: {agent is not None}")
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        # 处理文件信息
        files_data = None
        metadata = request.metadata or {}
        if request.files:
            files_data = [f.model_dump() for f in request.files]
            metadata['files_count'] = len(request.files)
        
        # 保存用户消息
        session_service.add_message(
            session_id=session_id,
            role='user',
            content=request.content,
            metadata=metadata
        )
        
        # 检查是否是第一条用户消息，如果是则更新会话名称
        # 使用用户输入的前30个字符作为会话名称
        messages = session_service.list_messages(session_id, limit=10)
        user_messages = [m for m in messages if m.get('role') == 'user']
        if len(user_messages) == 1:
            # 这是第一条用户消息，更新会话名称
            new_display_name = request.content[:30].strip()
            if new_display_name:
                # 如果截断后有内容，添加省略号（如果原消息更长）
                if len(request.content) > 30:
                    new_display_name = new_display_name + "..."
                try:
                    session_service.update_session(session_id, {'display_name': new_display_name})
                    logger.info(f"Updated session {session_id} display_name to: {new_display_name}")
                except Exception as e:
                    logger.warning(f"Failed to update session display_name: {e}")
        
        # 获取 Agent 运行时配置
        # 支持两种格式：直接字段或 agentcore_config 嵌套对象
        agentcore_config = agent.get("agentcore_config") or {}
        runtime_arn = (
            agent.get("agentcore_runtime_arn") or 
            agent.get("agentcore_arn") or
            agentcore_config.get("agent_arn") or
            agentcore_config.get("runtime_arn")
        )
        runtime_alias = (
            agent.get("agentcore_runtime_alias") or 
            agent.get("agentcore_alias") or
            agentcore_config.get("alias") or
            "DEFAULT"
        )
        runtime_region = (
            agent.get("agentcore_region") or 
            agent.get("region") or
            agentcore_config.get("region")
        )
        agent_path = agent.get("agent_path")
        prompt_path = agent.get("prompt_path")
        
        logger.info(f"Agent runtime config: arn={runtime_arn}, alias={runtime_alias}, region={runtime_region}, path={agent_path}, prompt={prompt_path}")
        
        def _format_sse(data: dict) -> str:
            """格式化 SSE 数据"""
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        
        async def generate():
            """生成流式响应"""
            assistant_chunks = []
            current_tool_name = None
            current_tool_id = ""
            current_tool_input = ""
            # 用于保存工具调用信息到数据库
            tool_calls_for_db = []
            # 用于保存内容块顺序（文本和工具调用的交替顺序）
            content_blocks_for_db = []
            # 当前文本块 ID
            current_text_block_id = None
            
            try:
                if runtime_arn:
                    # 使用 AgentCore 运行时
                    logger.info(f"Using AgentCore runtime: {runtime_arn}")
                    
                    async for event in invoke_agentcore_stream(
                        runtime_arn=runtime_arn,
                        session_id=session_id,
                        message=request.content,
                        runtime_alias=runtime_alias,
                        runtime_region=runtime_region,
                        user_id=session.get('user_id'),
                        files=files_data,
                    ):
                        event_type = event.get("event")
                        
                        if event_type == "connected":
                            yield _format_sse({"event": "connected", "session_id": session_id})
                        
                        elif event_type == "message":
                            msg_type = event.get("type")
                            
                            if msg_type == "text":
                                text_content = event.get("data", "")
                                assistant_chunks.append(text_content)
                                # 更新内容块顺序
                                if not current_text_block_id:
                                    # 创建新的文本块
                                    current_text_block_id = f"text-{len(content_blocks_for_db)}"
                                    content_blocks_for_db.append({
                                        "type": "text",
                                        "id": current_text_block_id,
                                        "text": text_content
                                    })
                                else:
                                    # 追加到现有文本块
                                    for block in content_blocks_for_db:
                                        if block["id"] == current_text_block_id:
                                            block["text"] = block.get("text", "") + text_content
                                            break
                                yield _format_sse({
                                    "event": "message",
                                    "type": "text",
                                    "data": text_content
                                })
                            
                            elif msg_type == "tool_use":
                                current_tool_name = event.get("tool_name", "unknown")
                                current_tool_id = event.get("tool_id", "")
                                current_tool_input = ""
                                # 重置文本块 ID，下次文本会创建新块
                                current_text_block_id = None
                                # 添加新的工具调用记录
                                tool_calls_for_db.append({
                                    "name": current_tool_name,
                                    "id": current_tool_id,
                                    "input": "",
                                    "result": "",
                                    "status": "running"
                                })
                                # 添加工具块到内容块顺序
                                content_blocks_for_db.append({
                                    "type": "tool",
                                    "id": current_tool_id,
                                    "tool_name": current_tool_name
                                })
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_use",
                                    "tool_name": current_tool_name,
                                    "tool_id": current_tool_id
                                })
                            
                            elif msg_type == "tool_input":
                                input_chunk = event.get("data", "")
                                current_tool_input += input_chunk
                                # 更新最后一个工具调用的输入
                                if tool_calls_for_db:
                                    tool_calls_for_db[-1]["input"] = current_tool_input
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_input",
                                    "tool_id": current_tool_id,  # 添加 tool_id 以便前端匹配
                                    "data": input_chunk
                                })
                            
                            elif msg_type == "tool_end":
                                tool_result = event.get("tool_result", "")
                                # 更新最后一个工具调用的结果和状态
                                if tool_calls_for_db:
                                    tool_calls_for_db[-1]["input"] = current_tool_input or event.get("tool_input", "")
                                    tool_calls_for_db[-1]["result"] = tool_result
                                    tool_calls_for_db[-1]["status"] = "success"
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_id": current_tool_id,  # 添加 tool_id 以便前端匹配
                                    "tool_name": current_tool_name or event.get("tool_name", ""),
                                    "tool_input": current_tool_input or event.get("tool_input", ""),
                                    "tool_result": tool_result
                                })
                                current_tool_name = None
                                current_tool_id = ""
                                current_tool_input = ""
                        
                        elif event_type == "metrics":
                            yield _format_sse({
                                "event": "metrics",
                                "data": event.get("data", {})
                            })
                        
                        elif event_type == "error":
                            yield _format_sse({
                                "event": "error",
                                "error": event.get("error", "Unknown error")
                            })
                        
                        elif event_type == "done":
                            yield _format_sse({"event": "done"})
                
                elif agent_path or prompt_path:
                    # 使用本地 Agent
                    logger.info(f"Using local agent: path={agent_path}, prompt={prompt_path}")
                    
                    event_count = 0
                    async for event in invoke_local_agent_stream(
                        agent_id=agent_id,
                        agent_path=agent_path,
                        session_id=session_id,
                        message=request.content,
                        prompt_path=prompt_path,
                    ):
                        event_count += 1
                        event_type = event.get("event")
                        logger.debug(f"[Stream] Event #{event_count}: type={event_type}, msg_type={event.get('type')}")
                        
                        if event_type == "connected":
                            yield _format_sse({"event": "connected", "session_id": session_id})
                        
                        elif event_type == "message":
                            msg_type = event.get("type")
                            
                            if msg_type == "text":
                                text_content = event.get("data", "")
                                assistant_chunks.append(text_content)
                                # 更新内容块顺序
                                if not current_text_block_id:
                                    # 创建新的文本块
                                    current_text_block_id = f"text-{len(content_blocks_for_db)}"
                                    content_blocks_for_db.append({
                                        "type": "text",
                                        "id": current_text_block_id,
                                        "text": text_content
                                    })
                                else:
                                    # 追加到现有文本块
                                    for block in content_blocks_for_db:
                                        if block["id"] == current_text_block_id:
                                            block["text"] = block.get("text", "") + text_content
                                            break
                                yield _format_sse({
                                    "event": "message",
                                    "type": "text",
                                    "data": text_content
                                })
                            
                            elif msg_type == "tool_use":
                                # 工具调用开始
                                current_tool_name = event.get("tool_name", "unknown")
                                current_tool_id = event.get("tool_id", "")
                                current_tool_input = ""
                                # 重置文本块 ID，下次文本会创建新块
                                current_text_block_id = None
                                # 添加新的工具调用记录
                                tool_calls_for_db.append({
                                    "name": current_tool_name,
                                    "id": current_tool_id,
                                    "input": "",
                                    "result": "",
                                    "status": "running"
                                })
                                # 添加工具块到内容块顺序
                                content_blocks_for_db.append({
                                    "type": "tool",
                                    "id": current_tool_id,
                                    "tool_name": current_tool_name
                                })
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_use",
                                    "tool_name": current_tool_name,
                                    "tool_id": current_tool_id
                                })
                            
                            elif msg_type == "tool_input":
                                # 工具输入增量
                                input_chunk = event.get("data", "")
                                # 优先使用事件中的 tool_id，回退到当前跟踪的 tool_id
                                event_tool_id = event.get("tool_id", current_tool_id)
                                current_tool_input += input_chunk
                                # 更新最后一个工具调用的输入
                                if tool_calls_for_db:
                                    tool_calls_for_db[-1]["input"] = current_tool_input
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_input",
                                    "tool_id": event_tool_id,  # 添加 tool_id 以便前端匹配
                                    "data": input_chunk
                                })
                            
                            elif msg_type == "tool_end":
                                # 工具调用结束
                                tool_result = event.get("tool_result", "")
                                event_tool_id = event.get("tool_id", current_tool_id)
                                # 更新对应工具调用的结果和状态
                                if tool_calls_for_db:
                                    # 通过 tool_id 查找并更新
                                    for tc in tool_calls_for_db:
                                        if tc.get("id") == event_tool_id:
                                            tc["input"] = current_tool_input or event.get("tool_input", "")
                                            tc["result"] = tool_result
                                            tc["status"] = "success"
                                            break
                                    else:
                                        # 回退：更新最后一个
                                        tool_calls_for_db[-1]["input"] = current_tool_input or event.get("tool_input", "")
                                        tool_calls_for_db[-1]["result"] = tool_result
                                        tool_calls_for_db[-1]["status"] = "success"
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_id": event_tool_id,
                                    "tool_name": current_tool_name or event.get("tool_name", ""),
                                    "tool_input": current_tool_input or event.get("tool_input", ""),
                                    "tool_result": tool_result
                                })
                                current_tool_name = None
                                current_tool_id = ""
                                current_tool_input = ""
                        
                        elif event_type == "error":
                            yield _format_sse({
                                "event": "error",
                                "error": event.get("error", "Unknown error")
                            })
                        
                        elif event_type == "done":
                            logger.info(f"[Stream] Received done event from local agent, total events: {event_count}")
                            yield _format_sse({"event": "done"})
                
                else:
                    # 没有配置运行时，返回模拟响应
                    logger.warning(f"Agent {agent_id} has no runtime configured (no arn, path, or prompt), using mock response")
                    
                    yield _format_sse({"event": "connected", "session_id": session_id})
                    
                    response_text = f"[Agent {agent_id}] 收到消息: {request.content}\n\n此 Agent 尚未配置运行时，无法处理请求。"
                    
                    for char in response_text:
                        assistant_chunks.append(char)
                        yield _format_sse({
                            "event": "message",
                            "type": "text",
                            "data": char
                        })
                        await asyncio.sleep(0.01)
                    
                    yield _format_sse({"event": "done"})
                
            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                yield _format_sse({
                    "event": "error",
                    "error": str(e)
                })
            
            finally:
                # 异步保存助手消息（包含工具调用信息和内容块顺序）
                # 使用后台任务，不阻塞流式响应
                if assistant_chunks:
                    # 构建消息元数据
                    message_metadata = {}
                    
                    # 保存工具调用信息（截断大型数据）
                    if tool_calls_for_db:
                        message_metadata["tool_calls"] = _truncate_tool_calls(tool_calls_for_db)
                    
                    # 保存内容块顺序（用于前端恢复文本和工具调用的交替顺序）
                    # 注意：不截断文本内容，保持完整性
                    if content_blocks_for_db:
                        message_metadata["content_blocks"] = content_blocks_for_db
                    
                    # 准备保存数据
                    final_content = "".join(assistant_chunks)
                    final_metadata = message_metadata if message_metadata else None
                    final_session_id = session_id
                    
                    # 定义异步保存函数
                    async def save_message_async():
                        """后台异步保存消息到数据库"""
                        try:
                            session_service.add_message(
                                session_id=final_session_id,
                                role='assistant',
                                content=final_content,
                                metadata=final_metadata
                            )
                            logger.info(f"Assistant message saved to session {final_session_id}")
                        except Exception as save_error:
                            # 如果保存失败，记录错误但不影响流式响应
                            logger.error(f"Failed to save assistant message: {save_error}")
                    
                    # 在后台执行保存操作，不阻塞
                    asyncio.create_task(save_message_async())
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stream chat for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"流式对话失败: {str(e)}")


@router.delete("/sessions/{session_id}", response_model=APIResponse)
async def delete_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    删除会话及其所有消息
    """
    try:
        result = session_service.delete_session(session_id)
        
        return APIResponse(
            success=True,
            message=f"会话已删除，共删除 {result.get('deleted_messages_count', 0)} 条消息",
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")
