#!/usr/bin/env python3
"""
辅助函数 - 通用的工具函数
"""

import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional
import json

def setup_page_config():
    """设置页面配置"""
    
    st.set_page_config(
        page_title="Nexus-AI Platform",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/nexus-ai/help',
            'Report a bug': 'https://github.com/nexus-ai/issues',
            'About': """
            # Nexus-AI Platform
            
            让AI帮你构建AI的企业级平台
            
            **版本:** v1.0.0
            **开发:** Nexus-AI Team
            """
        }
    )

def load_custom_css():
    """加载自定义CSS样式"""
    
    css = """
    <style>
    /* 主题色彩 */
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --success-color: #4caf50;
        --warning-color: #ff9800;
        --error-color: #f44336;
        --info-color: #2196f3;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 自定义容器样式 */
    .main-container {
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    /* 卡片样式 */
    .agent-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    .agent-card:hover {
        transform: translateY(-5px);
    }
    
    /* 状态指示器 */
    .status-running {
        color: #4caf50;
        font-weight: bold;
    }
    
    .status-building {
        color: #ff9800;
        font-weight: bold;
    }
    
    .status-error {
        color: #f44336;
        font-weight: bold;
    }
    
    .status-stopped {
        color: #9e9e9e;
        font-weight: bold;
    }
    
    /* 进度条样式 */
    .progress-container {
        background: #f5f5f5;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* 聊天界面样式 */
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background: #fafafa;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* 指标卡片 */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
    }
    
    /* 响应式设计 */
    @media (max-width: 768px) {
        .agent-card {
            margin: 0.5rem 0;
            padding: 1rem;
        }
        
        .main-container {
            padding: 0.5rem;
        }
    }
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)

def show_loading_spinner(message: str = "加载中..."):
    """显示加载动画"""
    
    with st.spinner(message):
        return st.empty()

def show_success_message(message: str, duration: int = 3):
    """显示成功消息"""
    
    success_placeholder = st.success(message)
    
    # 可以添加自动消失逻辑
    return success_placeholder

def show_error_message(message: str, details: str = None):
    """显示错误消息"""
    
    st.error(message)
    
    if details:
        with st.expander("错误详情"):
            st.code(details)

def show_warning_message(message: str):
    """显示警告消息"""
    
    return st.warning(message)

def show_info_message(message: str):
    """显示信息消息"""
    
    return st.info(message)

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """格式化时间长度显示"""
    
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}分{remaining_seconds}秒"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}小时{remaining_minutes}分钟"

def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本并添加省略号"""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全的JSON解析"""
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全的JSON序列化"""
    
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default

def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    
    return Path(filename).suffix.lower()

def is_valid_email(email: str) -> bool:
    """验证邮箱格式"""
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_unique_id() -> str:
    """生成唯一ID"""
    
    import uuid
    return str(uuid.uuid4())

def get_current_timestamp() -> str:
    """获取当前时间戳"""
    
    from datetime import datetime
    return datetime.now().isoformat()

def format_timestamp(timestamp: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳显示"""
    
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except:
        return timestamp

def create_download_link(data: str, filename: str, mime_type: str = "text/plain") -> None:
    """创建下载链接"""
    
    st.download_button(
        label=f"📥 下载 {filename}",
        data=data,
        file_name=filename,
        mime=mime_type
    )

def render_status_badge(status: str, text: str = None) -> None:
    """渲染状态徽章"""
    
    if text is None:
        text = status
    
    status_colors = {
        'success': 'success',
        'running': 'success',
        'completed': 'success',
        'warning': 'warning',
        'building': 'warning',
        'pending': 'warning',
        'error': 'error',
        'failed': 'error',
        'info': 'info',
        'stopped': 'info'
    }
    
    color = status_colors.get(status.lower(), 'info')
    
    if color == 'success':
        st.success(text)
    elif color == 'warning':
        st.warning(text)
    elif color == 'error':
        st.error(text)
    else:
        st.info(text)

def create_tabs(tab_names: list) -> tuple:
    """创建标签页"""
    
    return st.tabs(tab_names)

def create_columns(ratios: list) -> tuple:
    """创建列布局"""
    
    return st.columns(ratios)

def create_expander(title: str, expanded: bool = False):
    """创建可展开区域"""
    
    return st.expander(title, expanded=expanded)

def add_vertical_space(lines: int = 1):
    """添加垂直空间"""
    
    for _ in range(lines):
        st.write("")

def render_divider():
    """渲染分隔线"""
    
    st.markdown("---")

def check_password(password: str) -> bool:
    """检查密码强度（示例）"""
    
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit

def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    
    import re
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除前后空格
    filename = filename.strip()
    # 确保不为空
    if not filename:
        filename = "untitled"
    
    return filename

def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    
    import platform
    import psutil
    
    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(),
        'memory_total': psutil.virtual_memory().total,
        'memory_available': psutil.virtual_memory().available,
        'disk_usage': psutil.disk_usage('/').percent
    }

def log_user_action(action: str, details: Dict[str, Any] = None):
    """记录用户操作（用于分析和调试）"""
    
    import logging
    
    logger = logging.getLogger('nexus_ai_frontend')
    
    log_data = {
        'action': action,
        'timestamp': get_current_timestamp(),
        'session_id': st.session_state.get('session_id', 'unknown'),
        'user': st.session_state.get('user_info', {}).get('name', 'unknown')
    }
    
    if details:
        log_data.update(details)
    
    logger.info(f"User action: {safe_json_dumps(log_data)}")

def handle_exception(e: Exception, context: str = ""):
    """统一的异常处理"""
    
    import traceback
    
    error_msg = f"发生错误: {str(e)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    
    st.error(error_msg)
    
    # 在开发模式下显示详细错误信息
    if st.session_state.get('debug_mode', False):
        with st.expander("错误详情 (调试模式)"):
            st.code(traceback.format_exc())
    
    # 记录错误日志
    import logging
    logger = logging.getLogger('nexus_ai_frontend')
    logger.error(f"Exception in {context}: {str(e)}", exc_info=True)