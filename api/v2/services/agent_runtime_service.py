"""
Agent Runtime Service - Agent 运行时调用服务

职责:
- 调用 AgentCore 运行时（流式）
- 调用本地 Agent（流式）
- 统一的流式响应格式
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
import boto3
from botocore.config import Config

from api.v2.config import settings

logger = logging.getLogger(__name__)


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
    
    # 忽略内部事件（但保留工具结果相关的事件）
    internal_markers = ["'agent':", "'event_loop_cycle_id':", "AgentResult(", "event_loop_metrics"]
    if any(marker in chunk for marker in internal_markers):
        # 检查是否包含工具结果
        if "'tool_result'" not in chunk and '"tool_result"' not in chunk:
            return None
    
    # 忽略初始化事件
    init_markers = ["init_event_loop", "start_event_loop", '"start": true']
    if any(marker in chunk for marker in init_markers):
        return None
    
    # 尝试解析 JSON
    try:
        data = json.loads(chunk)
        
        # 处理 AgentCore 格式的事件
        if isinstance(data, dict):
            # AgentCore 事件格式: {"event": {"contentBlockDelta": {...}}}
            if 'event' in data:
                event_data = data['event']
                
                # 文本内容
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
                    if 'toolUse' in start_data:
                        tool_use = start_data['toolUse']
                        return {
                            "type": "tool_use",
                            "tool_name": tool_use.get('name', 'unknown'),
                            "tool_id": tool_use.get('toolUseId', ''),
                        }
                
                # 内容块结束（可能是工具调用结束）
                if 'contentBlockStop' in event_data:
                    return {"type": "content_block_stop"}
                
                # 消息结束
                if 'messageStop' in event_data:
                    return {"type": "message_stop", "stop_reason": event_data['messageStop'].get('stopReason')}
                
                # 元数据
                if 'metadata' in event_data:
                    return {"type": "metadata", "usage": event_data['metadata'].get('usage', {})}
            
            # 处理 Strands SDK 格式
            # 文本内容
            if 'text' in data:
                return {"type": "text", "content": data['text']}
            
            # 工具调用
            if 'tool_use' in data:
                tool_data = data['tool_use']
                return {
                    "type": "tool_use",
                    "tool_name": tool_data.get('name', 'unknown'),
                    "tool_id": tool_data.get('id', ''),
                    "tool_input": tool_data.get('input', '')
                }
            
            # 工具结果 - 重要：这表示工具执行完成，Agent 可能会继续输出
            if 'tool_result' in data:
                tool_result = data['tool_result']
                content = tool_result.get('content', '') if isinstance(tool_result, dict) else str(tool_result)
                return {"type": "tool_result", "content": content}
            
            # 元数据
            if 'usage' in data:
                return {"type": "metadata", "usage": data['usage']}
            
            # 消息格式
            if 'message' in data:
                # 完整消息，忽略（我们已经通过 delta 获取了内容）
                return None
            
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
        
        # 纯文本
        if isinstance(data, str):
            return {"type": "text", "content": data}
            
    except json.JSONDecodeError:
        # 非 JSON，作为纯文本处理
        if len(chunk) > 0 and not chunk.startswith('{'):
            return {"type": "text", "content": chunk}
    
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
                    if hasattr(response_stream, 'iter_lines'):
                        for line in response_stream.iter_lines(chunk_size=1):
                            if line:
                                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                                event_queue.put(('data', line_str))
                    elif hasattr(response_stream, 'read'):
                        raw = response_stream.read()
                        content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                        for line in content.split('\n'):
                            if line.strip():
                                event_queue.put(('data', line))
                except Exception as e:
                    event_queue.put(('error', str(e)))
                finally:
                    read_complete.set()
                    event_queue.put(('done', None))
            
            # 启动后台读取线程
            read_thread = threading.Thread(target=_read_stream_to_queue, daemon=True)
            read_thread.start()
            
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
                    elif event_type == 'data' and data.startswith('data: '):
                        data_content = data[6:]
                        
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
                                yield {
                                    "event": "message",
                                    "type": "tool_use",
                                    "tool_name": parsed.get("tool_name"),
                                    "tool_id": parsed.get("tool_id")
                                }
                            elif parsed_type == "tool_input":
                                yield {
                                    "event": "message",
                                    "type": "tool_input",
                                    "data": parsed.get("content", "")
                                }
                            elif parsed_type == "tool_end":
                                yield {
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": parsed.get("tool_name"),
                                    "tool_input": parsed.get("tool_input")
                                }
                            elif parsed_type == "tool_result":
                                # 工具执行完成，发送工具结束事件
                                yield {
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": "",
                                    "tool_result": parsed.get("content", "")
                                }
                            elif parsed_type == "content_block_stop":
                                # 内容块结束，可能是工具调用结束
                                yield {
                                    "event": "message",
                                    "type": "tool_end",
                                    "tool_name": "",
                                    "tool_input": ""
                                }
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
                                        yield {
                                            "event": "message",
                                            "type": "tool_use",
                                            "tool_name": item.get("tool_name"),
                                            "tool_id": item.get("tool_id")
                                        }
                                    elif item["type"] == "tool_result":
                                        yield {
                                            "event": "message",
                                            "type": "tool_end",
                                            "tool_name": "",
                                            "tool_result": item.get("content", "")
                                        }
                        
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
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    调用本地 Agent（流式）
    
    TODO: 实现本地 Agent 调用
    """
    yield {"event": "connected", "session_id": session_id}
    
    # 模拟响应
    response = f"[本地 Agent {agent_id}] 收到消息: {message}\n\n这是本地 Agent 的模拟响应。"
    
    for char in response:
        yield {"event": "message", "type": "text", "data": char}
        await asyncio.sleep(0.01)
    
    yield {"event": "done"}
