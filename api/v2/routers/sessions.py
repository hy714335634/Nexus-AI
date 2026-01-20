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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


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
        
        logger.info(f"Agent runtime config: arn={runtime_arn}, alias={runtime_alias}, region={runtime_region}, path={agent_path}")
        
        def _format_sse(data: dict) -> str:
            """格式化 SSE 数据"""
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        
        async def generate():
            """生成流式响应"""
            assistant_chunks = []
            current_tool_name = None
            current_tool_input = ""
            
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
                                yield _format_sse({
                                    "event": "message",
                                    "type": "text",
                                    "data": text_content
                                })
                            
                            elif msg_type == "tool_use":
                                current_tool_name = event.get("tool_name", "unknown")
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_use",
                                    "tool_name": current_tool_name,
                                    "tool_id": event.get("tool_id", "")
                                })
                            
                            elif msg_type == "tool_input":
                                input_chunk = event.get("data", "")
                                current_tool_input += input_chunk
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_input",
                                    "data": input_chunk
                                })
                            
                            elif msg_type == "tool_end":
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": current_tool_name or event.get("tool_name", ""),
                                    "tool_input": current_tool_input or event.get("tool_input", "")
                                })
                                current_tool_name = None
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
                
                elif agent_path:
                    # 使用本地 Agent
                    logger.info(f"Using local agent: {agent_path}")
                    
                    async for event in invoke_local_agent_stream(
                        agent_id=agent_id,
                        agent_path=agent_path,
                        session_id=session_id,
                        message=request.content,
                    ):
                        event_type = event.get("event")
                        
                        if event_type == "connected":
                            yield _format_sse({"event": "connected", "session_id": session_id})
                        
                        elif event_type == "message":
                            msg_type = event.get("type")
                            if msg_type == "text":
                                text_content = event.get("data", "")
                                assistant_chunks.append(text_content)
                                yield _format_sse({
                                    "event": "message",
                                    "type": "text",
                                    "data": text_content
                                })
                        
                        elif event_type == "done":
                            yield _format_sse({"event": "done"})
                
                else:
                    # 没有配置运行时，返回模拟响应
                    logger.warning(f"Agent {agent_id} has no runtime configured, using mock response")
                    
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
                # 保存助手消息
                if assistant_chunks:
                    session_service.add_message(
                        session_id=session_id,
                        role='assistant',
                        content="".join(assistant_chunks)
                    )
        
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
async def close_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    关闭会话
    """
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        
        session_service.close_session(session_id)
        
        return APIResponse(
            success=True,
            message="会话已关闭",
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"关闭会话失败: {str(e)}")
