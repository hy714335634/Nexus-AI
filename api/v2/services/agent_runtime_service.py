"""
Agent Runtime Service - Agent 运行时调用服务

职责:
- 调用 AgentCore 运行时（流式）
- 调用本地 Agent（流式）
- 统一的流式响应格式
- 支持多轮对话（通过 S3SessionManager）
"""
import json
import logging
import asyncio
import http.client
from typing import Dict, Any, Optional, AsyncGenerator, List
import boto3
from botocore.config import Config

from api.v2.config import settings

logger = logging.getLogger(__name__)


# S3SessionManager 实例缓存
_session_manager_cache: Dict[str, Any] = {}

# Agent 实例缓存（按 session_id + prompt_path 组合）
_agent_instance_cache: Dict[str, Any] = {}


def _get_s3_session_manager(session_id: str):
    """
    获取或创建 S3SessionManager 实例
    
    使用 Strands 官方的 S3SessionManager 实现多轮对话持久化
    
    参数:
        session_id: 会话 ID
    
    返回:
        S3SessionManager 实例，如果未配置 S3 bucket 则返回 None
    """
    if not settings.SESSION_STORAGE_S3_BUCKET:
        logger.warning("SESSION_STORAGE_S3_BUCKET not configured, multi-turn conversation disabled")
        return None
    
    # 检查缓存
    cache_key = f"{settings.SESSION_STORAGE_S3_BUCKET}:{session_id}"
    if cache_key in _session_manager_cache:
        return _session_manager_cache[cache_key]
    
    try:
        from strands.session.s3_session_manager import S3SessionManager
        
        # 创建 S3SessionManager 实例
        # 参数顺序: session_id, bucket, prefix, boto_session, boto_client_config, region_name
        session_manager = S3SessionManager(
            session_id=session_id,
            bucket=settings.SESSION_STORAGE_S3_BUCKET,
            prefix=settings.SESSION_STORAGE_S3_PREFIX,
            region_name=settings.AWS_REGION
        )
        
        logger.info(f"Created S3SessionManager for session {session_id}, bucket: {settings.SESSION_STORAGE_S3_BUCKET}")
        
        # 缓存实例
        _session_manager_cache[cache_key] = session_manager
        
        return session_manager
        
    except ImportError as e:
        logger.error(f"Failed to import S3SessionManager: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to create S3SessionManager: {e}", exc_info=True)
        return None


def _decode_unicode_escapes(text: str) -> str:
    """解码 Unicode 转义序列"""
    if not text:
        return text
    try:
        return text.encode('utf-8').decode('unicode_escape')
    except Exception:
        return text


