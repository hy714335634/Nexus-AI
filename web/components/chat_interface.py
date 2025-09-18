#!/usr/bin/env python3
"""
聊天界面组件 - 代理对话的UI组件
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
import re
import pandas as pd
import subprocess
import threading
import time
import yaml
from typing import List, Dict, Optional, Iterator, Any
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from datetime import datetime
import time
import threading
import queue

def render_chat_interface(agent_id: str, agent_name: str = "AI代理", agent_service=None) -> None:
    """渲染完整的聊天界面"""
    
    # 初始化聊天历史和会话状态
    chat_key = f"chat_history_{agent_id}"
    session_key = f"chat_session_{agent_id}"
    
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            'session_id': f"{agent_id}_{int(datetime.now().timestamp())}",
            'created_at': datetime.now().isoformat(),
            'agent_id': agent_id,
            'agent_name': agent_name,
            'status': 'active',
            'message_count': 0,
            'last_activity': datetime.now().isoformat()
        }
    
    # 渲染会话管理器
    render_session_manager(agent_id, agent_name)
    print(f"agent_id: {agent_id}")
    # 聊天历史显示区域
    render_chat_history(st.session_state[chat_key], agent_id)
    
    # 聊天输入区域
    user_input = render_chat_input(agent_id, agent_name)
    
    # 处理用户输入
    if user_input and agent_service:
        handle_user_input(user_input, agent_id, agent_name, agent_service)
    
    # 聊天控制面板
    render_chat_controls(agent_id, agent_name)



def render_enhanced_chat_interface(agent_id: str, agent_name: str = "AI代理") -> None:
    """渲染增强的聊天界面，集成代理调用功能"""
    
    # 初始化聊天历史
    chat_key = f"chat_history_{agent_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    
    # 获取代理信息
    available_agents = get_available_agents()
    agent_info = next((agent for agent in available_agents if agent['id'] == agent_id), None)
    
    if not agent_info:
        st.error(f"未找到代理信息: {agent_id}")
        return
    
    # 添加现代化聊天界面的CSS样式
    st.markdown("""
    <style>
    
    .chat-messages {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        max-height: 600px;
        overflow-y: auto;
        margin-bottom: 15px;
    }
    
    .message-bubble {
        margin-bottom: 15px;
        padding: 15px;
        border-radius: 15px;
        max-width: 80%;
        position: relative;
    }
    
    .message-bubble.user {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        margin-left: auto;
        text-align: right;
    }
    
    .message-bubble.assistant {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        margin-right: auto;
    }
    
    .message-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-weight: 600;
        font-size: 0.9em;
    }
    
    .message-bubble.user .message-header {
        color: rgba(255, 255, 255, 0.9);
        justify-content: flex-end;
    }
    
    .message-bubble.assistant .message-header {
        color: #667eea;
    }
    
    .message-time {
        font-size: 0.8em;
        opacity: 0.7;
    }
    
    .message-content {
        line-height: 1.5;
    }
    
    .analysis-section {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin-top: 10px;
        border-left: 4px solid #667eea;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
    }
    
    .analysis-section h3, .analysis-section h2 {
        color: #667eea;
        margin-top: 0;
        margin-bottom: 10px;
    }
    
    .analysis-title {
        font-weight: 600;
        color: #667eea;
        margin-bottom: 8px;
    }
    
    .status-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 10px;
        padding: 8px 0;
        border-top: 1px solid rgba(102, 126, 234, 0.2);
        font-size: 0.85em;
        color: #666;
    }
    
    .welcome-message {
        text-align: center;
        padding: 30px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 15px;
        margin-bottom: 20px;
    }
    
    .welcome-message h3 {
        color: #667eea;
        margin-bottom: 10px;
    }
    
    .welcome-message p {
        color: #666;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 调试设置面板
    render_debug_settings(agent_id)
    
    # 创建聊天容器
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
    
    # 显示欢迎消息（仅在首次访问时）
    if not st.session_state[chat_key]:
        st.markdown(f"""
        <div class="welcome-message">
            <h3>👋 欢迎使用 {agent_name}</h3>
            <p>我是您的AI助手，很高兴为您服务！请告诉我您需要什么帮助。</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 显示所有历史消息
    for message in st.session_state[chat_key]:
        render_modern_chat_message(message, agent_name)
    
    st.markdown('</div>', unsafe_allow_html=True)  # 结束 chat-messages
    
    # 处理用户输入
    user_input = st.chat_input(f"与 {agent_name} 对话...")
    
    # 如果有用户输入，立即处理并显示
    if user_input:
        # 立即添加用户消息到历史并重新运行，让用户消息立即显示
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state[chat_key].append(user_message)
        
        # 标记正在处理代理响应
        st.session_state[f"processing_{agent_id}"] = True
        
        # 立即重新运行以显示用户消息
        st.rerun()
    
    # 检查是否需要处理代理响应
    if st.session_state.get(f"processing_{agent_id}", False):
        # 获取最后一条用户消息
        last_message = st.session_state[chat_key][-1] if st.session_state[chat_key] else None
        
        if last_message and last_message['role'] == 'user':
            # 显示代理正在思考的状态
            with st.chat_message("assistant"):
                with st.spinner("🤔 代理正在思考..."):
                    # 获取代理响应
                    start_time = time.time()
                    response_content = render_enhanced_agent_response(agent_info, last_message['content'])
                    processing_time = time.time() - start_time
                    
                    # 添加代理响应到历史
                    assistant_message = {
                        'role': 'assistant',
                        'content': response_content,
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {
                            'processing_time': f"{processing_time:.1f}s",
                            'tokens_used': len(response_content.split()),
                            'agent_id': agent_id
                        }
                    }
                    st.session_state[chat_key].append(assistant_message)
                    
                    # 清除处理状态
                    st.session_state[f"processing_{agent_id}"] = False
                    
                    # 重新运行以显示代理响应
                    st.rerun()
    
    # 聊天控制面板
    render_chat_controls(agent_id, agent_name)

def render_chat_history(chat_history: List[Dict], agent_id: str) -> None:
    """渲染聊天历史"""
    
    if not chat_history:
        st.info("💬 开始与代理对话吧！")
        return
    
    # 获取显示设置
    show_timestamps = st.session_state.get(f"show_timestamps_{agent_id}", True)
    show_metadata = st.session_state.get(f"show_metadata_{agent_id}", True)
    
    # 按顺序显示所有消息
    for i, message in enumerate(chat_history):
        render_chat_message(message, i, show_timestamps, show_metadata)

def render_chat_message(message: Dict, message_index: int, show_timestamps: bool = True, show_metadata: bool = True) -> None:
    """渲染单条聊天消息"""
    
    role = message.get('role', 'user')
    content = message.get('content', '')
    timestamp = message.get('timestamp', '')
    metadata = message.get('metadata', {})
    message_type = message.get('type', 'text')  # text, json, table, error
    
    if role == 'user':
        # 用户消息
        with st.chat_message("user"):
            render_message_content(content, message_type)
            if show_timestamps and timestamp:
                st.caption(f"发送时间: {format_timestamp(timestamp)}")
    
    else:
        # 代理消息
        with st.chat_message("assistant"):
            render_message_content(content, message_type)
            
            # 显示元数据
            if show_metadata and metadata:
                render_message_metadata(metadata)
            
            if show_timestamps and timestamp:
                st.caption(f"回复时间: {format_timestamp(timestamp)}")

def render_message_content(content: str, message_type: str = 'text') -> None:
    """渲染消息内容，支持不同格式"""
    
    if message_type == 'json':
        # JSON格式数据
        try:
            json_data = json.loads(content) if isinstance(content, str) else content
            st.json(json_data)
        except:
            st.code(content, language='json')
    
    elif message_type == 'table':
        # 表格数据
        try:
            if isinstance(content, str):
                # 尝试解析CSV格式或JSON格式的表格数据
                if content.startswith('[') or content.startswith('{'):
                    data = json.loads(content)
                    if isinstance(data, list):
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.json(data)
                else:
                    # CSV格式
                    lines = content.strip().split('\n')
                    if len(lines) > 1:
                        headers = lines[0].split(',')
                        rows = [line.split(',') for line in lines[1:]]
                        df = pd.DataFrame(rows, columns=headers)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.write(content)
            else:
                st.dataframe(content, use_container_width=True)
        except:
            st.write(content)
    
    elif message_type == 'error':
        # 错误消息
        st.error(content)
    
    elif message_type == 'code':
        # 代码块
        language = 'python'  # 默认语言
        if '```' in content:
            # 提取语言标识
            lines = content.split('\n')
            if lines[0].startswith('```'):
                language = lines[0][3:].strip() or 'python'
                content = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else '\n'.join(lines[1:])
        st.code(content, language=language)
    
    else:
        # 普通文本，支持Markdown
        # 检查是否包含特殊格式
        if '|' in content and '\n' in content:
            # 可能是Markdown表格
            try:
                lines = content.strip().split('\n')
                if len(lines) >= 2 and '|' in lines[0] and '|' in lines[1]:
                    st.markdown(content)
                    return
            except:
                pass
        
        # 检查是否包含JSON数据
        json_pattern = r'```json\s*(.*?)\s*```'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        if json_matches:
            # 分离文本和JSON
            parts = re.split(json_pattern, content)
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    # 文本部分
                    if part.strip():
                        st.markdown(part)
                else:
                    # JSON部分
                    try:
                        json_data = json.loads(part)
                        st.json(json_data)
                    except:
                        st.code(part, language='json')
        else:
            st.markdown(content)

def render_message_metadata(metadata: Dict) -> None:
    """渲染消息元数据"""
    
    cols = st.columns(4)
    
    with cols[0]:
        processing_time = metadata.get('processing_time', '')
        if processing_time:
            st.caption(f"⏱️ 处理时间: {processing_time}")
    
    with cols[1]:
        tokens_used = metadata.get('tokens_used', '')
        if tokens_used:
            st.caption(f"🔤 Token使用: {tokens_used}")
    
    with cols[2]:
        model_used = metadata.get('model_used', '')
        if model_used:
            st.caption(f"🤖 模型: {model_used}")
    
    with cols[3]:
        status = metadata.get('status', '')
        if status:
            status_icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
            st.caption(f"{status_icon} 状态: {status}")

def render_session_manager(agent_id: str, agent_name: str) -> None:
    """渲染会话管理器"""
    
    with st.expander("📋 会话管理", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 会话搜索
            search_query = st.text_input("🔍 搜索消息", key=f"search_{agent_id}")
            if search_query:
                search_results = search_chat_history(agent_id, search_query)
                if search_results:
                    st.write(f"找到 {len(search_results)} 条匹配消息:")
                    for idx, result in enumerate(search_results[:5]):  # 显示前5条
                        with st.container():
                            st.caption(f"消息 #{result['index']} - {result['role']}")
                            st.text(result['content'][:100] + "..." if len(result['content']) > 100 else result['content'])
                else:
                    st.info("未找到匹配的消息")
        
        with col2:
            # 会话统计
            chat_history = get_chat_history(agent_id)
            st.metric("总消息数", len(chat_history))
            
            if chat_history:
                user_count = len([msg for msg in chat_history if msg['role'] == 'user'])
                st.metric("用户消息", user_count)
                st.metric("代理回复", len(chat_history) - user_count)
        
        with col3:
            # 会话控制
            session_info = st.session_state.get(f"chat_session_{agent_id}", {})
            st.write(f"**会话状态:** {session_info.get('status', 'unknown')}")
            st.write(f"**创建时间:** {format_timestamp(session_info.get('created_at', ''))}")
            
            if st.button("暂停会话", key=f"pause_{agent_id}"):
                pause_chat_session(agent_id)
                st.success("会话已暂停")
            
            if st.button("恢复会话", key=f"resume_{agent_id}"):
                resume_chat_session(agent_id)
                st.success("会话已恢复")

def render_chat_input(agent_id: str, agent_name: str) -> Optional[str]:
    """渲染聊天输入框"""
    
    # 检查会话状态
    session_info = st.session_state.get(f"chat_session_{agent_id}", {})
    if session_info.get('status') == 'paused':
        st.warning("⏸️ 会话已暂停，请先恢复会话")
        return None
    
    # 聊天输入
    user_input = st.chat_input(f"与 {agent_name} 对话...")
    
    return user_input

def call_agent_with_input(agent_info: Dict, user_input: str, show_debug_logs: bool = False) -> Iterator[str]:
    """调用代理并返回流式响应 - 通过脚本调用已存在的代理
    
    Args:
        agent_info: 代理信息字典，包含script_path等完整信息
        user_input: 用户输入
        show_debug_logs: 是否显示调试日志
    """
    try:
        # 直接使用传入的代理脚本路径
        from pathlib import Path
        agent_path = Path(agent_info['script_path'])
        agent_id = agent_info['id']
        agent_name = agent_info['name']
        
        if not agent_path.exists():
            yield f"❌ 错误: 代理脚本不存在: {agent_path}"
            return
        
        # 准备环境变量，确保Python路径正确
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        env['BYPASS_TOOL_CONSENT'] = "true"
        
        # 检测代理的参数格式
        input_param, has_interactive = _smart_detect_agent_parameter(agent_path)
        
        # 准备命令
        venv_python = project_root / "venv" / "bin" / "python"
        
        # 构建命令
        if input_param is None and has_interactive:
            # 纯交互模式，不需要参数，通过stdin传递输入
            if venv_python.exists():
                cmd = [str(venv_python), str(agent_path)]
            else:
                cmd = [sys.executable, str(agent_path)]
            use_stdin = True
        else:
            # 命令行参数模式
            if venv_python.exists():
                cmd = [str(venv_python), str(agent_path), input_param, user_input]
            else:
                cmd = [sys.executable, str(agent_path), input_param, user_input]
            use_stdin = False
        
        # 输出启动信息（在调试模式下显示）
        if show_debug_logs:
            yield f"🚀 启动代理: {agent_id}"
            yield f"📁 工作目录: {project_root}"
            yield f"🐍 Python: {cmd[0]}"
            yield f"📜 代理脚本: {agent_path}"
            
            if use_stdin:
                yield f"⚙️ 模式: 交互模式 (通过stdin传递输入)"
            else:
                yield f"⚙️ 参数: {input_param} '{user_input[:50]}...'"
            
            yield f"{'='*50}"
        
        # 启动进程
        try:
            if use_stdin:
                # 交互模式，需要stdin
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(project_root),
                    env=env,
                    bufsize=0,
                    universal_newlines=True
                )
                
                # 向stdin发送用户输入
                try:
                    process.stdin.write(user_input + "\n")
                    process.stdin.write("exit\n")  # 发送退出命令
                    process.stdin.flush()
                    process.stdin.close()
                except Exception as e:
                    yield f"⚠️ 发送输入失败: {str(e)}"
            else:
                # 命令行参数模式
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(project_root),
                    env=env,
                    bufsize=0,
                    universal_newlines=True
                )
        except Exception as e:
            yield f"❌ 启动进程失败: {str(e)}"
            return

        # 收集所有输出用于分析
        all_output = []
        agent_response_started = False
        agent_response_lines = []
        
        while True:
            output = process.stdout.readline()
            
            if output == '' and process.poll() is not None:
                break
            
            if output:
                line = output.strip()
                all_output.append(line)
                
                # 输出调试信息（显示所有日志）
                if show_debug_logs:
                    # 显示所有输出，不过滤
                    yield f"🔧 [LOG] {line}"
                
                # 通用的代理响应检测逻辑 - 不依赖特定的代理类型
                # 使用更通用的模式来检测代理响应
                response_indicators = [
                    # 通用响应标志
                    "Agent response:", "代理响应:", "Response:", "响应:",
                    # 用户请求处理
                    "用户请求:", "User request:", "处理请求:", "Processing request:",
                    # 分析和处理（通用词汇）
                    "分析", "Analysis", "处理", "Processing", "结果", "Result", "输出", "Output",
                    # 方案和报告（通用）
                    "方案", "Solution", "报告", "Report", "建议", "Recommendation",
                    # 常见表情符号标志
                    "📋", "📊", "🎯", "💡", "✅", "🔍", "📈", "📉", "💰", "🔧"
                ]
                
                # 检测是否包含响应指示符
                if any(indicator in line for indicator in response_indicators):
                    agent_response_started = True
                    agent_response_lines.append(line)
                    continue
                
                # 简化的系统信息过滤 - 只过滤明显的启动信息
                startup_patterns = [
                    "Creating agent", "Loaded prompt", "Successfully loaded",
                    "Agent创建成功", "tools available", "Parse command line"
                ]
                
                # 只在响应未开始时过滤启动信息
                if not agent_response_started and any(pattern in line for pattern in startup_patterns):
                    continue
                
                # 收集所有有意义的内容
                if line.strip():  # 非空行
                    if agent_response_started or len(line.strip()) > 10:  # 响应已开始或内容足够长
                        agent_response_lines.append(line)
        
        # 检查返回码
        return_code = process.poll()
        
        if show_debug_logs:
            yield f"{'='*50}"
            yield f"✅ 代理执行完成，返回码: {return_code}"
            
            if return_code != 0:
                yield f"❌ 代理执行异常，返回码: {return_code}"
            
            # 输出最终结果标题
            yield f"{'='*50}"
            yield f"📋 **代理响应结果:**"
            yield f"{'='*50}"
        
        # 智能输出处理：优先显示代理响应，如果没有则显示所有有意义的输出
        if agent_response_lines:
            # 显示检测到的代理响应
            for line in agent_response_lines:
                yield line
        else:
            # 如果没有检测到明确的代理响应，显示所有非系统信息的输出
            meaningful_output = []
            for line in all_output:
                if line.strip():
                    # 过滤掉明显的系统信息和调试标记
                    if not any(prefix in line for prefix in [
                        "🔧 [LOG]", "🚀", "📁", "🐍", "📜", "⚙️", "Creating agent", 
                        "Loaded prompt", "Successfully", "Warning:", "tools available"
                    ]):
                        meaningful_output.append(line)
            
            if meaningful_output:
                for line in meaningful_output:
                    yield line
            else:
                # 如果连有意义的输出都没有，显示原始输出供调试
                yield "⚠️ 未检测到明确的代理响应，显示原始输出："
                for line in all_output[-20:]:  # 显示最后20行
                    if line.strip():
                        yield f"  {line}"
            
    except Exception as e:
        yield f"❌ 调用代理失败: {str(e)}"

def get_available_agents() -> List[Dict]:
    """从项目状态JSON文件获取所有可用的代理"""
    agents = []
    projects_status_file = project_root / "web" / "data" / "projects_status.json"
    
    if not projects_status_file.exists():
        return agents
    
    try:
        import json
        with open(projects_status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        projects = status_data.get('projects', [])
        
        for project in projects:
            agent_id = project.get('id')
            agent_name = project.get('name', agent_id.replace('_', ' ').title())
            
            # 只返回状态为running的代理（表示已完成构建）
            if project.get('status') == 'running':
                agent_dir = project_root / "agents" / "generated_agents" / agent_id
                
                # 直接获取文件夹下的唯一.py文件
                agent_script_path = None
                script_name = None
                
                if agent_dir.exists():
                    # 查找文件夹下的.py文件（应该只有一个）
                    py_files = list(agent_dir.glob("*.py"))
                    
                    if py_files:
                        # 直接使用第一个（也是唯一的）.py文件
                        agent_script_path = py_files[0]
                        script_name = agent_script_path.name
                
                # 如果找到了代理脚本文件
                if agent_script_path:
                    agents.append({
                        'id': agent_id,
                        'name': agent_name,
                        'description': project.get('description', ''),
                        'path': str(agent_dir),
                        'script_path': str(agent_script_path),
                        'script_name': script_name,
                        'created_at': project.get('created_at', ''),
                        'last_updated': project.get('updated_at', ''),
                        'version': project.get('version', 'v1.0'),
                        'status': project.get('status', 'running'),
                        'metrics': project.get('metrics', {})
                    })
    
    except Exception as e:
        print(f"读取项目状态文件失败 {projects_status_file}: {e}")
    
    return agents

def get_agent_description(agent_script_path: Path) -> str:
    """从代理脚本中提取描述信息"""
    try:
        with open(agent_script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取文档字符串中的描述
        lines = content.split('\n')
        in_docstring = False
        description_lines = []
        
        for line in lines:
            if '"""' in line and not in_docstring:
                in_docstring = True
                # 如果同一行有开始和结束的三引号
                if line.count('"""') == 2:
                    desc = line.split('"""')[1].strip()
                    if desc:
                        return desc
                continue
            elif '"""' in line and in_docstring:
                break
            elif in_docstring:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith('#'):
                    description_lines.append(clean_line)
        
        if description_lines:
            return description_lines[0]  # 返回第一行描述
        
        return "AI代理"
        
    except Exception:
        return "AI代理"

def detect_agent_input_parameter(agent_path: Path) -> tuple[str, bool]:
    """检测代理脚本使用的输入参数格式
    
    由于我们已经标准化了代理生成过程，新生成的代理应该都使用 -i 参数。
    这个函数主要用于兼容旧的代理。
    
    Returns:
        tuple: (参数名, 是否支持交互模式)
    """
    try: 
        with open(agent_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有交互模式（旧代理可能有）
        has_interactive = any(pattern in content for pattern in [
            "while True:", "input(", "Interactive mode", "Enter your", "Type 'exit'"
        ])
        
        # 优先检查标准化的 -i 参数
        if "add_argument('-i'" in content or "add_argument('--input'" in content:
            return "-i", has_interactive
        
        # 兼容旧代理的其他参数格式
        elif "add_argument('-p'" in content or "add_argument('--product'" in content:
            return "-p", has_interactive
        elif "add_argument('-d'" in content or "add_argument('--data'" in content:
            return "-d", has_interactive
        elif "add_argument('-m'" in content or "add_argument('--message'" in content:
            return "-m", has_interactive
        elif "add_argument('-t'" in content or "add_argument('--text'" in content:
            return "-t", has_interactive
        elif "add_argument('-q'" in content or "add_argument('--query'" in content:
            return "-q", has_interactive
        else:
            # 如果没有找到明确的参数，检查是否是纯交互模式
            if has_interactive and "args.parse_args()" not in content:
                return None, True  # 纯交互模式，不需要参数
            else:
                # 默认使用标准化的 -i 参数
                return "-i", has_interactive
    except Exception:
        # 如果检测失败，使用标准化的默认值
        return "-i", False

def _smart_detect_agent_parameter(agent_path: Path) -> tuple[str, bool]:
    """使用AI智能检测代理参数"""
    try:
        print(f'_smart_detect_agent_parameter: {agent_path}')
        # 获取help信息
        help_output = _get_agent_help_output(agent_path)
        if not help_output:
            return None, False
        
        # 使用AI分析help输出
        best_param = _analyze_help_with_ai(help_output)
        print(f'best_param:--- {best_param}')
        # 检查是否支持交互模式
        has_interactive = _check_interactive_mode(agent_path)
        
        return best_param, has_interactive
        
    except Exception as e:
        print(f"智能检测失败: {e}")
        return None, False

def _get_agent_help_output(agent_path: Path) -> str:
    """获取代理脚本的help输出"""
    try:
        import subprocess
        
        # 准备环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        env['BYPASS_TOOL_CONSENT'] = "true"
        
        # 尝试不同的Python路径
        python_paths = [
            project_root / "venv" / "bin" / "python",
            "python3",
            "python"
        ]
        
        for python_cmd in python_paths:
            try:
                cmd = [str(python_cmd), str(agent_path), "--help"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(project_root),
                    env=env
                )
                
                if result.returncode == 0 and result.stdout:
                    return result.stdout
                elif result.stderr and "usage:" in result.stderr.lower():
                    return result.stderr
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return ""
        
    except Exception as e:
        print(f"获取help输出失败: {e}")
        return ""

def _analyze_help_with_ai(help_output: str) -> str:
    """使用Strands Agent调用Bedrock来分析help输出，决定最佳的输入参数"""
    try:
        from strands import Agent, tool
        from strands.models import BedrockModel
        print(f'help_output: {help_output}')
        # 创建一个简单的分析Agent
        model = BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",  # 使用轻量级模型
            region_name="us-west-2"  # 使用正确的区域
        )
        
        analyzer_agent = Agent(
            name="parameter_analyzer",
            model=model,
            system_prompt="""分析命令行help输出，找出最适合接收用户输入的参数。

优先选择包含这些词汇的参数：input, query, message, data, text, requirement, 用户输入, 查询, 请求。

直接返回参数名（如"-r"或"-i"），不要其他内容。如果不确定，返回"-i"。"""
        )
        
        # 构建分析提示
        analysis_prompt = f"""请分析以下命令行help输出，找出最适合用于接收用户输入的参数：

```
{help_output}
```

请直接返回最佳的参数名（如"-i", "-q", "-r"等），不要返回其他内容。"""
        
        # 调用AI分析
        response = analyzer_agent(analysis_prompt)
        print(f'response----: {response}')
        
        # 处理AgentResult对象，提取文本内容
        if hasattr(response, 'content'):
            response_text = response.content
        elif hasattr(response, 'text'):
            response_text = response.text
        else:
            response_text = str(response)
        
        print(f'response_text----: {response_text}')
        
        # 提取参数名
        import re
        param_match = re.search(r'-[a-zA-Z]', response_text)
        if param_match:
            return param_match.group()
        
        # 如果AI返回的不是标准格式，尝试解析
        response_lower = response_text.lower().strip()
        if response_lower.startswith('-'):
            return response_lower[:2]  # 取前两个字符，如"-i"
        
        # 默认返回 -i
        return "-i"
        
    except Exception as e:
        print(f"AI分析失败: {e}")
        # 回退到简单的正则表达式匹配
        return _fallback_analyze_help(help_output)

def _fallback_analyze_help(help_output: str) -> str:
    """回退的help分析方法"""
    try:
        import re
        
        # 查找所有参数
        param_matches = re.findall(r'-([a-zA-Z])\s+[^,\n]*(?:input|query|message|data|text|requirement|用户|输入|查询|请求)', help_output, re.IGNORECASE)
        
        if param_matches:
            # 优先选择常见的输入参数
            for preferred in ['i', 'q', 'm', 'd', 't', 'r', 'p']:
                if preferred in param_matches:
                    return f"-{preferred}"
            # 返回第一个匹配的
            return f"-{param_matches[0]}"
        
        # 如果没有找到语义匹配，查找所有参数
        all_params = re.findall(r'-([a-zA-Z])\s+', help_output)
        if all_params:
            # 优先选择常见的输入参数
            for preferred in ['i', 'q', 'm', 'd', 't', 'r', 'p']:
                if preferred in all_params:
                    return f"-{preferred}"
            # 返回第一个参数
            return f"-{all_params[0]}"
        
        return "-i"
        
    except Exception:
        return "-i"

def _check_interactive_mode(agent_path: Path) -> bool:
    """检查代理是否支持交互模式"""
    try:
        with open(agent_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查交互模式的标志
        interactive_patterns = [
            "while True:", "input(", "Interactive mode", 
            "Enter your", "Type 'exit'", "交互模式",
            "输入 'exit'", "请输入", "继续对话"
        ]
        
        return any(pattern in content for pattern in interactive_patterns)
        
    except Exception:
        return False

def _fallback_detect_agent_parameter(agent_path: Path) -> tuple[str, bool]:
    """传统的参数检测方法（回退方案）"""
    try:
        with open(agent_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有交互模式
        has_interactive = _check_interactive_mode(agent_path)
        
        # 按优先级检查参数
        param_checks = [
            ("-i", ["add_argument('-i'", "add_argument('--input'"]),
            ("-q", ["add_argument('-q'", "add_argument('--query'"]),
            ("-m", ["add_argument('-m'", "add_argument('--message'"]),
            ("-d", ["add_argument('-d'", "add_argument('--data'"]),
            ("-t", ["add_argument('-t'", "add_argument('--text'"]),
            ("-r", ["add_argument('-r'", "add_argument('--requirement'"]),
            ("-p", ["add_argument('-p'", "add_argument('--product'"])
        ]
        
        for param, patterns in param_checks:
            if any(pattern in content for pattern in patterns):
                return param, has_interactive
        
        # 如果没有找到明确的参数，检查是否是纯交互模式
        if has_interactive and "args.parse_args()" not in content:
            return None, True  # 纯交互模式，不需要参数
        
        # 默认使用 -i
        return "-i", has_interactive
        
    except Exception:
        return "-i", False

def render_agent_response_streaming(agent_info: Dict, user_input: str) -> str:
    """渲染代理的流式响应"""
    
    response_placeholder = st.empty()
    full_response = ""
    
    try:
        # 显示思考状态
        with response_placeholder.container():
            st.markdown("🤔 *代理正在思考...*")
        
        # 获取流式响应
        response_generator = call_agent_with_input(agent_info, user_input)
        
        # 逐步显示响应
        for chunk in response_generator:
            if chunk.strip():
                full_response += chunk + "\n"
                
                # 更新显示
                with response_placeholder.container():
                    st.markdown(full_response)
        
        return full_response.strip()
        
    except Exception as e:
        error_msg = f"代理响应失败: {str(e)}"
        with response_placeholder.container():
            st.error(error_msg)
        return error_msg



def render_welcome_message(agent_name: str) -> None:
    """渲染欢迎消息"""
    
    with st.chat_message("assistant"):
        st.write(f"👋 您好！我是 **{agent_name}**，很高兴为您服务！")
        st.write("请告诉我您需要什么帮助，我会尽力为您解答。")

def format_timestamp(timestamp: str) -> str:
    """格式化时间戳显示"""
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return timestamp

def handle_user_input(user_input: str, agent_id: str, agent_name: str, agent_service) -> None:
    """处理用户输入"""
    
    # 添加用户消息到历史
    add_chat_message(agent_id, {
        'role': 'user',
        'content': user_input,
        'timestamp': datetime.now().isoformat(),
        'type': 'text'
    })
    
    # 显示用户消息
    with st.chat_message("user"):
        st.write(user_input)
    
    # 显示代理思考状态
    with st.chat_message("assistant"):
        with st.spinner("🤔 代理正在思考..."):
            # 创建进度占位符
            progress_placeholder = st.empty()
            response_placeholder = st.empty()
            
            try:
                # 调用代理服务
                start_time = time.time()
                
                # 获取代理路径 - 使用完整的脚本路径
                agent_path = f"../agents/generated_agents/{agent_id}/{agent_id}.py"
                
                # 调用代理并获取流式响应
                response_generator = agent_service.call_agent(
                    agent_path=agent_path,
                    args=['-d', user_input]
                )
                
                # 处理流式响应
                full_response = ""
                response_type = "text"
                
                for chunk in response_generator:
                    if chunk.startswith("错误:"):
                        response_type = "error"
                    elif chunk.startswith("{") or chunk.startswith("["):
                        response_type = "json"
                    
                    full_response += chunk + "\n"
                    
                    # 实时更新响应
                    with response_placeholder.container():
                        render_message_content(full_response.strip(), response_type)
                
                # 计算处理时间
                processing_time = time.time() - start_time
                
                # 添加代理响应到历史
                add_chat_message(agent_id, {
                    'role': 'assistant',
                    'content': full_response.strip(),
                    'timestamp': datetime.now().isoformat(),
                    'type': response_type,
                    'metadata': {
                        'processing_time': f"{processing_time:.1f}s",
                        'tokens_used': len(full_response.split()),
                        'model_used': 'Claude 3.5 Sonnet',
                        'status': 'success' if response_type != 'error' else 'error'
                    }
                })
                
                # 更新会话统计
                update_session_activity(agent_id)
                
            except Exception as e:
                error_msg = f"代理调用失败: {str(e)}"
                response_placeholder.error(error_msg)
                
                # 添加错误消息到历史
                add_chat_message(agent_id, {
                    'role': 'assistant',
                    'content': error_msg,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'error',
                    'metadata': {
                        'status': 'error',
                        'error_type': type(e).__name__
                    }
                })
            
            finally:
                progress_placeholder.empty()

def render_modern_chat_message(message: Dict, agent_name: str) -> None:
    """渲染现代化的聊天消息气泡"""
    
    role = message.get('role', 'user')
    content = message.get('content', '')
    timestamp = message.get('timestamp', '')
    metadata = message.get('metadata', {})
    
    # 格式化时间
    time_str = format_timestamp(timestamp) if timestamp else ''
    
    if role == 'user':
        # 用户消息气泡
        st.markdown(f"""
        <div class="message-bubble user">
            <div class="message-header">
                <span class="message-time">({time_str})</span>
                <span>👤 用户</span>
            </div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        # 代理消息气泡
        processing_time = metadata.get('processing_time', '')
        tokens_used = metadata.get('tokens_used', '')
        
        # 智能内容处理和清理
        import re
        import html
        
        # 清理和处理内容
        processed_content = content
        
        # 1. 移除或清理HTML标签（避免显示原始HTML代码）
        if '<' in processed_content and '>' in content:
            # 移除HTML标签但保留内容
            processed_content = re.sub(r'<[^>]+>', '', processed_content)
            # 处理HTML实体
            processed_content = html.unescape(processed_content)
        
        # 2. 清理多余的空行和格式
        processed_content = re.sub(r'\n\s*\n\s*\n', '\n\n', processed_content)  # 合并多个空行
        processed_content = processed_content.strip()
        
        # 3. 检查是否包含结构化内容
        structure_indicators = [
            '📋', '📊', '🎯', '💡', '✅', '🔍',  # 表情符号
            '分析结果', '方案', '报价', '建议', '总结',  # 中文关键词
            'Analysis', 'Result', 'Solution', 'Summary',  # 英文关键词
            '###', '##', '#',  # Markdown标题
            '**', '*',  # Markdown格式
        ]
        
        is_structured = any(indicator in processed_content for indicator in structure_indicators)
        
        # 4. 检查是否包含列表或多行内容
        has_list = ('•' in processed_content or 
                   '-' in processed_content or 
                   any(f'{i}.' in processed_content for i in range(1, 10)) or
                   processed_content.count('\n') > 2)
        
        # 5. 转换为HTML
        if is_structured or has_list:
            # 结构化内容，使用特殊样式
            content_html = processed_content.replace('\n', '<br>')
            
            # 处理Markdown样式的粗体
            content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
            content_html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content_html)
            
            # 添加分析区域样式
            content_html = f'<div class="analysis-section">{content_html}</div>'
        else:
            # 普通内容
            content_html = processed_content.replace('\n', '<br>')
            # 处理简单的Markdown格式
            content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
            content_html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content_html)
        
        
        st.markdown(f"""
        <div class="message-bubble assistant">
            <div class="message-header">
                <span>🤖 {agent_name}</span>
                <span class="message-time">({time_str})</span>
            </div>
            <div class="message-content">{content_html}</div>
        </div>
        """, unsafe_allow_html=True)

def render_chat_controls(agent_id: str, agent_name: str) -> None:
    """渲染聊天控制面板"""
    
    st.markdown("---")
    
    # 主要控制按钮
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🗑️ 清空对话", key=f"clear_{agent_id}"):
            clear_chat_history(agent_id)
            st.success("对话历史已清空")
            st.rerun()
    
    with col2:
        # 导出选项
        export_format = st.selectbox(
            "导出格式",
            ["markdown", "json", "csv"],
            key=f"export_format_{agent_id}",
            format_func=lambda x: {"markdown": "📄 Markdown", "json": "📋 JSON", "csv": "📊 CSV"}[x]
        )
    
    with col3:
        if st.button("💾 导出对话", key=f"export_{agent_id}"):
            export_chat_history(agent_id, agent_name, export_format)
    
    with col4:
        if st.button("📊 对话统计", key=f"stats_{agent_id}"):
            show_chat_statistics(agent_id)
    
    with col5:
        if st.button("🔄 刷新", key=f"refresh_{agent_id}"):
            st.rerun()
    
    # 高级控制选项
    with st.expander("🔧 高级选项", expanded=False):
        adv_col1, adv_col2, adv_col3 = st.columns(3)
        
        with adv_col1:
            if st.button("⏸️ 暂停会话", key=f"pause_adv_{agent_id}"):
                pause_chat_session(agent_id)
                st.success("会话已暂停")
                st.rerun()
            
            if st.button("▶️ 恢复会话", key=f"resume_adv_{agent_id}"):
                resume_chat_session(agent_id)
                st.success("会话已恢复")
                st.rerun()
        
        with adv_col2:
            if st.button("🛑 终止会话", key=f"terminate_{agent_id}"):
                terminate_chat_session(agent_id)
                st.warning("会话已终止")
                st.rerun()
            
            if st.button("🔄 重置会话", key=f"reset_{agent_id}"):
                # 重置会话状态
                session_key = f"chat_session_{agent_id}"
                if session_key in st.session_state:
                    st.session_state[session_key]['status'] = 'active'
                    st.session_state[session_key]['last_activity'] = datetime.now().isoformat()
                st.success("会话已重置")
                st.rerun()
        
        with adv_col3:
            # 会话信息
            session_info = st.session_state.get(f"chat_session_{agent_id}", {})
            st.write(f"**会话状态:** {session_info.get('status', 'unknown')}")
            st.write(f"**消息计数:** {session_info.get('message_count', 0)}")
            
            # 显示最后活动时间
            last_activity = session_info.get('last_activity', '')
            if last_activity:
                st.write(f"**最后活动:** {format_timestamp(last_activity)}")

def render_typing_indicator() -> None:
    """渲染打字指示器"""
    
    with st.chat_message("assistant"):
        st.markdown("🤔 *代理正在思考...*")

def render_streaming_response(response_placeholder, response_text: str) -> None:
    """渲染流式响应"""
    
    response_placeholder.write(response_text)

def add_chat_message(agent_id: str, message: Dict) -> None:
    """添加聊天消息到历史"""
    
    chat_key = f"chat_history_{agent_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    
    # 添加时间戳
    if 'timestamp' not in message:
        message['timestamp'] = datetime.now().isoformat()
    
    st.session_state[chat_key].append(message)

def clear_chat_history(agent_id: str) -> None:
    """清空聊天历史"""
    
    chat_key = f"chat_history_{agent_id}"
    if chat_key in st.session_state:
        st.session_state[chat_key] = []

def get_chat_history(agent_id: str) -> List[Dict]:
    """获取聊天历史"""
    
    chat_key = f"chat_history_{agent_id}"
    return st.session_state.get(chat_key, [])

def export_chat_history(agent_id: str, agent_name: str, export_format: str = "markdown") -> None:
    """导出聊天历史，支持多种格式"""
    
    chat_history = get_chat_history(agent_id)
    session_info = st.session_state.get(f"chat_session_{agent_id}", {})
    
    if not chat_history:
        st.info("暂无对话记录可导出")
        return
    
    if export_format == "json":
        # JSON格式导出
        export_data = {
            "session_info": session_info,
            "agent_name": agent_name,
            "agent_id": agent_id,
            "export_time": datetime.now().isoformat(),
            "total_messages": len(chat_history),
            "messages": chat_history
        }
        
        export_content = json.dumps(export_data, ensure_ascii=False, indent=2)
        file_name = f"{agent_name}_对话记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        mime_type = "application/json"
    
    elif export_format == "csv":
        # CSV格式导出
        df_data = []
        for i, message in enumerate(chat_history, 1):
            row = {
                "序号": i,
                "角色": "用户" if message['role'] == 'user' else agent_name,
                "内容": message['content'],
                "时间": message.get('timestamp', ''),
                "消息类型": message.get('type', 'text'),
                "处理时间": message.get('metadata', {}).get('processing_time', ''),
                "Token使用": message.get('metadata', {}).get('tokens_used', ''),
                "状态": message.get('metadata', {}).get('status', '')
            }
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        export_content = df.to_csv(index=False, encoding='utf-8-sig')
        file_name = f"{agent_name}_对话记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        mime_type = "text/csv"
    
    else:
        # Markdown格式导出（默认）
        export_content = f"# {agent_name} 对话记录\n\n"
        export_content += f"**导出时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_content += f"**会话ID:** {session_info.get('session_id', 'unknown')}\n"
        export_content += f"**总消息数:** {len(chat_history)}\n"
        export_content += f"**会话创建时间:** {format_timestamp(session_info.get('created_at', ''))}\n\n"
        
        # 统计信息
        user_count = len([msg for msg in chat_history if msg['role'] == 'user'])
        assistant_count = len(chat_history) - user_count
        export_content += f"**用户消息:** {user_count} | **代理回复:** {assistant_count}\n\n"
        export_content += "---\n\n"
        
        for i, message in enumerate(chat_history, 1):
            role = "👤 用户" if message['role'] == 'user' else f"🤖 {agent_name}"
            content = message['content']
            timestamp = message.get('timestamp', '')
            message_type = message.get('type', 'text')
            
            export_content += f"## {i}. {role}\n\n"
            
            if timestamp:
                formatted_time = format_timestamp(timestamp)
                export_content += f"**时间:** {formatted_time}\n"
            
            if message_type != 'text':
                export_content += f"**类型:** {message_type}\n"
            
            export_content += "\n"
            
            # 根据消息类型格式化内容
            if message_type == 'json':
                export_content += "```json\n"
                export_content += content
                export_content += "\n```\n\n"
            elif message_type == 'code':
                export_content += "```python\n"
                export_content += content
                export_content += "\n```\n\n"
            elif message_type == 'error':
                export_content += f"❌ **错误:** {content}\n\n"
            else:
                export_content += f"{content}\n\n"
            
            # 添加元数据
            metadata = message.get('metadata', {})
            if metadata:
                export_content += "**元数据:**\n"
                for key, value in metadata.items():
                    export_content += f"- **{key}:** {value}\n"
                export_content += "\n"
            
            export_content += "---\n\n"
        
        file_name = f"{agent_name}_对话记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        mime_type = "text/markdown"
    
    # 提供下载
    st.download_button(
        label=f"📄 下载{export_format.upper()}格式",
        data=export_content,
        file_name=file_name,
        mime=mime_type,
        key=f"download_{export_format}_{agent_id}"
    )

def show_chat_statistics(agent_id: str) -> None:
    """显示对话统计信息"""
    
    stats = get_session_statistics(agent_id)
    
    if not stats:
        st.info("暂无对话数据")
        return
    
    # 显示统计信息
    with st.expander("📊 详细统计", expanded=True):
        # 基本统计
        st.subheader("📈 基本统计")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总消息数", stats['total_messages'])
            st.metric("用户消息", stats['user_messages'])
        
        with col2:
            st.metric("代理回复", stats['assistant_messages'])
            st.metric("错误次数", stats['error_count'])
        
        with col3:
            if stats['avg_response_time'] > 0:
                st.metric("平均响应时间", f"{stats['avg_response_time']:.1f}s")
            st.metric("成功率", f"{stats['success_rate']:.1f}%")
        
        with col4:
            if stats['session_duration'] > 0:
                st.metric("会话时长", f"{stats['session_duration']:.1f}分钟")
            st.metric("会话状态", stats['session_status'])
        
        # 时间线统计
        st.subheader("⏰ 时间统计")
        time_col1, time_col2 = st.columns(2)
        
        with time_col1:
            st.write(f"**会话创建:** {format_timestamp(stats['created_at'])}")
        
        with time_col2:
            st.write(f"**最后活动:** {format_timestamp(stats['last_activity'])}")
        
        # 消息类型分布
        st.subheader("📋 消息类型分布")
        chat_history = get_chat_history(agent_id)
        
        if chat_history:
            message_types = {}
            for msg in chat_history:
                msg_type = msg.get('type', 'text')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            type_col1, type_col2 = st.columns(2)
            
            with type_col1:
                for msg_type, count in message_types.items():
                    st.write(f"**{msg_type}:** {count}")
            
            with type_col2:
                # 创建简单的条形图数据
                if len(message_types) > 1:
                    df = pd.DataFrame(list(message_types.items()), columns=['类型', '数量'])
                    st.bar_chart(df.set_index('类型'))
        
        # 性能统计
        st.subheader("⚡ 性能统计")
        perf_col1, perf_col2 = st.columns(2)
        
        with perf_col1:
            # 响应时间分布
            response_times = []
            for msg in chat_history:
                if msg.get('role') == 'assistant':
                    metadata = msg.get('metadata', {})
                    processing_time = metadata.get('processing_time', '')
                    if processing_time and 's' in processing_time:
                        try:
                            time_value = float(processing_time.replace('s', ''))
                            response_times.append(time_value)
                        except:
                            pass
            
            if response_times:
                st.write(f"**最快响应:** {min(response_times):.1f}s")
                st.write(f"**最慢响应:** {max(response_times):.1f}s")
                st.write(f"**响应时间中位数:** {sorted(response_times)[len(response_times)//2]:.1f}s")
        
        with perf_col2:
            # Token使用统计
            total_tokens = 0
            for msg in chat_history:
                metadata = msg.get('metadata', {})
                tokens = metadata.get('tokens_used', 0)
                if isinstance(tokens, (int, float)):
                    total_tokens += tokens
                elif isinstance(tokens, str) and tokens.isdigit():
                    total_tokens += int(tokens)
            
            if total_tokens > 0:
                st.write(f"**总Token使用:** {total_tokens}")
                if stats['assistant_messages'] > 0:
                    avg_tokens = total_tokens / stats['assistant_messages']
                    st.write(f"**平均Token/回复:** {avg_tokens:.1f}")

def render_chat_sidebar(agent_id: str) -> None:
    """渲染聊天侧边栏"""
    
    with st.sidebar:
        st.subheader("💬 对话设置")
        
        # 自动滚动设置
        auto_scroll = st.checkbox("自动滚动到底部", value=True)
        st.session_state[f"auto_scroll_{agent_id}"] = auto_scroll
        
        # 显示时间戳
        show_timestamps = st.checkbox("显示时间戳", value=True)
        st.session_state[f"show_timestamps_{agent_id}"] = show_timestamps
        
        # 显示元数据
        show_metadata = st.checkbox("显示元数据", value=True)
        st.session_state[f"show_metadata_{agent_id}"] = show_metadata
        
        st.markdown("---")
        
        # 快速操作
        st.subheader("🔧 快速操作")
        
        if st.button("清空对话", key="sidebar_clear"):
            clear_chat_history(agent_id)
            st.rerun()
        
        if st.button("导出对话", key="sidebar_export"):
            export_chat_history(agent_id, "代理")
        
        # 对话统计
        chat_history = get_chat_history(agent_id)
        if chat_history:
            st.markdown("---")
            st.subheader("📊 统计信息")
            st.caption(f"总消息: {len(chat_history)}")
            
            user_count = len([msg for msg in chat_history if msg['role'] == 'user'])
            assistant_count = len([msg for msg in chat_history if msg['role'] == 'assistant'])
            
            st.caption(f"用户: {user_count} | 代理: {assistant_count}")

def search_chat_history(agent_id: str, query: str) -> List[Dict]:
    """搜索聊天历史"""
    
    chat_history = get_chat_history(agent_id)
    results = []
    
    query_lower = query.lower()
    
    for i, message in enumerate(chat_history):
        content = message.get('content', '').lower()
        if query_lower in content:
            results.append({
                'index': i + 1,
                'role': message.get('role', 'unknown'),
                'content': message.get('content', ''),
                'timestamp': message.get('timestamp', ''),
                'relevance': content.count(query_lower)  # 简单的相关性评分
            })
    
    # 按相关性排序
    results.sort(key=lambda x: x['relevance'], reverse=True)
    return results

def pause_chat_session(agent_id: str) -> None:
    """暂停聊天会话"""
    
    session_key = f"chat_session_{agent_id}"
    if session_key in st.session_state:
        st.session_state[session_key]['status'] = 'paused'
        st.session_state[session_key]['paused_at'] = datetime.now().isoformat()

def resume_chat_session(agent_id: str) -> None:
    """恢复聊天会话"""
    
    session_key = f"chat_session_{agent_id}"
    if session_key in st.session_state:
        st.session_state[session_key]['status'] = 'active'
        st.session_state[session_key]['resumed_at'] = datetime.now().isoformat()

def terminate_chat_session(agent_id: str) -> None:
    """终止聊天会话"""
    
    session_key = f"chat_session_{agent_id}"
    if session_key in st.session_state:
        st.session_state[session_key]['status'] = 'terminated'
        st.session_state[session_key]['terminated_at'] = datetime.now().isoformat()

def update_session_activity(agent_id: str) -> None:
    """更新会话活动时间"""
    
    session_key = f"chat_session_{agent_id}"
    if session_key in st.session_state:
        st.session_state[session_key]['last_activity'] = datetime.now().isoformat()
        st.session_state[session_key]['message_count'] = st.session_state[session_key].get('message_count', 0) + 1

def get_session_statistics(agent_id: str) -> Dict:
    """获取会话统计信息"""
    
    chat_history = get_chat_history(agent_id)
    session_info = st.session_state.get(f"chat_session_{agent_id}", {})
    
    if not chat_history:
        return {}
    
    # 基本统计
    total_messages = len(chat_history)
    user_messages = len([msg for msg in chat_history if msg['role'] == 'user'])
    assistant_messages = total_messages - user_messages
    
    # 计算平均响应时间
    response_times = []
    for msg in chat_history:
        if msg.get('role') == 'assistant':
            metadata = msg.get('metadata', {})
            processing_time = metadata.get('processing_time', '')
            if processing_time and 's' in processing_time:
                try:
                    time_value = float(processing_time.replace('s', ''))
                    response_times.append(time_value)
                except:
                    pass
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # 计算会话时长
    session_duration = 0
    if chat_history:
        try:
            first_msg_time = datetime.fromisoformat(chat_history[0].get('timestamp', ''))
            last_msg_time = datetime.fromisoformat(chat_history[-1].get('timestamp', ''))
            session_duration = (last_msg_time - first_msg_time).total_seconds() / 60  # 分钟
        except:
            pass
    
    # 错误统计
    error_count = len([msg for msg in chat_history if msg.get('type') == 'error'])
    
    return {
        'total_messages': total_messages,
        'user_messages': user_messages,
        'assistant_messages': assistant_messages,
        'avg_response_time': avg_response_time,
        'session_duration': session_duration,
        'error_count': error_count,
        'success_rate': ((assistant_messages - error_count) / assistant_messages * 100) if assistant_messages > 0 else 0,
        'session_status': session_info.get('status', 'unknown'),
        'created_at': session_info.get('created_at', ''),
        'last_activity': session_info.get('last_activity', '')
    }

def render_typing_indicator(agent_name: str = "代理") -> None:
    """渲染打字指示器"""
    
    with st.chat_message("assistant"):
        # 创建动态的打字效果
        placeholder = st.empty()
        
        typing_messages = [
            f"🤔 {agent_name}正在思考...",
            f"💭 {agent_name}正在分析您的问题...",
            f"⚡ {agent_name}正在生成回复...",
            f"🔍 {agent_name}正在查找相关信息..."
        ]
        
        for i, msg in enumerate(typing_messages):
            placeholder.markdown(f"*{msg}*")
            time.sleep(0.5)
        
        placeholder.empty()

def render_streaming_response(response_placeholder, response_text: str, message_type: str = 'text') -> None:
    """渲染流式响应"""
    
    with response_placeholder.container():
        render_message_content(response_text, message_type)

def format_timestamp(timestamp: str) -> str:
    """格式化时间戳显示"""
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now()
        
        # 如果是今天，只显示时间
        if dt.date() == now.date():
            return dt.strftime('%H:%M:%S')
        # 如果是昨天，显示"昨天 时间"
        elif (now.date() - dt.date()).days == 1:
            return f"昨天 {dt.strftime('%H:%M:%S')}"
        # 其他情况显示完整日期时间
        else:
            return dt.strftime('%m-%d %H:%M:%S')
    except:
        return timestamp

def render_welcome_message(agent_name: str) -> None:
    """渲染欢迎消息"""
    
    with st.chat_message("assistant"):
        st.write(f"👋 您好！我是 **{agent_name}**，很高兴为您服务！")
        st.write("请告诉我您需要什么帮助，我会尽力为您解答。")

def render_error_message(error_msg: str) -> None:
    """渲染错误消息"""
    
    with st.chat_message("assistant"):
        st.error(f"❌ 抱歉，处理您的请求时出现了错误：{error_msg}")
        st.write("请稍后重试，或者尝试重新表述您的问题。")



def render_chat_session_manager(agent_id: str) -> None:
    """渲染聊天会话管理器"""
    
    st.subheader("💾 会话管理")
    
    # 会话历史列表
    chat_history = get_chat_history(agent_id)
    
    if chat_history:
        # 会话统计
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总消息数", len(chat_history))
        
        with col2:
            user_count = len([msg for msg in chat_history if msg['role'] == 'user'])
            st.metric("用户消息", user_count)
        
        with col3:
            assistant_count = len([msg for msg in chat_history if msg['role'] == 'assistant'])
            st.metric("代理回复", assistant_count)
        
        # 会话搜索
        search_query = st.text_input("🔍 搜索对话内容", placeholder="输入关键词搜索...")
        
        if search_query:
            filtered_history = [
                msg for msg in chat_history 
                if search_query.lower() in msg['content'].lower()
            ]
            
            st.write(f"找到 {len(filtered_history)} 条匹配的消息")
            
            for i, msg in enumerate(filtered_history):
                with st.expander(f"消息 {i+1} - {msg['role']} ({format_timestamp(msg['timestamp'])})"):
                    st.write(msg['content'])
        
        # 会话导出选项
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            export_format = st.selectbox(
                "导出格式",
                ["Markdown", "JSON", "CSV"]
            )
        
        with col2:
            if st.button("📤 导出会话"):
                export_chat_session(agent_id, export_format)
    
    else:
        st.info("暂无会话记录")

def export_chat_session(agent_id: str, format_type: str = "Markdown") -> None:
    """导出聊天会话"""
    
    chat_history = get_chat_history(agent_id)
    
    if not chat_history:
        st.warning("暂无对话记录可导出")
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == "Markdown":
        content = generate_markdown_export(chat_history, agent_id)
        filename = f"chat_session_{agent_id}_{timestamp}.md"
        mime_type = "text/markdown"
    
    elif format_type == "JSON":
        content = json.dumps(chat_history, ensure_ascii=False, indent=2)
        filename = f"chat_session_{agent_id}_{timestamp}.json"
        mime_type = "application/json"
    
    elif format_type == "CSV":
        content = generate_csv_export(chat_history)
        filename = f"chat_session_{agent_id}_{timestamp}.csv"
        mime_type = "text/csv"
    
    else:
        st.error("不支持的导出格式")
        return
    
    st.download_button(
        label=f"📄 下载 {format_type} 格式",
        data=content,
        file_name=filename,
        mime=mime_type
    )

def generate_markdown_export(chat_history: List[Dict], agent_id: str) -> str:
    """生成Markdown格式的导出内容"""
    
    content = f"# 代理对话记录 - {agent_id}\n\n"
    content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    content += f"总消息数: {len(chat_history)}\n\n"
    content += "---\n\n"
    
    for i, message in enumerate(chat_history, 1):
        role = "👤 用户" if message['role'] == 'user' else "🤖 代理"
        content += f"## {i}. {role}\n\n"
        
        # 时间戳
        if 'timestamp' in message:
            content += f"**时间:** {format_timestamp(message['timestamp'])}\n\n"
        
        # 消息内容
        content += f"{message['content']}\n\n"
        
        # 元数据
        if 'metadata' in message and message['metadata']:
            content += "**元数据:**\n"
            for key, value in message['metadata'].items():
                content += f"- {key}: {value}\n"
            content += "\n"
        
        content += "---\n\n"
    
    return content

def generate_csv_export(chat_history: List[Dict]) -> str:
    """生成CSV格式的导出内容"""
    
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题行
    writer.writerow(['序号', '角色', '内容', '时间戳', '处理时间', 'Token使用'])
    
    # 写入数据行
    for i, message in enumerate(chat_history, 1):
        metadata = message.get('metadata', {})
        writer.writerow([
            i,
            message['role'],
            message['content'],
            message.get('timestamp', ''),
            metadata.get('processing_time', ''),
            metadata.get('tokens_used', '')
        ])
    
    return output.getvalue()

def render_chat_analytics(agent_id: str) -> None:
    """渲染聊天分析面板"""
    
    chat_history = get_chat_history(agent_id)
    
    if not chat_history:
        st.info("暂无数据可分析")
        return
    
    st.subheader("📊 对话分析")
    
    # 基础统计
    total_messages = len(chat_history)
    user_messages = [msg for msg in chat_history if msg['role'] == 'user']
    assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总消息数", total_messages)
    
    with col2:
        st.metric("用户消息", len(user_messages))
    
    with col3:
        st.metric("代理回复", len(assistant_messages))
    
    with col4:
        if assistant_messages:
            avg_response_time = sum(
                float(msg.get('metadata', {}).get('processing_time', '0').replace('s', ''))
                for msg in assistant_messages
                if msg.get('metadata', {}).get('processing_time')
            ) / len(assistant_messages)
            st.metric("平均响应时间", f"{avg_response_time:.1f}s")
    
    # 时间分布图
    if len(chat_history) > 1:
        st.markdown("### 📈 消息时间分布")
        
        # 准备时间数据
        timestamps = []
        for msg in chat_history:
            if 'timestamp' in msg:
                try:
                    dt = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    timestamps.append(dt)
                except:
                    pass
        
        if timestamps:
            # 创建时间分布数据
            df = pd.DataFrame({
                'timestamp': timestamps,
                'count': [1] * len(timestamps)
            })
            
            # 按小时分组
            df['hour'] = df['timestamp'].dt.hour
            hourly_counts = df.groupby('hour')['count'].sum().reset_index()
            
            st.bar_chart(hourly_counts.set_index('hour'))
    
    # 消息长度分析
    st.markdown("### 📏 消息长度分析")
    
    user_lengths = [len(msg['content']) for msg in user_messages]
    assistant_lengths = [len(msg['content']) for msg in assistant_messages]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if user_lengths:
            st.metric("用户消息平均长度", f"{sum(user_lengths) / len(user_lengths):.0f} 字符")
    
    with col2:
        if assistant_lengths:
            st.metric("代理回复平均长度", f"{sum(assistant_lengths) / len(assistant_lengths):.0f} 字符")

def render_debug_settings(agent_id: str) -> None:
    """渲染调试设置面板"""
    
    with st.sidebar.expander("🔧 调试设置", expanded=False):
        debug_key = f"debug_logs_{agent_id}"
        
        # 调试日志开关
        show_debug = st.checkbox(
            "显示详细执行日志",
            value=st.session_state.get(debug_key, True),  # 默认开启调试模式
            help="显示代理执行过程中的详细日志信息"
        )
        
        # 保存设置到session state
        st.session_state[debug_key] = show_debug
        
        if show_debug:
            st.success("💡 调试模式已启用")
        else:
            st.info("🔇 调试模式已关闭")
        
        # 日志级别选择
        log_level = st.selectbox(
            "日志级别",
            ["基础", "详细", "完整"],
            index=0,
            help="选择要显示的日志详细程度"
        )
        
        st.session_state[f"log_level_{agent_id}"] = log_level
        
        # 添加状态信息
        st.markdown("---")
        st.markdown("**📊 当前状态**")
        
        # 显示聊天统计
        chat_history = get_chat_history(agent_id)
        if chat_history:
            user_count = len([msg for msg in chat_history if msg['role'] == 'user'])
            assistant_count = len([msg for msg in chat_history if msg['role'] == 'assistant'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("用户消息", user_count)
            with col2:
                st.metric("代理回复", assistant_count)
        
        # 快速操作按钮
        st.markdown("**⚡ 快速操作**")
        if st.button("🗑️ 清空对话", key="sidebar_clear_modern"):
            clear_chat_history(agent_id)
            st.rerun()

def render_enhanced_agent_response(agent_info: Dict, user_input: str) -> str:
    """渲染增强的代理响应，支持调试日志"""
    
    # 获取调试设置
    agent_id = agent_info['id']
    debug_key = f"debug_logs_{agent_id}"
    show_debug = st.session_state.get(debug_key, True)  # 默认开启调试模式
    
    if show_debug:
        # 调试模式：分别显示执行日志和代理响应
        st.markdown("#### 🔧 执行日志")
        debug_placeholder = st.empty()
        
        response_placeholder = st.empty()
        
        # 收集调试日志和响应
        debug_logs = []
        response_content = ""
        
        try:
            for chunk in call_agent_with_input(agent_info, user_input, show_debug_logs=True):
                # 检查是否是系统/调试信息
                if any(chunk.startswith(prefix) for prefix in [
                    "🚀", "📁", "🐍", "📜", "⚙️", "✅", "❌", "🔧", "="
                ]):
                    # 系统信息和调试日志
                    debug_logs.append(chunk)
                    debug_text = "\n".join(debug_logs[-20:])  # 显示最近20行
                    
                    # 使用code块显示日志，并在末尾添加标记来"推动"滚动到底部
                    log_with_marker = debug_text + "\n\n" + "="*30 + " 最新日志 " + "="*30
                    debug_placeholder.code(log_with_marker, language="text")
                else:
                    # 代理响应内容
                    if chunk.strip():  # 只添加非空内容
                        response_content += chunk + "\n"
                        response_placeholder.markdown(response_content)
            
            # 如果没有响应内容，显示所有输出用于调试
            if not response_content.strip():
                response_placeholder.warning("⚠️ 未检测到代理响应内容")
                if debug_logs:
                    response_placeholder.text("所有输出内容：")
                    all_output = "\n".join(debug_logs)
                    # 使用code块显示原始输出，保持滚动在底部
                    output_with_marker = all_output + "\n\n" + "="*30 + " 输出结束 " + "="*30
                    response_placeholder.code(output_with_marker, language="text")
            
            return response_content.strip()
            
        except Exception as e:
            st.error(f"执行出错: {str(e)}")
            return ""
    
    else:
        # 标准响应模式
        return render_agent_response_streaming(agent_info, user_input)