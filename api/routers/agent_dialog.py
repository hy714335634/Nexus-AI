from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError
import httpx
from fastapi import APIRouter, HTTPException, Path, Request, status, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.core.config import settings
from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import AgentSessionMessageRecord, AgentSessionRecord

router = APIRouter()
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _utc_now() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def _isoformat(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    iso = value.astimezone(timezone.utc).isoformat()
    if iso.endswith("+00:00"):
        iso = iso[:-6] + "Z"
    return iso


def _success_payload(data: Any) -> Dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "timestamp": _isoformat(_utc_now()),
        "request_id": uuid.uuid4().hex,
    }


def _format_sse(event: Dict[str, Any]) -> bytes:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")


def _get_db() -> DynamoDBClient:
    return DynamoDBClient()


def _coerce_metadata(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {"raw": value}


# --------------------------------------------------------------------------- #
# Pydantic models for responses
# --------------------------------------------------------------------------- #


class AgentSessionItem(BaseModel):
    session_id: str
    display_name: Optional[str] = None
    created_at: str
    last_active_at: Optional[str] = None


class AgentSessionListResponse(BaseModel):
    sessions: list[AgentSessionItem] = Field(default_factory=list)


class AgentSessionCreatePayload(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=120)


class AgentMessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentMessageListResponse(BaseModel):
    messages: list[AgentMessageItem] = Field(default_factory=list)


class AgentContextResponse(BaseModel):
    agent_id: str
    display_name: Optional[str] = None
    system_prompt_path: Optional[str] = None
    code_path: Optional[str] = None
    tools_path: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    runtime_model_id: Optional[str] = None
    agentcore_runtime_arn: Optional[str] = None
    agentcore_runtime_alias: Optional[str] = None
    agentcore_region: Optional[str] = None


class AgentStreamRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入的对话内容")
    files: Optional[List[Dict[str, Any]]] = Field(default=None, description="上传的文件列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "请分析这张图片",
                "files": [
                    {
                        "filename": "image.jpg",
                        "content_type": "image/jpeg",
                        "data": "base64_encoded_content..."
                    }
                ]
            }
        }


# --------------------------------------------------------------------------- #
# Session management
# --------------------------------------------------------------------------- #


@router.get("/agents/{agent_id}/sessions")
async def list_agent_sessions(agent_id: str = Path(..., description="Agent ID")):
    db = _get_db()
    result = db.list_agent_sessions(agent_id, limit=100)
    sessions: list[AgentSessionItem] = []
    for entry in result.get("items", []):
        sessions.append(
            AgentSessionItem(
                session_id=entry["session_id"],
                display_name=entry.get("display_name"),
                created_at=_isoformat(entry.get("created_at")) or "",
                last_active_at=_isoformat(entry.get("last_active_at")),
            )
        )
    return _success_payload(AgentSessionListResponse(sessions=sessions).dict())


@router.post("/agents/{agent_id}/sessions", status_code=status.HTTP_201_CREATED)
async def create_agent_session(
    payload: AgentSessionCreatePayload,
    agent_id: str = Path(..., description="Agent ID"),
):
    db = _get_db()
    created_at = _utc_now()
    session_record = AgentSessionRecord(
        agent_id=agent_id,
        session_id=uuid.uuid4().hex,
        display_name=payload.display_name or f"会话 {created_at.strftime('%H:%M')}",
        created_at=created_at,
        last_active_at=created_at,
        metadata={},
    )
    db.create_agent_session(session_record)
    return _success_payload(
        AgentSessionItem(
            session_id=session_record.session_id,
            display_name=session_record.display_name,
            created_at=_isoformat(session_record.created_at) or "",
            last_active_at=_isoformat(session_record.last_active_at),
        ).dict()
    )