def _parse_stream_event(chunk: str) -> Optional[Dict[str, Any]]:
    """
    解析流式事件
    
    返回格式:
    - {"type": "text", "content": "..."}
    - {"type": "tool_use", "tool_name": "...", "tool_id": "..."}
    - {"type": "tool_input", "content": "..."}
    - {"type": "tool_end", "tool_name": "...", "tool_input": "..."}
    - {"type": "tool_result", "content": "..."}
    - {"type": "metadata", "usage": {...}}
    - {"type": "message_stop", "stop_reason": "..."}
    - None (忽略的内部事件)
    """
    if not chunk or not chunk.strip():
        return None
    
    chunk = chunk.strip()
    
    # 尝试解析 JSON
    try:
        data = json.loads(chunk)
        
        # 如果解析结果是字符串，检查是否是 Python repr 格式的调试输出
        # 这些字符串包含 'agent': <strands.agent.agent.Agent object 等内容
        if isinstance(data, str):
            # 忽略包含 Agent 对象引用的调试输出
            if "'agent':" in data or "Agent object at" in data:
                return None
            # 忽略包含 AgentResult 的调试输出
            if "AgentResult(" in data or "'result':" in data:
                return None
            # 忽略包含 event_loop_cycle_id 的调试输出
            if "'event_loop_cycle_id':" in data:
                return None
            # 其他字符串作为文本内容返回
            return {"type": "text", "content": data}
        
        # 处理 AgentCore 格式的事件
        if isinstance(data, dict):
            # AgentCore 事件格式: {"event": {"contentBlockDelta": {...}}}
            if 'event' in data:
                event_data = data['event']
                
                # 文本内容增量
                if 'contentBlockDelta' in event_data:
                    delta = event_data['contentBlockDelta'].get('delta', {})
                    text = delta.get('text', '')
                    if text:
                        return {"type": "text", "content": text}
                    # 工具输入增量
                    tool_input = delta.get('toolUse', {}).get('input', '')
                    if tool_input:
                        return {"type": "tool_input", "content": tool_input}
                
                # 工具调用开始
                if 'contentBlockStart' in event_data:
                    start_data = event_data['contentBlockStart']
                    # 检查多种可能的格式:
                    # 格式1: {"start": {"toolUse": {...}}} (AgentCore 格式)
                    # 格式2: {"toolUse": {...}} (直接格式)
                    tool_use = None
                    if 'start' in start_data and isinstance(start_data.get('start'), dict):
                        tool_use = start_data['start'].get('toolUse')
                    elif 'toolUse' in start_data:
                        tool_use = start_data['toolUse']
                    
                    if tool_use:
                        return {
                            "type": "tool_use",
                            "tool_name": tool_use.get('name', 'unknown'),
                            "tool_id": tool_use.get('toolUseId', ''),
                        }
                
                # 内容块结束
                if 'contentBlockStop' in event_data:
                    return {"type": "content_block_stop"}
                
                # 消息结束
                if 'messageStop' in event_data:
                    return {"type": "message_stop", "stop_reason": event_data['messageStop'].get('stopReason')}
                
                # 元数据（包含 token 使用量）
                if 'metadata' in event_data:
                    return {"type": "metadata", "usage": event_data['metadata'].get('usage', {})}
            
            # 处理完整消息（可能包含工具结果）
            if 'message' in data:
                msg = data['message']
                if isinstance(msg, dict):
                    # 检查是否是包含工具结果的用户消息
                    if msg.get('role') == 'user':
                        content = msg.get('content', [])
                        for item in content:
                            if isinstance(item, dict) and 'toolResult' in item:
                                tool_result = item['toolResult']
                                result_content = tool_result.get('content', [])
                                result_text = ""
                                # 调试日志：查看 toolResult 的实际结构
                                logger.info(f"[TOOL_RESULT] toolResult keys: {tool_result.keys() if isinstance(tool_result, dict) else 'N/A'}")
                                logger.info(f"[TOOL_RESULT] result_content type: {type(result_content)}, len: {len(result_content) if hasattr(result_content, '__len__') else 'N/A'}")
                                logger.info(f"[TOOL_RESULT] result_content preview: {str(result_content)[:300]}")
                                for rc in result_content:
                                    logger.info(f"[TOOL_RESULT] item: type={type(rc)}, value={str(rc)[:150]}")
                                    if isinstance(rc, dict) and 'text' in rc:
                                        result_text += rc['text']
                                    elif isinstance(rc, str):
                                        # 处理字符串格式的内容
                                        result_text += rc
                                # 如果 result_content 本身是字符串
                                if isinstance(result_content, str):
                                    result_text = result_content
                                logger.info(f"[TOOL_RESULT] Final result_len={len(result_text)}")
                                return {
                                    "type": "tool_result",
                                    "tool_id": tool_result.get('toolUseId', ''),
                                    "content": result_text
                                }
                # 忽略其他消息类型
                return None
            
            # 处理 Strands SDK 格式（本地 Agent）
            if 'text' in data:
                return {"type": "text", "content": data['text']}
            
            if 'tool_use' in data:
                tool_data = data['tool_use']
                return {
                    "type": "tool_use",
                    "tool_name": tool_data.get('name', 'unknown'),
                    "tool_id": tool_data.get('id', ''),
                    "tool_input": tool_data.get('input', '')
                }
            
            if 'tool_result' in data:
                tool_result = data['tool_result']
                content = tool_result.get('content', '') if isinstance(tool_result, dict) else str(tool_result)
                return {"type": "tool_result", "content": content}
            
            if 'usage' in data:
                return {"type": "metadata", "usage": data['usage']}
            
            if 'content' in data and isinstance(data['content'], list):
                items = []
                for item in data['content']:
                    if item.get('type') == 'text':
                        items.append({"type": "text", "content": item.get('text', '')})
                    elif item.get('type') == 'tool_use':
                        items.append({
                            "type": "tool_use",
                            "tool_name": item.get('name', 'unknown'),
                            "tool_id": item.get('id', ''),
                            "tool_input": json.dumps(item.get('input', {}), ensure_ascii=False)
                        })
                    elif item.get('type') == 'tool_result':
                        items.append({
                            "type": "tool_result",
                            "content": item.get('content', '')
                        })
                if items:
                    return {"type": "multi_content", "items": items}
            
    except json.JSONDecodeError:
        # 非 JSON 格式，忽略
        pass
    
    return None


