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
                    if 'toolUse' in start_data:
                        tool_use = start_data['toolUse']
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
            
            # 忽略完整消息（我们已经通过 delta 获取了内容）
            if 'message' in data:
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
                except Exception as e:
                    logger.error(f"Stream read error: {e}", exc_info=True)
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
    prompt_path: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    调用本地 Agent（流式）
    
    使用 create_agent_from_prompt_template 创建 agent 实例，
    并通过 stream_async 实现真正的流式输出
    
    参数:
        agent_id: Agent ID
        agent_path: Agent 代码路径（可选，用于回退）
        session_id: 会话 ID
        message: 用户消息
        prompt_path: 提示词模板路径（优先使用）
    """
    yield {"event": "connected", "session_id": session_id}
    
    try:
        # 尝试从提示词模板创建 Agent
        agent = None
        
        if prompt_path:
            logger.info(f"Creating agent from prompt template: {prompt_path}")
            try:
                # 在线程池中执行同步的 agent 创建
                loop = asyncio.get_event_loop()
                agent = await loop.run_in_executor(
                    None,
                    _create_agent_from_template,
                    prompt_path
                )
            except Exception as e:
                logger.warning(f"Failed to create agent from prompt template: {e}")
        
        if not agent:
            # 回退：返回错误信息
            logger.warning(f"No valid agent configuration found for {agent_id}")
            yield {
                "event": "error",
                "error": f"Agent {agent_id} 未配置有效的提示词模板路径"
            }
            return
        
        logger.info(f"Successfully created agent for {agent_id}, starting stream...")
        
        # 使用队列实现异步流式传输
        import queue
        import threading
        
        event_queue = queue.Queue()
        stream_complete = threading.Event()
        
        def _run_agent_stream():
            """在后台线程中运行 agent 流式调用"""
            try:
                import asyncio as async_lib
                
                # 创建新的事件循环用于后台线程
                new_loop = async_lib.new_event_loop()
                async_lib.set_event_loop(new_loop)
                
                async def _stream_agent():
                    """异步流式调用 agent"""
                    try:
                        async for event in agent.stream_async(message):
                            # 解析 strands agent 的流式事件
                            if isinstance(event, dict):
                                # 处理文本内容
                                if "data" in event:
                                    event_queue.put(("text", event["data"]))
                                # 处理工具调用
                                elif "tool_use" in event:
                                    tool_data = event["tool_use"]
                                    event_queue.put(("tool_use", {
                                        "name": tool_data.get("name", "unknown"),
                                        "id": tool_data.get("id", ""),
                                    }))
                                elif "tool_input" in event:
                                    event_queue.put(("tool_input", event["tool_input"]))
                                elif "tool_result" in event:
                                    event_queue.put(("tool_end", {
                                        "result": event["tool_result"]
                                    }))
                                # 处理 contentBlockDelta 格式
                                elif "contentBlockDelta" in event:
                                    delta = event["contentBlockDelta"].get("delta", {})
                                    text = delta.get("text", "")
                                    if text:
                                        event_queue.put(("text", text))
                                # 处理 content 格式
                                elif "content" in event:
                                    content = event["content"]
                                    if isinstance(content, str):
                                        event_queue.put(("text", content))
                                    elif isinstance(content, list):
                                        for item in content:
                                            if isinstance(item, dict):
                                                if item.get("type") == "text":
                                                    event_queue.put(("text", item.get("text", "")))
                                # 处理 message 格式
                                elif "message" in event:
                                    msg = event["message"]
                                    if isinstance(msg, dict) and "content" in msg:
                                        for item in msg.get("content", []):
                                            if isinstance(item, dict) and item.get("type") == "text":
                                                event_queue.put(("text", item.get("text", "")))
                            elif isinstance(event, str):
                                event_queue.put(("text", event))
                    except Exception as e:
                        logger.error(f"Agent stream error: {e}", exc_info=True)
                        event_queue.put(("error", str(e)))
                
                new_loop.run_until_complete(_stream_agent())
                
            except Exception as e:
                logger.error(f"Agent thread error: {e}", exc_info=True)
                event_queue.put(("error", str(e)))
            finally:
                stream_complete.set()
                event_queue.put(("done", None))
        
        # 启动后台线程
        stream_thread = threading.Thread(target=_run_agent_stream, daemon=True)
        stream_thread.start()
        
        # 从队列中读取并 yield 事件
        current_tool_name = None
        
        while True:
            try:
                event_type, data = event_queue.get(timeout=0.1)
                
                if event_type == "done":
                    break
                elif event_type == "error":
                    yield {"event": "error", "error": data}
                    break
                elif event_type == "text":
                    yield {
                        "event": "message",
                        "type": "text",
                        "data": data
                    }
                elif event_type == "tool_use":
                    current_tool_name = data.get("name", "unknown")
                    yield {
                        "event": "message",
                        "type": "tool_use",
                        "tool_name": current_tool_name,
                        "tool_id": data.get("id", "")
                    }
                elif event_type == "tool_input":
                    yield {
                        "event": "message",
                        "type": "tool_input",
                        "data": data
                    }
                elif event_type == "tool_end":
                    yield {
                        "event": "message",
                        "type": "tool_end",
                        "tool_name": current_tool_name or "",
                        "tool_result": data.get("result", "")
                    }
                    current_tool_name = None
                
                # 让出控制权
                await asyncio.sleep(0)
                
            except queue.Empty:
                if stream_complete.is_set():
                    break
                await asyncio.sleep(0.01)
        
        yield {"event": "done"}
        
    except Exception as e:
        logger.error(f"Local agent stream error: {e}", exc_info=True)
        yield {"event": "error", "error": str(e)}


def _create_agent_from_template(prompt_path: str):
    """
    从提示词模板创建 Agent（同步函数，用于线程池执行）
    
    参数:
        prompt_path: 提示词模板路径
    
    返回:
        Agent 实例
    """
    try:
        from nexus_utils.agent_factory import create_agent_from_prompt_template
        
        # 创建 agent 实例
        agent = create_agent_from_prompt_template(
            agent_name=prompt_path,
            env="production",
            nocallback=True  # 禁用回调以避免干扰流式输出
        )
        
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create agent from template {prompt_path}: {e}", exc_info=True)
        raise