def _ensure_session(agent_id: str, session_id: str) -> Dict[str, Any]:
    db = _get_db()
    session = db.get_agent_session(agent_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/agents/{agent_id}/sessions/{session_id}/messages")
async def get_session_messages(
    agent_id: str = Path(..., description="Agent ID"),
    session_id: str = Path(..., description="Session ID"),
):
    _ensure_session(agent_id, session_id)
    db = _get_db()
    result = db.list_session_messages(session_id, limit=500, ascending=True)
    messages: list[AgentMessageItem] = []
    for entry in result.get("items", []):
        messages.append(
            AgentMessageItem(
                message_id=entry["message_id"],
                role=entry.get("role", "assistant"),
                content=entry.get("content", ""),
                created_at=_isoformat(entry.get("created_at")) or "",
                metadata=_coerce_metadata(entry.get("metadata")),
            )
        )
    return _success_payload(AgentMessageListResponse(messages=messages).dict())


# --------------------------------------------------------------------------- #
# Agent context
# --------------------------------------------------------------------------- #


@router.get("/agents/{agent_id}/context")
async def get_agent_context(agent_id: str = Path(..., description="Agent ID")):
    db = _get_db()
    record = db.get_agent(agent_id)
    if not record:
        return _success_payload(AgentContextResponse(agent_id=agent_id).dict())

    tags = record.get("tags") or (record.get("metadata") or {}).get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    payload = AgentContextResponse(
        agent_id=agent_id,
        display_name=record.get("display_name") or record.get("agent_name"),
        system_prompt_path=record.get("prompt_path"),
        code_path=record.get("code_path"),
        tools_path=record.get("tools_path"),
        description=record.get("description"),
        tags=list(tags),
        runtime_model_id=record.get("runtime_model_id"),
        agentcore_runtime_arn=record.get("agentcore_runtime_arn") or record.get("agentcore_arn"),
        agentcore_runtime_alias=record.get("agentcore_runtime_alias") or record.get("agentcore_alias"),
        agentcore_region=record.get("agentcore_region") or record.get("region"),
    )
    return _success_payload(payload.dict())


@router.get("/agents/{agent_id}/runtime/health")
async def check_agent_runtime_health(agent_id: str = Path(..., description="Agent ID")):
    """检查 Agent 运行时健康状态"""
    db = _get_db()
    agent_record = db.get_agent(agent_id)
    
    if not agent_record:
        return {
            "success": False,
            "error": {
                "code": "AGENT_NOT_FOUND",
                "message": f"Agent '{agent_id}' not found in database"
            }
        }
    
    runtime_arn = agent_record.get("agentcore_runtime_arn") or agent_record.get("agentcore_arn")
    entrypoint = agent_record.get("entrypoint") or agent_record.get("code_path")
    
    health_status = {
        "agent_id": agent_id,
        "agent_name": agent_record.get("agent_name"),
        "status": agent_record.get("status"),
        "has_agentcore_arn": bool(runtime_arn),
        "has_entrypoint": bool(entrypoint),
        "runtime_type": "agentcore" if runtime_arn else "local_http",
        "agentcore_arn": runtime_arn if runtime_arn else None,
        "entrypoint": entrypoint if entrypoint else None,
        "is_ready": bool(runtime_arn or entrypoint),
    }
    
    return _success_payload(health_status)


@router.post("/agents/{agent_id}/sessions/{session_id}/upload")
async def upload_files_to_session(
    agent_id: str = Path(..., description="Agent ID"),
    session_id: str = Path(..., description="Session ID"),
    files: List[UploadFile] = File(..., description="上传的文件列表"),
):
    """
    上传文件到会话，返回文件信息供后续消息使用
    """
    import base64
    
    _ensure_session(agent_id, session_id)
    
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
    
    return _success_payload({
        "files": uploaded_files,
        "count": len(uploaded_files),
        "session_id": session_id,
    })


# --------------------------------------------------------------------------- #
# Streaming proxy
# --------------------------------------------------------------------------- #


async def _invoke_agentcore_runtime(
    *,
    runtime_arn: str,
    runtime_alias: Optional[str],
    runtime_region: Optional[str],
    session_id: str,
    message: str,
    user_id: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    使用 boto3 调用 AgentCore runtime
    支持文本和多模态输入（图片、文件等）
    """

    def _call() -> Tuple[str, Dict[str, Any]]:
        try:
            print(f"\n🚀 Invoking AgentCore:")
            print(f"   ARN: {runtime_arn}")
            print(f"   Session: {session_id}")
            print(f"   Message: {message[:100]}")
            if files:
                print(f"   Files: {len(files)} file(s)")
            
            # 使用 bedrock-agentcore 服务（不是 bedrock-agent-runtime）
            client = boto3.client(
                "bedrock-agentcore",
                region_name=runtime_region or settings.AWS_DEFAULT_REGION
            )
            
            # 构建 payload（AgentCore 标准格式）
            payload = {"prompt": message}
            
            # 如果有文件，添加到 media 字段
            if files and len(files) > 0:
                media_items = []
                for file_data in files:
                    # 提取文件信息
                    filename = file_data.get('filename', 'unknown')
                    content_type = file_data.get('content_type', 'application/octet-stream')
                    data = file_data.get('data', '')  # base64编码的内容
                    
                    # 确定媒体类型
                    if content_type.startswith('image/'):
                        media_type = 'image'
                        format_type = content_type.split('/')[-1]  # jpeg, png, etc.
                    elif content_type.startswith('audio/'):
                        media_type = 'audio'
                        format_type = content_type.split('/')[-1]
                    elif content_type.startswith('video/'):
                        media_type = 'video'
                        format_type = content_type.split('/')[-1]
                    else:
                        media_type = 'document'
                        format_type = filename.split('.')[-1] if '.' in filename else 'bin'
                    
                    media_items.append({
                        'type': media_type,
                        'format': format_type,
                        'data': data,
                        'filename': filename
                    })
                
                payload['media'] = media_items
                print(f"   Media items: {len(media_items)}")
            
            print(f"   Payload keys: {list(payload.keys())}\n")
            
            logger.info(f"Invoking AgentCore: arn={runtime_arn}, session={session_id}")
            logger.info(f"Payload: query={message[:100]}, media_count={len(files) if files else 0}")
            
            # 调用 invoke_agent_runtime
            print(f"   Calling invoke_agent_runtime...")
            response = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                payload=json.dumps(payload)
            )
            
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            print(f"   ✅ Response status: {status_code}")
            logger.info(f"Response status: {status_code}")
            
            # 读取 payload 流
            completion = ""
            if 'payload' in response:
                print(f"   Reading payload stream...")
                payload_stream = response['payload']
                completion = payload_stream.read().decode('utf-8')
                print(f"   ✅ Got response: {len(completion)} characters")
                print(f"   Preview: {completion[:200]}...\n")
            else:
                print(f"   ⚠️ No payload in response")
                print(f"   Response keys: {list(response.keys())}\n")
            
            logger.info(f"AgentCore response: {completion[:100]}...")
            
            # 提取指标（如果有的话）
            metrics = {}
            if 'usage' in response:
                usage = response['usage']
                metrics = {
                    'input_tokens': usage.get('inputTokens', 0),
                    'output_tokens': usage.get('outputTokens', 0),
                }
            
            return completion, metrics
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            print(f"\n❌ AgentCore ClientError:")
            print(f"   Code: {error_code}")
            print(f"   Message: {error_message}\n")
            logger.error(f"AgentCore invocation failed: {error_code} - {error_message}")
            raise Exception(f"AgentCore error: {error_code} - {error_message}")
        except Exception as e:
            print(f"\n❌ AgentCore Exception: {str(e)}\n")
            logger.error(f"AgentCore invocation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    return await asyncio.to_thread(_call)


async def _proxy_http_runtime(
    *,
    agent_id: str,
    session_id: str,
    message: str,
    request: Request,
) -> AsyncGenerator[Tuple[bytes, Optional[Dict[str, Any]]], None]:
    """Forward request to local runtime via HTTP and yield SSE bytes with parsed payload."""
    runtime_url = settings.AGENT_RUNTIME_URL.rstrip("/") + "/invocations"
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Session-Id": session_id,
        "X-Agent-Id": agent_id,
    }
    payload = {"prompt": message, "streaming": True}

    timeout = httpx.Timeout(None, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(runtime_url, headers=headers, json=payload, stream=True)
        if response.status_code >= 400:
            body = await response.aread()
            error_payload = {
                "event": "error",
                "error": f"Runtime returned {response.status_code}",
                "details": body.decode("utf-8"),
            }
            yield _format_sse(error_payload), error_payload
            return

        buffer = ""
        async for line in response.aiter_lines():
            if await request.is_disconnected():
                break
            if line is None:
                continue
            buffer += line + "\n"

            while "\n\n" in buffer:
                raw_event, buffer = buffer.split("\n\n", 1)
                raw_event = raw_event.strip()
                if not raw_event:
                    continue

                data_line = None
                for row in raw_event.split("\n"):
                    row = row.strip()
                    if row.startswith("data:"):
                        data_line = row[5:].strip()
                        break

                parsed = None
                if data_line:
                    try:
                        parsed = json.loads(data_line)
                    except json.JSONDecodeError:
                        parsed = None

                yield (raw_event + "\n\n").encode("utf-8"), parsed


@router.post(
    "/agents/{agent_id}/sessions/{session_id}/stream",
    response_class=StreamingResponse,
)
async def stream_agent_response(
    payload: AgentStreamRequest,
    request: Request,
    agent_id: str = Path(..., description="Agent ID"),
    session_id: str = Path(..., description="Session ID"),
):
    print(f"\n{'='*80}")
    print(f"🔵 STREAM REQUEST: agent_id={agent_id}, session_id={session_id}")
    print(f"   Message: {payload.message[:100]}")
    print(f"{'='*80}\n")
    logger.info(f"Stream request received for agent_id={agent_id}, session_id={session_id}")
    
    db = _get_db()
    session = _ensure_session(agent_id, session_id)

    user_message = payload.message.strip()
    if not user_message:
        logger.warning(f"Empty message received for agent_id={agent_id}")
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # 提取文件信息
    files = payload.files or []
    
    now = _utc_now()
    user_message_record = AgentSessionMessageRecord(
        session_id=session_id,
        message_id=uuid.uuid4().hex,
        agent_id=agent_id,
        role="user",
        content=user_message,
        metadata={"files_count": len(files)} if files else {},
        created_at=now,
    )
    db.append_session_message(user_message_record)
    db.update_agent_session_activity(agent_id, session_id, last_active_at=now)

    agent_record = db.get_agent(agent_id)
    if not agent_record:
        logger.error(f"Agent not found in database: agent_id={agent_id}")
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found in database")
    
    logger.info(f"Agent record found: agent_name={agent_record.get('agent_name')}, status={agent_record.get('status')}")

    runtime_arn = agent_record.get("agentcore_runtime_arn") or agent_record.get("agentcore_arn")
    runtime_alias = agent_record.get("agentcore_runtime_alias") or agent_record.get("agentcore_alias")
    runtime_region = agent_record.get("agentcore_region") or agent_record.get("region")
    
    # 添加详细日志（使用 print 确保能看到）
    print(f"\n🔍 Agent Runtime Config:")
    print(f"   agentcore_runtime_arn: {agent_record.get('agentcore_runtime_arn')}")
    print(f"   agentcore_arn: {agent_record.get('agentcore_arn')}")
    print(f"   runtime_arn (final): {runtime_arn}")
    print(f"   runtime_alias: {runtime_alias}")
    print(f"   runtime_region: {runtime_region}\n")
    
    logger.info(f"Agent runtime config:")
    logger.info(f"  agentcore_runtime_arn: {agent_record.get('agentcore_runtime_arn')}")
    logger.info(f"  agentcore_arn: {agent_record.get('agentcore_arn')}")
    logger.info(f"  runtime_arn (final): {runtime_arn}")
    logger.info(f"  runtime_alias: {runtime_alias}")
    logger.info(f"  runtime_region: {runtime_region}")

    async def event_stream():
        assistant_chunks: list[str] = []
        metrics_snapshot: Dict[str, Any] = {}

        try:
            if runtime_arn:
                # 使用 AgentCore (boto3)
                print(f"✅ Using AgentCore runtime: {runtime_arn}")
                logger.info(f"✅ Using AgentCore runtime: {runtime_arn}")
                try:
                    # 从会话中获取 user_id（如果有的话）
                    user_id = session.get('user_id') if isinstance(session, dict) else None
                    
                    # 调用 AgentCore（支持文件）
                    text, runtime_metrics = await _invoke_agentcore_runtime(
                        runtime_arn=runtime_arn,
                        runtime_alias=runtime_alias,
                        runtime_region=runtime_region,
                        session_id=session_id,
                        message=user_message,
                        user_id=user_id,
                        files=files,
                    )
                    
                    # 分块发送响应（模拟流式效果）
                    if text:
                        assistant_chunks.append(text)
                        # 将响应分成小块发送
                        chunk_size = 50
                        for i in range(0, len(text), chunk_size):
                            chunk = text[i:i+chunk_size]
                            yield _format_sse({"event": "message", "data": chunk})
                            await asyncio.sleep(0.01)  # 小延迟，模拟流式效果
                    
                    # 发送指标
                    if runtime_metrics:
                        metrics_snapshot.update(runtime_metrics)
                        yield _format_sse({"event": "metrics", "data": runtime_metrics})
                    
                    # 发送完成事件
                    yield _format_sse({"event": "done"})
                    
                except Exception as exc:
                    error_msg = f"AgentCore invocation failed: {str(exc)}"
                    logger.error(error_msg)
                    yield _format_sse({"event": "error", "error": error_msg})
                    return
            else:
                # 使用本地 HTTP runtime
                print(f"⚠️ No AgentCore ARN found, using local HTTP runtime")
                print(f"   AGENT_RUNTIME_URL: {settings.AGENT_RUNTIME_URL}")
                logger.warning(f"⚠️ No AgentCore ARN found, using local HTTP runtime")
                logger.warning(f"   AGENT_RUNTIME_URL: {settings.AGENT_RUNTIME_URL}")
                async for event_bytes, parsed in _proxy_http_runtime(
                    agent_id=agent_id,
                    session_id=session_id,
                    message=user_message,
                    request=request,
                ):
                    if parsed:
                        event_type = parsed.get("event")
                        if event_type == "message":
                            assistant_chunks.append(str(parsed.get("data", "")))
                        elif event_type == "metrics":
                            metrics_snapshot.update(parsed.get("data") or {})
                    yield event_bytes
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"Stream error: {str(exc)}", exc_info=True)
            error_payload = {"event": "error", "error": str(exc)}
            yield _format_sse(error_payload)
        finally:
            # 保存助手消息
            if assistant_chunks:
                assistant_message = AgentSessionMessageRecord(
                    session_id=session_id,
                    message_id=uuid.uuid4().hex,
                    agent_id=agent_id,
                    role="assistant",
                    content="".join(assistant_chunks),
                    metadata={"metrics": metrics_snapshot},
                    created_at=_utc_now(),
                )
                db.append_session_message(assistant_message)
                db.update_agent_session_activity(agent_id, session_id, last_active_at=_utc_now())

    return StreamingResponse(event_stream(), media_type="text/event-stream")