async def invoke_agentcore_stream(
    runtime_arn: str,
    session_id: str,
    message: str,
    runtime_alias: Optional[str] = None,
    runtime_region: Optional[str] = None,
    user_id: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    调用 AgentCore 运行时（流式）
    
    支持文本和多模态输入（图片、文件等）
    
    Yields:
        Dict with keys:
        - event: "message" | "metrics" | "error" | "done"
        - type: "text" | "tool_use" | "tool_input" | "tool_end" (for message events)
        - data/content: actual content
    """
    
    def _sync_invoke():
        """同步调用 AgentCore"""
        try:
            logger.info(f"Invoking AgentCore: arn={runtime_arn}, session={session_id}")
            
            # 构建 payload
            payload = {"prompt": message}
            if user_id:
                payload["user_id"] = user_id
            
            # 如果有文件，添加到 media 字段
            if files and len(files) > 0:
                media_items = []
                for file_data in files:
                    filename = file_data.get('filename', 'unknown')
                    content_type = file_data.get('content_type', 'application/octet-stream')
                    data = file_data.get('data', '')  # base64编码的内容
                    
                    # 确定媒体类型
                    if content_type.startswith('image/'):
                        media_type = 'image'
                        format_type = content_type.split('/')[-1]
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
                logger.info(f"Added {len(media_items)} media items to payload")
            
            payload_str = json.dumps(payload)
            
            # 配置 boto3 客户端
            config = Config(
                read_timeout=300,  # 5分钟读取超时
                connect_timeout=30,
                retries={'max_attempts': 0}
            )
            
            client = boto3.client(
                "bedrock-agentcore",
                region_name=runtime_region or settings.AWS_REGION,
                config=config
            )
            
            response = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                qualifier=runtime_alias or "DEFAULT",
                runtimeSessionId=session_id,
                contentType="application/json",
                accept="text/event-stream",
                payload=payload_str
            )
            
            return response
            
        except Exception as e:
            logger.error(f"AgentCore invocation failed: {e}", exc_info=True)
            raise
    
    try:
        # 发送连接确认
        yield {"event": "connected", "session_id": session_id}
        
        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_invoke)
        
        content_type = response.get('contentType', '')
        response_stream = response.get('response')
        
        logger.info(f"AgentCore response: content_type={content_type}, has_stream={response_stream is not None}")
        
        if 'text/event-stream' in content_type and response_stream:
            # 使用队列实现真正的流式传输
            import queue
            import threading
            
            event_queue = queue.Queue()
            read_complete = threading.Event()
            
            def _read_stream_to_queue():
                """在后台线程中读取流并放入队列"""
                try:
                    logger.info(f"Starting stream read, stream type: {type(response_stream)}")
                    logger.info(f"Stream has iter_lines: {hasattr(response_stream, 'iter_lines')}")
                    logger.info(f"Stream has iter_chunks: {hasattr(response_stream, 'iter_chunks')}")
                    
                    # 优先使用 iter_lines 进行真正的流式读取
                    if hasattr(response_stream, 'iter_lines'):
                        line_count = 0
                        for line in response_stream.iter_lines():
                            if line:
                                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                                line_count += 1
                                logger.debug(f"Stream line {line_count}: {line_str[:100]}...")
                                event_queue.put(('data', line_str))
                        logger.info(f"Stream read complete, total lines: {line_count}")
                    # 回退：使用 iter_chunks 逐块读取
                    elif hasattr(response_stream, 'iter_chunks'):
                        buffer = ""
                        for chunk in response_stream.iter_chunks():
                            if chunk:
                                chunk_str = chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
                                buffer += chunk_str
                                # 按行分割并处理
                                while '\n' in buffer:
                                    line, buffer = buffer.split('\n', 1)
                                    if line.strip():
                                        event_queue.put(('data', line))
                        # 处理剩余内容
                        if buffer.strip():
                            event_queue.put(('data', buffer))
                    # 最后回退：一次性读取（非流式）
                    elif hasattr(response_stream, 'read'):
                        logger.warning("Using non-streaming read() as fallback")
                        raw = response_stream.read()
                        content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                        for line in content.split('\n'):
                            if line.strip():
                                event_queue.put(('data', line))
                except http.client.IncompleteRead as e:
                    # 处理不完整读取错误，这通常发生在流被提前关闭时
                    logger.warning(f"IncompleteRead during stream: {e}, partial data may have been received")
                    # 尝试处理已读取的部分数据
                    if hasattr(e, 'partial') and e.partial:
                        try:
                            partial_content = e.partial.decode('utf-8') if isinstance(e.partial, bytes) else str(e.partial)
                            for line in partial_content.split('\n'):
                                if line.strip():
                                    event_queue.put(('data', line))
                        except Exception as parse_err:
                            logger.warning(f"Failed to parse partial data: {parse_err}")
                except Exception as e:
                    logger.error(f"Stream read error: {e}", exc_info=True)
                    event_queue.put(('error', str(e)))
                finally:
                    read_complete.set()
                    event_queue.put(('done', None))
            
            # 启动后台读取线程
            read_thread = threading.Thread(target=_read_stream_to_queue, daemon=True)
            read_thread.start()
            
            # 状态跟踪
            current_tool_name = None
            current_tool_id = None
            current_tool_input = ""
            in_tool_use = False
            
            # 从队列中读取并 yield 事件
            while True:
                try:
                    # 使用短超时以便能够响应
                    event_type, data = event_queue.get(timeout=0.1)
                    
                    if event_type == 'done':
                        break
                    elif event_type == 'error':
                        yield {"event": "error", "error": data}
                        break
                    elif event_type == 'data':
                        # 处理 SSE 格式的数据行
                        data_content = data
                        if data.startswith('data: '):
                            data_content = data[6:]
                        elif data.startswith('data:'):
                            data_content = data[5:]
                        
                        # 跳过空数据
                        if not data_content or not data_content.strip():
                            continue
                        
                        # 调试日志：查看原始数据
                        if 'message' in data_content and 'toolResult' in data_content:
                            logger.info(f"[AGENTCORE] Raw toolResult data: {data_content[:500]}")
                        
                        logger.debug(f"Processing event data: {data_content[:100]}...")
                        
                        # 解析事件
                        parsed = _parse_stream_event(data_content)
                        if parsed:
                            parsed_type = parsed.get("type")
                            
                            if parsed_type == "text":
                                yield {
                                    "event": "message",
                                    "type": "text",
                                    "data": parsed.get("content", "")
                                }
                            elif parsed_type == "tool_use":
                                # 工具调用开始，记录状态
                                current_tool_name = parsed.get("tool_name")
                                current_tool_id = parsed.get("tool_id")
                                current_tool_input = ""
                                in_tool_use = True
                                yield {
                                    "event": "message",
                                    "type": "tool_use",
                                    "tool_name": current_tool_name,
                                    "tool_id": current_tool_id
                                }
                            elif parsed_type == "tool_input":
                                # 累积工具输入
                                input_chunk = parsed.get("content", "")
                                current_tool_input += input_chunk
                                yield {
                                    "event": "message",
                                    "type": "tool_input",
                                    "data": input_chunk
                                }
                            elif parsed_type == "tool_end":
                                yield {
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": parsed.get("tool_name"),
                                    "tool_input": parsed.get("tool_input")
                                }
                            elif parsed_type == "tool_result":
                                # 工具执行完成，发送带结果的工具结束事件
                                yield {
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": current_tool_name or "",
                                    "tool_id": parsed.get("tool_id") or current_tool_id or "",
                                    "tool_input": current_tool_input,
                                    "tool_result": parsed.get("content", "")
                                }
                                # 重置工具状态
                                current_tool_name = None
                                current_tool_id = None
                                current_tool_input = ""
                                in_tool_use = False
                            elif parsed_type == "content_block_stop":
                                # 内容块结束
                                # 不在这里发送 tool_end，等待 tool_result 事件
                                # 只有在非工具调用的内容块结束时才需要处理
                                pass
                            elif parsed_type == "message_stop":
                                # 消息结束，但不是整个流结束
                                # Agent 可能会继续下一轮循环
                                yield {
                                    "event": "message",
                                    "type": "message_stop",
                                    "stop_reason": parsed.get("stop_reason", "")
                                }
                            elif parsed_type == "metadata":
                                yield {
                                    "event": "metrics",
                                    "data": parsed.get("usage", {})
                                }
                            elif parsed_type == "multi_content":
                                for item in parsed.get("items", []):
                                    if item["type"] == "text":
                                        yield {
                                            "event": "message",
                                            "type": "text",
                                            "data": item.get("content", "")
                                        }
                                    elif item["type"] == "tool_use":
                                        current_tool_name = item.get("tool_name")
                                        current_tool_id = item.get("tool_id")
                                        current_tool_input = ""
                                        in_tool_use = True
                                        yield {
                                            "event": "message",
                                            "type": "tool_use",
                                            "tool_name": current_tool_name,
                                            "tool_id": current_tool_id
                                        }
                                    elif item["type"] == "tool_result":
                                        yield {
                                            "event": "message",
                                            "type": "tool_end",
                                            "tool_name": current_tool_name or "",
                                            "tool_result": item.get("content", "")
                                        }
                                        # 重置工具状态
                                        current_tool_name = None
                                        current_tool_id = None
                                        current_tool_input = ""
                                        in_tool_use = False
                        
                        # 让出控制权以便其他协程运行
                        await asyncio.sleep(0)
                        
                except queue.Empty:
                    # 队列为空，检查是否读取完成
                    if read_complete.is_set():
                        break
                    # 让出控制权
                    await asyncio.sleep(0.01)
        
        elif response_stream:
            # 非流式响应
            if hasattr(response_stream, 'read'):
                raw = response_stream.read()
                content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            else:
                content = str(response_stream)
            
            yield {"event": "message", "type": "text", "data": content}
        
        # 发送完成信号
        yield {"event": "done"}
        
    except Exception as e:
        logger.error(f"AgentCore stream error: {e}", exc_info=True)
        yield {"event": "error", "error": str(e)}


async def invoke_local_agent_stream(
    agent_id: str,
    agent_path: str,
    session_id: str,
    message: str,
    prompt_path: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    调用本地 Agent（流式）
    
    使用简化的事件处理逻辑：
    - 只处理带 "data" 键的文本事件（避免与 contentBlockDelta 重复）
    - 使用 tool_use_stream 事件处理工具调用
    - 使用 message 事件处理工具结果
    - 支持多轮对话（通过 S3SessionManager 持久化会话历史）
    
    参数:
        agent_id: Agent ID
        agent_path: Agent 代码路径（可选，用于回退）
        session_id: 会话 ID
        message: 用户消息
        prompt_path: 提示词模板路径（优先使用）
    """
    yield {"event": "connected", "session_id": session_id}
    
    try:
        # 构建 Agent 缓存 key（session_id + prompt_path 组合）
        agent_cache_key = f"{session_id}:{prompt_path or agent_path}"
        
        # 尝试从缓存获取 Agent 实例（支持多轮对话复用）
        agent = _agent_instance_cache.get(agent_cache_key)
        
        if agent:
            logger.info(f"Reusing cached agent for session {session_id}, prompt: {prompt_path}")
        else:
            # 首次对话或缓存已清理，需要创建 Agent 实例
            # 获取 S3SessionManager 实例（用于多轮对话）
            session_manager = _get_s3_session_manager(session_id)
            if session_manager:
                logger.info(f"Using S3SessionManager for multi-turn conversation, session: {session_id}")
            else:
                logger.info(f"S3SessionManager not available, single-turn mode for session: {session_id}")
            
            # 从提示词模板创建 Agent
            if prompt_path:
                logger.info(f"Creating agent from prompt template: {prompt_path}")
                try:
                    # 生成唯一的 agent_id 后缀，确保同一 session 中可以多次创建 Agent
                    # 使用时间戳确保唯一性（用户重新打开旧 session 时需要）
                    import time
                    agent_id_suffix = str(int(time.time() * 1000))
                    
                    loop = asyncio.get_event_loop()
                    agent = await loop.run_in_executor(
                        None,
                        lambda: _create_agent_from_template(
                            prompt_path,
                            session_manager,
                            agent_id_suffix
                        )
                    )
                    
                    # 缓存 Agent 实例
                    if agent:
                        _agent_instance_cache[agent_cache_key] = agent
                        logger.info(f"Cached agent instance for key: {agent_cache_key}")
                        
                except Exception as e:
                    logger.warning(f"Failed to create agent from prompt template: {e}")
        
        if not agent:
            logger.warning(f"No valid agent configuration found for {agent_id}")
            yield {
                "event": "error",
                "error": f"Agent {agent_id} 未配置有效的提示词模板路径"
            }
            return
        
        logger.info(f"Successfully created agent for {agent_id}, starting stream...")
        
        # 状态跟踪
        current_tool_name = None
        current_tool_id = None
        current_tool_input = ""
        # 已发送的工具 ID 集合，用于去重
        sent_tool_ids = set()
        
        # 直接使用 agent.stream_async() 处理流式事件
        async for event in agent.stream_async(message):
            if not isinstance(event, dict):
                continue
            
            # 1. 文本数据 - 只处理带 "data" 键的事件
            # 注意：Strands 会同时发送 {"data": "text"} 和 {"event": {"contentBlockDelta": {"delta": {"text": "text"}}}}
            # 我们只处理 "data" 键的事件，避免重复
            if "data" in event and isinstance(event["data"], str):
                text = event["data"]
                if text:
                    yield {
                        "event": "message",
                        "type": "text",
                        "data": text
                    }
                    await asyncio.sleep(0)
                continue  # 处理完 data 事件后跳过其他检查
            
            # 2. 工具流式事件 - type: tool_use_stream
            # 这是工具调用的主要事件源
            if event.get("type") == "tool_use_stream":
                current_tool_info = event.get("current_tool_use", {})
                tool_id = current_tool_info.get("toolUseId", "")
                tool_name = current_tool_info.get("name", "unknown")
                
                # 如果是新工具调用（ID 不同且未发送过）
                if tool_id and tool_id not in sent_tool_ids:
                    current_tool_name = tool_name
                    current_tool_id = tool_id
                    current_tool_input = ""
                    sent_tool_ids.add(tool_id)
                    logger.info(f"Tool use started: {current_tool_name}, id: {current_tool_id}")
                    yield {
                        "event": "message",
                        "type": "tool_use",
                        "tool_name": current_tool_name,
                        "tool_id": current_tool_id
                    }
                    await asyncio.sleep(0)
                
                # 工具输入增量
                delta = event.get("delta", {})
                if "toolUse" in delta:
                    input_chunk = delta["toolUse"].get("input", "")
                    if input_chunk:
                        current_tool_input += input_chunk
                        yield {
                            "event": "message",
                            "type": "tool_input",
                            "tool_id": current_tool_id,
                            "data": input_chunk
                        }
                        await asyncio.sleep(0)
                continue
            
            # 3. 消息事件 - 包含工具结果
            if "message" in event:
                msg = event["message"]
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content", [])
                    
                    # 工具结果在 user 消息中
                    if role == "user":
                        for item in content:
                            if isinstance(item, dict) and "toolResult" in item:
                                tool_result = item["toolResult"]
                                result_content = tool_result.get("content", [])
                                result_text = ""
                                for rc in result_content:
                                    if isinstance(rc, dict) and "text" in rc:
                                        result_text += rc["text"]
                                
                                tool_id_from_result = tool_result.get("toolUseId", current_tool_id or "")
                                logger.info(f"Tool result received: tool_id={tool_id_from_result}, result_len={len(result_text)}")
                                yield {
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": current_tool_name or "",
                                    "tool_id": tool_id_from_result,
                                    "tool_input": current_tool_input,
                                    "tool_result": result_text
                                }
                                await asyncio.sleep(0)
                                
                                # 重置工具状态
                                current_tool_name = None
                                current_tool_id = None
                                current_tool_input = ""
                continue
            
            # 4. Agent 完成
            if "result" in event:
                logger.info(f"Agent completed for session {session_id}, result keys: {event.get('result', {}).keys() if isinstance(event.get('result'), dict) else 'N/A'}")
                continue
            
            # 5. 强制停止
            if event.get("force_stop", False):
                reason = event.get("force_stop_reason", "unknown")
                logger.warning(f"Agent force stopped: {reason}")
                yield {
                    "event": "error",
                    "error": f"Agent 被强制停止: {reason}"
                }
        
        # 流式输出完成，发送 done 事件
        logger.info(f"Stream completed for session {session_id}, sending done event")
        yield {"event": "done"}
        
    except Exception as e:
        logger.error(f"Local agent stream error: {e}", exc_info=True)
        yield {"event": "error", "error": str(e)}
        # 即使出错也发送 done 事件，确保前端能正确结束流式状态
        yield {"event": "done"}


def _create_agent_from_template(prompt_path: str, session_manager=None, agent_id_suffix: str = None):
    """
    从提示词模板创建 Agent（同步函数，用于线程池执行）
    
    参数:
        prompt_path: 提示词模板路径
        session_manager: 会话管理器实例（用于多轮对话）
        agent_id_suffix: Agent ID 后缀，用于确保同一 session 中 agent_id 唯一
    
    返回:
        Agent 实例
    """
    try:
        from nexus_utils.agent_factory import create_agent_from_prompt_template
        
        # 构建额外参数
        extra_params = {
            "nocallback": True,  # 禁用回调以避免干扰流式输出
        }
        
        if session_manager:
            extra_params["session_manager"] = session_manager
        
        # 如果提供了后缀，使用自定义 agent_id 确保唯一性
        # 这样即使用户重新打开旧 session，也能正常创建 Agent
        if agent_id_suffix:
            base_name = prompt_path.split('/')[-1]
            extra_params["agent_id"] = f"{base_name}_{agent_id_suffix}"
        
        # 创建 agent 实例
        agent = create_agent_from_prompt_template(
            agent_name=prompt_path,
            env="production",
            **extra_params
        )
        
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create agent from template {prompt_path}: {e}", exc_info=True)
        raise


def clear_agent_cache_for_session(session_id: str) -> int:
    """
    清理指定会话的 Agent 实例缓存
    
    当会话关闭时调用此函数，释放内存资源
    
    参数:
        session_id: 会话 ID
    
    返回:
        清理的缓存条目数量
    """
    cleared_count = 0
    
    # 清理 Agent 实例缓存
    keys_to_remove = [key for key in _agent_instance_cache if key.startswith(f"{session_id}:")]
    for key in keys_to_remove:
        del _agent_instance_cache[key]
        cleared_count += 1
    
    # 清理 SessionManager 缓存
    sm_keys_to_remove = [key for key in _session_manager_cache if session_id in key]
    for key in sm_keys_to_remove:
        del _session_manager_cache[key]
        cleared_count += 1
    
    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} cache entries for session {session_id}")
    
    return cleared_count
