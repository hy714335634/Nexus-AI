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
    """格式化 SSE 事件，确保中文正确编码"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")


def _decode_unicode_escapes(text: str) -> str:
    """解码 Unicode 转义序列，如 \\u767d\\u8272 -> 白色"""
    if not text:
        return text
    try:
        # 处理双重转义的情况 \\u -> \u
        if '\\u' in text:
            # 使用 unicode_escape 解码
            return text.encode('utf-8').decode('unicode_escape')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return text


def _parse_stream_event(data_content: str) -> Optional[Dict[str, Any]]:
    """
    解析流事件，提取内容并标记类型。

    返回格式:
    - {"type": "text", "content": "..."} - 普通文本内容
    - {"type": "tool_use", "tool_name": "...", "tool_input": {...}} - 工具调用开始
    - {"type": "tool_result", "content": "..."} - 工具调用结果
    - {"type": "thinking", "content": "..."} - 思考过程
    - {"type": "metadata", "usage": {...}} - 元数据（token使用等）
    - None - 应该忽略的内部事件
    """
    import ast
    import re

    # 最早期检查：如果原始字符串包含 Strands SDK 内部标识符，直接跳过
    # 这可以避免解析失败后把整个 dict 字符串当作文本返回
    internal_markers = [
        "'agent':", '"agent":',
        "'event_loop_cycle_id':", '"event_loop_cycle_id":',
        "'request_state':", '"request_state":',
        "'event_loop_cycle_trace':", '"event_loop_cycle_trace":',
        "'event_loop_cycle_span':", '"event_loop_cycle_span":',
        "'model':", '"model":',
        "'messages':", '"messages":',
        "'system_prompt':", '"system_prompt":',
        "'tool_config':", '"tool_config":',
        "<strands.agent.agent.Agent object",
        "<strands.models.bedrock.BedrockModel object",
        "event_loop_parent_cycle_id",
        "AgentResult(stop_reason=",
    ]
    for marker in internal_markers:
        if marker in data_content:
            return None

    def _try_parse(content: str) -> Optional[dict]:
        """尝试解析 JSON 或 Python dict 字符串"""
        # 先尝试 JSON
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试 Python ast.literal_eval（处理单引号 dict）
        # 首先清理不能被 literal_eval 解析的 Python 对象引用
        cleaned = content
        # 移除 Python 对象引用 如 <strands.agent.agent.Agent object at 0x...>
        cleaned = re.sub(r"<[^>]+object at 0x[0-9a-fA-F]+>", "null", cleaned)
        # 移除 UUID 对象引用 如 UUID('...')
        cleaned = re.sub(r"UUID\('([^']+)'\)", r"'\1'", cleaned)
        # 移除 _Span 对象引用
        cleaned = re.sub(r"_Span\([^)]+\)", "null", cleaned)
        # 将 True/False/None 转为 JSON 格式（小写）
        # 注意：只替换独立的单词，不替换字符串中的
        cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
        cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
        cleaned = re.sub(r'\bNone\b', 'null', cleaned)
        # 将单引号替换为双引号（简单处理）
        # 注意：这个简单替换可能在某些边缘情况下不正确
        cleaned = cleaned.replace("'", '"')

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            pass

        # 最后尝试 ast.literal_eval
        try:
            result = ast.literal_eval(content)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError):
            pass

        return None

    parsed = _try_parse(data_content)

    # 如果解析失败，检查是否是普通文本
    if parsed is None:
        stripped = data_content.strip()
        if stripped:
            return {"type": "text", "content": stripped}
        return None

    # 处理双重编码的字符串
    if isinstance(parsed, str):
        inner = _try_parse(parsed)
        if inner and isinstance(inner, dict):
            parsed = inner
        else:
            # 如果是普通字符串，作为文本返回
            return {"type": "text", "content": parsed}

    if not isinstance(parsed, dict):
        return {"type": "text", "content": str(parsed)}

    # 忽略内部事件
    if parsed.get("init_event_loop") or parsed.get("start") or parsed.get("start_event_loop"):
        return None

    # 优先检查：忽略包含 agent、event_loop_cycle_id 等内部字段的事件
    # 这些是 Strands SDK 的内部状态，不应该发送给前端
    internal_keys = {"agent", "event_loop_cycle_id", "request_state", "event_loop_cycle_trace",
                     "event_loop_cycle_span", "model", "messages", "system_prompt", "tool_config",
                     "event_loop_parent_cycle_id"}
    if internal_keys & set(parsed.keys()):
        return None

    # 处理 Strands SDK 的 tool_use_stream 事件（Python dict 格式）
    if parsed.get("type") == "tool_use_stream":
        current_tool = parsed.get("current_tool_use", {})
        tool_name = current_tool.get("name")
        tool_id = current_tool.get("toolUseId", "")
        delta_input = parsed.get("delta", {}).get("toolUse", {}).get("input", "")

        if tool_name:
            # 这是工具调用的开始或输入更新
            return {
                "type": "tool_use",
                "tool_name": tool_name,
                "tool_id": tool_id,
                "tool_input": delta_input,
            }
        return None

    # 处理 Strands SDK 的 data/delta 事件（文本内容）
    if "data" in parsed and "delta" in parsed:
        delta = parsed.get("delta", {})
        if "text" in delta:
            return {"type": "text", "content": delta["text"]}
        # 忽略其他 delta 类型
        return None

    # 处理 event 包装的事件（标准 AgentCore 格式）
    if "event" in parsed:
        event_data = parsed["event"]

        # 文本内容: contentBlockDelta
        if "contentBlockDelta" in event_data:
            delta = event_data["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                return {"type": "text", "content": delta["text"]}
            # 工具输入
            if "toolUse" in delta:
                tool_input = delta["toolUse"].get("input", "")
                return {"type": "tool_input", "content": tool_input}
            return None

        # 工具调用开始: contentBlockStart with toolUse
        if "contentBlockStart" in event_data:
            start_data = event_data["contentBlockStart"].get("start", {})
            if "toolUse" in start_data:
                tool_use = start_data["toolUse"]
                return {
                    "type": "tool_use",
                    "tool_name": tool_use.get("name", "unknown"),
                    "tool_id": tool_use.get("toolUseId", ""),
                }
            return None

        # 内容块结束
        if "contentBlockStop" in event_data:
            return {"type": "block_stop"}

        # 消息开始/结束
        if "messageStart" in event_data or "messageStop" in event_data:
            return None

        # 元数据（token使用等）
        if "metadata" in event_data:
            metadata = event_data["metadata"]
            if "usage" in metadata:
                return {"type": "metadata", "usage": metadata["usage"]}
            return None

    # 处理 result 事件（最终结果）
    if "result" in parsed:
        return None  # 忽略最终result，内容已通过delta发送

    # 处理 message 事件（完整消息格式，需要提取内容）
    if "message" in parsed:
        message_data = parsed["message"]
        print(f"   🔍 Processing message event: role={message_data.get('role') if isinstance(message_data, dict) else 'N/A'}")
        if isinstance(message_data, dict):
            role = message_data.get("role", "")
            content = message_data.get("content", [])

            # 只处理 assistant 消息
            if role == "assistant" and isinstance(content, list):
                extracted_parts = []
                for item in content:
                    if isinstance(item, dict):
                        # 提取文本内容
                        if "text" in item:
                            text = item["text"]
                            if text and isinstance(text, str):
                                extracted_parts.append({"type": "text", "content": text})
                        # 提取工具调用
                        elif "toolUse" in item:
                            tool_use = item["toolUse"]
                            if isinstance(tool_use, dict):
                                extracted_parts.append({
                                    "type": "tool_use",
                                    "tool_name": tool_use.get("name", "unknown"),
                                    "tool_id": tool_use.get("toolUseId", ""),
                                    "tool_input": json.dumps(tool_use.get("input", {}), ensure_ascii=False) if tool_use.get("input") else ""
                                })

                # 如果有提取的内容，返回一个特殊的多内容响应
                if extracted_parts:
                    print(f"   ✅ Extracted {len(extracted_parts)} parts from message")
                    if len(extracted_parts) == 1:
                        return extracted_parts[0]
                    else:
                        # 返回多个内容项的标记
                        return {"type": "multi_content", "items": extracted_parts}
                else:
                    print(f"   ⚠️ No content extracted from message, content items: {len(content)}")
            else:
                print(f"   ⚠️ Skipping message: role={role}, content_is_list={isinstance(content, list)}")

            # 忽略 user 消息（工具结果等）
            return None
        return None

    # 其他情况忽略（避免显示原始 dict）
    return None


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
        session_id=str(uuid.uuid4()),  # 使用带连字符的 UUID (36字符) 以满足 AWS runtimeSessionId 最小 33 字符要求
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


async def _invoke_agentcore_runtime_stream(
    *,
    runtime_arn: str,
    runtime_alias: Optional[str],
    runtime_region: Optional[str],
    session_id: str,
    message: str,
    user_id: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
):
    """
    使用 boto3 调用 AgentCore runtime（流式版本）
    支持文本和多模态输入（图片、文件等）

    Yields:
        Tuple[str, Optional[Dict]]: (chunk_text, metrics_or_none)
    """

    def _stream_call():
        try:
            print(f"\n🚀 Invoking AgentCore (streaming):")
            print(f"   ARN: {runtime_arn}")
            print(f"   Session: {session_id}")
            print(f"   Message: {message[:100]}")
            if files:
                print(f"   Files: {len(files)} file(s)")

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
            payload_str = json.dumps(payload)
            print(f"   Calling invoke_agent_runtime...")
            print(f"   Payload: {payload_str[:200]}")

            # 添加 botocore 配置以增加超时
            from botocore.config import Config
            config = Config(
                read_timeout=3000,  # 5分钟读取超时
                connect_timeout=30,  # 30秒连接超时
                retries={'max_attempts': 0}  # 不重试
            )
            client = boto3.client(
                "bedrock-agentcore",
                region_name=runtime_region or settings.AWS_DEFAULT_REGION,
                config=config
            )

            try:
                response = client.invoke_agent_runtime(
                    agentRuntimeArn=runtime_arn,
                    qualifier="DEFAULT",
                    runtimeSessionId=session_id,
                    contentType="application/json",
                    accept="text/event-stream",  # 请求流式响应
                    payload=payload_str
                )
            except Exception as e:
                error_msg = str(e)
                if "ReadTimeout" in error_msg or "read timeout" in error_msg.lower():
                    logger.error(f"Agent runtime timeout after 5 minutes: {error_msg}")
                    raise HTTPException(
                        status_code=504,
                        detail={
                            "code": "AGENT_TIMEOUT",
                            "message": "Agent 执行超时（超过5分钟）",
                            "details": "请简化查询或优化 Agent 工具的性能"
                        }
                    )
                raise

            status_code = response['ResponseMetadata']['HTTPStatusCode']
            print(f"   ✅ Response status: {status_code}")
            logger.info(f"Response status: {status_code}")

            # 检查 contentType 判断响应类型
            content_type = response.get('contentType', '')
            print(f"   Content-Type: {content_type}")

            # 处理 text/event-stream 流式响应
            if 'text/event-stream' in content_type:
                print(f"   📡 Streaming response detected")
                response_stream = response.get('response')
                if response_stream and hasattr(response_stream, 'iter_lines'):
                    for line in response_stream.iter_lines(chunk_size=1):
                        if line:
                            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                            if line_str.startswith('data: '):
                                data_content = line_str[6:]  # 去掉 "data: " 前缀
                                # 尝试解析 JSON 字符串（AgentCore 可能返回 JSON 编码的字符串）
                                try:
                                    parsed = json.loads(data_content)
                                    # 如果解析成功且是字符串，使用解析后的值
                                    if isinstance(parsed, str):
                                        data_content = parsed
                                        # 继续尝试解析（可能是双重编码）
                                        try:
                                            parsed2 = json.loads(data_content)
                                            if isinstance(parsed2, str):
                                                data_content = parsed2
                                        except (json.JSONDecodeError, TypeError):
                                            pass
                                except (json.JSONDecodeError, TypeError):
                                    pass  # 保持原样
                                print(f"   📤 Stream chunk: {data_content[:100]}")
                                yield (data_content, None)
                elif response_stream and hasattr(response_stream, 'read'):
                    # fallback: 一次性读取
                    raw_content = response_stream.read()
                    completion = raw_content.decode('utf-8') if isinstance(raw_content, bytes) else raw_content
                    # 尝试解析 JSON 字符串
                    try:
                        parsed = json.loads(completion)
                        if isinstance(parsed, str):
                            completion = parsed
                    except (json.JSONDecodeError, TypeError):
                        pass
                    yield (completion, None)
            # 处理普通响应
            elif 'response' in response:
                print(f"   Reading non-streaming response...")
                response_stream = response['response']
                if hasattr(response_stream, 'read'):
                    raw = response_stream.read()
                    completion = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                else:
                    completion = str(response_stream)
                # 尝试解析 JSON 字符串
                try:
                    parsed = json.loads(completion)
                    if isinstance(parsed, str):
                        completion = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
                print(f"   ✅ Got response: {len(completion)} characters")
                yield (completion, None)
            elif 'payload' in response:
                # 兼容旧版本
                print(f"   Reading payload stream...")
                payload_stream = response['payload']
                if hasattr(payload_stream, 'read'):
                    raw = payload_stream.read()
                    completion = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                else:
                    completion = str(payload_stream)
                # 尝试解析 JSON 字符串
                try:
                    parsed = json.loads(completion)
                    if isinstance(parsed, str):
                        completion = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
                print(f"   ✅ Got response: {len(completion)} characters")
                yield (completion, None)
            else:
                print(f"   ⚠️ No response/payload in response")
                print(f"   Response keys: {list(response.keys())}\n")

            # 提取指标（如果有的话）
            if 'usage' in response:
                usage = response['usage']
                metrics = {
                    'input_tokens': usage.get('inputTokens', 0),
                    'output_tokens': usage.get('outputTokens', 0),
                }
                yield (None, metrics)

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

    # 使用队列实现真正的流式传输
    import asyncio
    import queue
    import threading

    chunk_queue: queue.Queue = queue.Queue()
    error_holder: list = []

    def run_stream():
        try:
            chunk_count = 0
            for chunk in _stream_call():
                chunk_count += 1
                print(f"   🔄 Queue put chunk #{chunk_count}: {str(chunk)[:80]}")
                chunk_queue.put(chunk)
            print(f"   ✅ Stream completed with {chunk_count} chunks")
        except Exception as e:
            print(f"   ❌ Stream error: {e}")
            error_holder.append(e)
        finally:
            chunk_queue.put(None)  # 结束信号
            print(f"   🏁 Queue end signal sent")

    # 在后台线程中运行同步生成器
    thread = threading.Thread(target=run_stream, daemon=True)
    thread.start()

    # 异步地从队列中读取结果
    yield_count = 0
    while True:
        # 使用 run_in_executor 来非阻塞地等待队列
        try:
            chunk = await asyncio.get_event_loop().run_in_executor(
                None, lambda: chunk_queue.get(timeout=0.1)
            )
            if chunk is None:  # 结束信号
                print(f"   🏁 Received end signal after {yield_count} yields")
                break
            yield_count += 1
            print(f"   📤 Yielding chunk #{yield_count}")
            yield chunk
        except queue.Empty:
            # 队列为空，继续等待
            if not thread.is_alive() and chunk_queue.empty():
                print(f"   ⚠️ Thread dead and queue empty after {yield_count} yields")
                break
            await asyncio.sleep(0.01)

    # 检查是否有错误
    if error_holder:
        print(f"   ❌ Re-raising error: {error_holder[0]}")
        raise error_holder[0]


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
    使用 boto3 调用 AgentCore runtime（非流式版本，保留用于向后兼容）
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
            # payload 是 JSON 字符串（不是 bytes）
            payload_str = json.dumps(payload)
            print(f"   Calling invoke_agent_runtime...")
            print(f"   Payload: {payload_str[:200]}")

            # 添加 botocore 配置以增加超时（处理冷启动和长时间运行的 Agent）
            from botocore.config import Config
            config = Config(
                read_timeout=3000,  # 5分钟读取超时（Agent可能需要调用多个工具）
                connect_timeout=30,  # 30秒连接超时
                retries={'max_attempts': 0}  # 不重试，避免重复调用
            )
            client = boto3.client(
                "bedrock-agentcore",
                region_name=runtime_region or settings.AWS_DEFAULT_REGION,
                config=config
            )

            try:
                response = client.invoke_agent_runtime(
                    agentRuntimeArn=runtime_arn,
                    qualifier="DEFAULT",
                    sessionId=session_id,  # 传递 session_id 以维护对话历史
                    payload=payload_str
                )
            except Exception as e:
                error_msg = str(e)
                if "ReadTimeout" in error_msg or "read timeout" in error_msg.lower():
                    logger.error(f"Agent runtime timeout after 5 minutes: {error_msg}")
                    raise HTTPException(
                        status_code=504,
                        detail={
                            "code": "AGENT_TIMEOUT",
                            "message": "Agent 执行超时（超过5分钟）",
                            "details": "请简化查询或优化 Agent 工具的性能"
                        }
                    )
                raise
            
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            print(f"   ✅ Response status: {status_code}")
            logger.info(f"Response status: {status_code}")

            # 检查 contentType 判断响应类型
            content_type = response.get('contentType', '')
            print(f"   Content-Type: {content_type}")

            completion = ""

            # 处理 text/event-stream 流式响应
            if 'text/event-stream' in content_type:
                print(f"   Reading event stream...")
                content_parts = []
                response_stream = response.get('response')
                if response_stream and hasattr(response_stream, 'iter_lines'):
                    for line in response_stream.iter_lines(chunk_size=1):
                        if line:
                            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                            if line_str.startswith('data: '):
                                data_content = line_str[6:]  # 去掉 "data: " 前缀
                                print(f"   Stream data: {data_content[:100]}")
                                content_parts.append(data_content)
                    completion = "".join(content_parts)
                elif response_stream and hasattr(response_stream, 'read'):
                    # fallback: 一次性读取
                    raw_content = response_stream.read()
                    completion = raw_content.decode('utf-8') if isinstance(raw_content, bytes) else raw_content
                print(f"   ✅ Got event stream response: {len(completion)} characters")

            # 处理普通响应
            elif 'response' in response:
                print(f"   Reading response...")
                response_stream = response['response']
                # response 可能是 StreamingBody 或者已经是字符串/字节
                if hasattr(response_stream, 'read'):
                    raw = response_stream.read()
                    completion = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                else:
                    completion = str(response_stream)
                print(f"   ✅ Got response: {len(completion)} characters")
                print(f"   Preview: {completion[:200]}...\n")
            elif 'payload' in response:
                # 兼容旧版本
                print(f"   Reading payload stream...")
                payload_stream = response['payload']
                if hasattr(payload_stream, 'read'):
                    raw = payload_stream.read()
                    completion = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                else:
                    completion = str(payload_stream)
                print(f"   ✅ Got response: {len(completion)} characters")
                print(f"   Preview: {completion[:200]}...\n")
            else:
                print(f"   ⚠️ No response/payload in response")
                print(f"   Response keys: {list(response.keys())}\n")
            
            logger.info(f"AgentCore response: {completion[:100]}...")

            # 尝试解析响应内容
            # 新格式：handler 直接返回字符串（可能被 JSON 编码为字符串）
            # 旧格式：handler 返回 {"success": True, "response": "..."} 或 {"success": False, "error": "..."}
            final_text = completion
            try:
                parsed = json.loads(completion)
                if isinstance(parsed, str):
                    # 新格式：响应是 JSON 编码的字符串
                    final_text = parsed
                    print(f"   📋 Extracted string from JSON")
                elif isinstance(parsed, dict):
                    if parsed.get("success") and "response" in parsed:
                        # 旧格式：提取 response 字段
                        final_text = parsed["response"]
                        print(f"   📋 Extracted response from JSON (legacy format)")
                    elif not parsed.get("success") and "error" in parsed:
                        # 旧格式：错误情况
                        final_text = f"Error: {parsed['error']}"
                        print(f"   ⚠️ Extracted error from JSON (legacy format)")
                    # 如果是其他 JSON 格式，保持原样
            except (json.JSONDecodeError, TypeError):
                # 不是 JSON，直接使用原始字符串
                pass

            # 提取指标（如果有的话）
            metrics = {}
            if 'usage' in response:
                usage = response['usage']
                metrics = {
                    'input_tokens': usage.get('inputTokens', 0),
                    'output_tokens': usage.get('outputTokens', 0),
                }

            return final_text, metrics
            
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
        current_tool_name: Optional[str] = None
        current_tool_input: str = ""

        # 立即发送一个初始事件，确保连接建立
        yield _format_sse({"event": "connected", "session_id": session_id})
        print(f"   📡 SSE connection established for session {session_id}")

        try:
            if runtime_arn:
                # 使用 AgentCore (boto3) - 流式响应
                print(f"✅ Using AgentCore runtime (streaming): {runtime_arn}")
                logger.info(f"✅ Using AgentCore runtime (streaming): {runtime_arn}")
                try:
                    # 从会话中获取 user_id（如果有的话）
                    user_id = session.get('user_id') if isinstance(session, dict) else None

                    # 调用 AgentCore 流式函数
                    async for chunk_text, metrics in _invoke_agentcore_runtime_stream(
                        runtime_arn=runtime_arn,
                        runtime_alias=runtime_alias,
                        runtime_region=runtime_region,
                        session_id=session_id,
                        message=user_message,
                        user_id=user_id,
                        files=files,
                    ):
                        if chunk_text:
                            # 解析事件类型
                            # 只打印前100字符，避免日志过长
                            is_internal = any(m in chunk_text for m in ["'agent':", "'event_loop_cycle_id':", "AgentResult("])
                            if is_internal:
                                print(f"   🔇 Internal event (len={len(chunk_text)})")
                            else:
                                print(f"   📥 Raw chunk ({len(chunk_text)} chars): {chunk_text[:150]}")

                            parsed_event = _parse_stream_event(chunk_text)

                            if parsed_event is None:
                                # 忽略内部事件
                                if not is_internal:
                                    print(f"   ⏭️ Skipped: {chunk_text[:80]}...")
                                continue

                            event_type = parsed_event.get("type")
                            print(f"   ✨ Parsed event: type={event_type}, content={str(parsed_event)[:150]}")

                            if event_type == "text":
                                # 普通文本内容
                                text_content = parsed_event.get("content", "")
                                assistant_chunks.append(text_content)
                                sse_payload = {
                                    "event": "message",
                                    "type": "text",
                                    "data": text_content
                                }
                                print(f"   📤 Sending SSE: {str(sse_payload)[:100]}")
                                yield _format_sse(sse_payload)

                            elif event_type == "tool_use":
                                # 工具调用开始
                                current_tool_name = parsed_event.get("tool_name", "unknown")
                                current_tool_input = ""
                                sse_payload = {
                                    "event": "message",
                                    "type": "tool_use",
                                    "tool_name": current_tool_name,
                                    "tool_id": parsed_event.get("tool_id", "")
                                }
                                print(f"   📤 Sending SSE (tool_use): {current_tool_name}")
                                yield _format_sse(sse_payload)

                            elif event_type == "tool_input":
                                # 工具输入内容（累积）
                                input_chunk = parsed_event.get("content", "")
                                # 解码 Unicode 转义
                                input_chunk = _decode_unicode_escapes(input_chunk)
                                current_tool_input += input_chunk
                                yield _format_sse({
                                    "event": "message",
                                    "type": "tool_input",
                                    "data": input_chunk
                                })

                            elif event_type == "block_stop":
                                # 内容块结束
                                if current_tool_name:
                                    # 工具调用结束，发送完整工具信息
                                    yield _format_sse({
                                        "event": "message",
                                        "type": "tool_end",
                                        "tool_name": current_tool_name,
                                        "tool_input": current_tool_input
                                    })
                                    current_tool_name = None
                                    current_tool_input = ""

                            elif event_type == "multi_content":
                                # 处理包含多个内容项的消息（来自完整 message 格式）
                                items = parsed_event.get("items", [])
                                for idx, item in enumerate(items):
                                    item_type = item.get("type")
                                    if item_type == "text":
                                        text_content = item.get("content", "")
                                        assistant_chunks.append(text_content)
                                        sse_payload = {
                                            "event": "message",
                                            "type": "text",
                                            "data": text_content
                                        }
                                        print(f"   📤 Sending SSE (from multi_content): {str(sse_payload)[:100]}")
                                        yield _format_sse(sse_payload)
                                    elif item_type == "tool_use":
                                        current_tool_name = item.get("tool_name", "unknown")
                                        tool_input = item.get("tool_input", "")
                                        # 确保工具 ID 唯一
                                        tool_id = item.get("tool_id") or f"tool-{uuid.uuid4().hex[:12]}"
                                        sse_payload = {
                                            "event": "message",
                                            "type": "tool_use",
                                            "tool_name": current_tool_name,
                                            "tool_id": tool_id,
                                        }
                                        print(f"   📤 Sending SSE (tool_use from multi_content): {current_tool_name}, id={tool_id}")
                                        yield _format_sse(sse_payload)
                                        # 如果有工具输入，也发送
                                        if tool_input:
                                            yield _format_sse({
                                                "event": "message",
                                                "type": "tool_input",
                                                "data": tool_input
                                            })
                                            yield _format_sse({
                                                "event": "message",
                                                "type": "tool_end",
                                                "tool_name": current_tool_name,
                                                "tool_input": tool_input
                                            })
                                            current_tool_name = None

                            elif event_type == "metadata":
                                # 元数据（token使用等）
                                usage = parsed_event.get("usage", {})
                                if usage:
                                    metrics_snapshot.update({
                                        "input_tokens": usage.get("inputTokens", 0),
                                        "output_tokens": usage.get("outputTokens", 0),
                                    })
                                    yield _format_sse({
                                        "event": "metrics",
                                        "data": metrics_snapshot
                                    })

                        if metrics:
                            # 发送指标
                            metrics_snapshot.update(metrics)
                            yield _format_sse({"event": "metrics", "data": metrics})

                    # 发送完成事件
                    yield _format_sse({"event": "done"})

                except Exception as exc:
                    error_msg = f"AgentCore invocation failed: {str(exc)}"
                    logger.error(error_msg)
                    yield _format_sse({"event": "error", "error": error_msg})
                    return
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

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Transfer-Encoding": "chunked",
        }
    )
