#!/usr/bin/env python3
"""
状态管理器 - 管理Streamlit会话状态
"""

import streamlit as st
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

class StateManager:
    """状态管理器类，负责管理Streamlit会话状态"""
    
    def __init__(self):
        self.session_state = st.session_state
        self.project_root = Path(__file__).parent.parent.parent
        self.sessions_dir = self.project_root / "web" / "data" / "sessions"
        self.user_sessions_dir = self.project_root / "web" / "data" / "user_sessions"
        
        # 确保会话目录存在
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.user_sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成或获取会话ID
        self._ensure_session_id()
    
    def _ensure_session_id(self):
        """确保会话有唯一ID"""
        if 'session_id' not in self.session_state:
            self.session_state['session_id'] = str(uuid.uuid4())
            self.session_state['session_created_at'] = datetime.now().isoformat()
    
    def get_session_id(self) -> str:
        """获取当前会话ID"""
        return self.session_state.get('session_id', '')
    
    def init_session_state(self):
        """初始化会话状态"""
        
        # 确保会话ID存在
        self._ensure_session_id()
        
        # 尝试从持久化存储恢复会话数据
        self._restore_session_data()
        
        # 用户信息
        if 'user_info' not in self.session_state:
            self.session_state['user_info'] = {
                'name': '张强',
                'department': '企业业务部门',
                'role': 'business_user'
            }
        
        # 当前选中的代理
        if 'selected_agent' not in self.session_state:
            self.session_state['selected_agent'] = None
        
        # 当前选中的项目
        if 'selected_project_id' not in self.session_state:
            self.session_state['selected_project_id'] = None
        
        # 当前构建任务
        if 'current_build_task' not in self.session_state:
            self.session_state['current_build_task'] = None
        
        # 选中的模板
        if 'selected_template' not in self.session_state:
            self.session_state['selected_template'] = None
        
        # 页面状态
        if 'page_state' not in self.session_state:
            self.session_state['page_state'] = {}
        
        # 通知消息
        if 'notifications' not in self.session_state:
            self.session_state['notifications'] = []
        
        # 用户偏好设置
        if 'user_preferences' not in self.session_state:
            self.session_state['user_preferences'] = {
                'auto_refresh': True,
                'refresh_interval': 5,
                'theme': 'light',
                'language': 'zh-CN'
            }
    
    def get_user_info(self) -> Dict:
        """获取用户信息"""
        return self.session_state.get('user_info', {})
    
    def set_user_info(self, user_info: Dict):
        """设置用户信息"""
        self.session_state['user_info'] = user_info
    
    def get_current_agent(self) -> Optional[str]:
        """获取当前选中的代理"""
        return self.session_state.get('selected_agent', None)
    
    def set_current_agent(self, agent_id: str):
        """设置当前选中的代理"""
        self.session_state['selected_agent'] = agent_id
        self.auto_save_session()
    
    def get_current_project(self) -> Optional[str]:
        """获取当前选中的项目"""
        return self.session_state.get('selected_project_id', None)
    
    def set_current_project(self, project_id: str):
        """设置当前选中的项目"""
        self.session_state['selected_project_id'] = project_id
        self.auto_save_session()
    
    def get_build_task(self) -> Optional[Dict]:
        """获取当前构建任务"""
        return self.session_state.get('current_build_task', None)
    
    def set_build_task(self, task_info: Dict):
        """设置构建任务信息"""
        self.session_state['current_build_task'] = task_info
    
    def clear_build_task(self):
        """清除构建任务"""
        if 'current_build_task' in self.session_state:
            del self.session_state['current_build_task']
    
    def get_selected_template(self) -> Optional[Dict]:
        """获取选中的模板"""
        return self.session_state.get('selected_template', None)
    
    def set_selected_template(self, template: Dict):
        """设置选中的模板"""
        self.session_state['selected_template'] = template
    
    def clear_selected_template(self):
        """清除选中的模板"""
        if 'selected_template' in self.session_state:
            del self.session_state['selected_template']
    
    def get_chat_history(self, agent_id: str) -> List[Dict]:
        """获取聊天历史"""
        chat_key = f"chat_history_{agent_id}"
        return self.session_state.get(chat_key, [])
    
    def add_chat_message(self, agent_id: str, message: Dict):
        """添加聊天消息"""
        chat_key = f"chat_history_{agent_id}"
        if chat_key not in self.session_state:
            self.session_state[chat_key] = []
        
        message['timestamp'] = datetime.now().isoformat()
        self.session_state[chat_key].append(message)
        self.auto_save_session()
    
    def clear_chat_history(self, agent_id: str):
        """清除聊天历史"""
        chat_key = f"chat_history_{agent_id}"
        if chat_key in self.session_state:
            self.session_state[chat_key] = []
    
    def get_page_state(self, page_name: str) -> Dict:
        """获取页面状态"""
        page_state = self.session_state.get('page_state', {})
        return page_state.get(page_name, {})
    
    def set_page_state(self, page_name: str, state: Dict):
        """设置页面状态"""
        if 'page_state' not in self.session_state:
            self.session_state['page_state'] = {}
        
        self.session_state['page_state'][page_name] = state
    
    def update_page_state(self, page_name: str, state_update: Dict):
        """更新页面状态"""
        if 'page_state' not in self.session_state:
            self.session_state['page_state'] = {}
        
        if page_name not in self.session_state['page_state']:
            self.session_state['page_state'][page_name] = {}
        
        self.session_state['page_state'][page_name].update(state_update)
    
    def add_notification(self, message: str, level: str = 'info', duration: int = 5):
        """添加通知消息"""
        notification = {
            'id': datetime.now().timestamp(),
            'message': message,
            'level': level,  # info, success, warning, error
            'timestamp': datetime.now().isoformat(),
            'duration': duration
        }
        
        if 'notifications' not in self.session_state:
            self.session_state['notifications'] = []
        
        self.session_state['notifications'].append(notification)
    
    def get_notifications(self) -> List[Dict]:
        """获取通知消息"""
        return self.session_state.get('notifications', [])
    
    def clear_notifications(self):
        """清除通知消息"""
        self.session_state['notifications'] = []
    
    def remove_notification(self, notification_id: float):
        """移除特定通知"""
        if 'notifications' in self.session_state:
            self.session_state['notifications'] = [
                n for n in self.session_state['notifications'] 
                if n['id'] != notification_id
            ]
    
    def get_user_preferences(self) -> Dict:
        """获取用户偏好设置"""
        return self.session_state.get('user_preferences', {})
    
    def update_user_preferences(self, preferences_update: Dict):
        """更新用户偏好设置"""
        if 'user_preferences' not in self.session_state:
            self.session_state['user_preferences'] = {}
        
        self.session_state['user_preferences'].update(preferences_update)
        self.auto_save_session()
    
    def is_auto_refresh_enabled(self) -> bool:
        """检查是否启用自动刷新"""
        preferences = self.get_user_preferences()
        return preferences.get('auto_refresh', True)
    
    def get_refresh_interval(self) -> int:
        """获取刷新间隔（秒）"""
        preferences = self.get_user_preferences()
        return preferences.get('refresh_interval', 5)
    
    def save_form_data(self, form_name: str, form_data: Dict):
        """保存表单数据"""
        form_key = f"form_data_{form_name}"
        self.session_state[form_key] = form_data
    
    def get_form_data(self, form_name: str) -> Dict:
        """获取表单数据"""
        form_key = f"form_data_{form_name}"
        return self.session_state.get(form_key, {})
    
    def clear_form_data(self, form_name: str):
        """清除表单数据"""
        form_key = f"form_data_{form_name}"
        if form_key in self.session_state:
            del self.session_state[form_key]
    
    def set_navigation_context(self, context: Dict):
        """设置导航上下文"""
        self.session_state['navigation_context'] = context
    
    def get_navigation_context(self) -> Dict:
        """获取导航上下文"""
        return self.session_state.get('navigation_context', {})
    
    def clear_all_temporary_data(self):
        """清除所有临时数据"""
        # 保留用户信息和偏好设置，清除其他临时数据
        keys_to_keep = ['user_info', 'user_preferences']
        keys_to_remove = [
            key for key in self.session_state.keys() 
            if key not in keys_to_keep
        ]
        
        for key in keys_to_remove:
            del self.session_state[key]
        
        # 重新初始化基本状态
        self.init_session_state()
    
    def _restore_session_data(self):
        """从持久化存储恢复会话数据"""
        try:
            session_id = self.session_state.get('session_id')
            if not session_id:
                return
            
            session_file = self.user_sessions_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                # 恢复特定的会话数据（不包括临时状态）
                restorable_keys = [
                    'user_info', 'user_preferences', 'selected_agent', 
                    'selected_project_id', 'selected_template'
                ]
                
                for key in restorable_keys:
                    if key in saved_data and key not in self.session_state:
                        self.session_state[key] = saved_data[key]
                
                # 恢复聊天历史
                for key, value in saved_data.items():
                    if key.startswith('chat_history_'):
                        self.session_state[key] = value
        
        except Exception as e:
            # 恢复失败时静默处理，不影响正常使用
            pass
    
    def save_session_data(self):
        """保存会话数据到持久化存储"""
        try:
            session_id = self.get_session_id()
            if not session_id:
                return
            
            # 准备要保存的数据
            data_to_save = {}
            
            # 保存用户相关数据
            saveable_keys = [
                'user_info', 'user_preferences', 'selected_agent',
                'selected_project_id', 'selected_template', 'session_created_at'
            ]
            
            for key in saveable_keys:
                if key in self.session_state:
                    data_to_save[key] = self.session_state[key]
            
            # 保存聊天历史
            for key, value in self.session_state.items():
                if key.startswith('chat_history_'):
                    data_to_save[key] = value
            
            # 添加保存时间戳
            data_to_save['last_saved'] = datetime.now().isoformat()
            
            # 保存到文件
            session_file = self.user_sessions_dir / f"{session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            # 保存失败时添加通知
            self.add_notification(f"会话数据保存失败: {str(e)}", "warning")
    
    def auto_save_session(self):
        """自动保存会话数据（在关键操作后调用）"""
        # 在后台自动保存，不阻塞用户操作
        try:
            self.save_session_data()
        except Exception:
            # 静默处理自动保存失败
            pass
    
    def get_session_info(self) -> Dict:
        """获取会话信息"""
        return {
            'session_id': self.get_session_id(),
            'created_at': self.session_state.get('session_created_at'),
            'user_info': self.get_user_info(),
            'active_agent': self.get_current_agent(),
            'active_project': self.get_current_project()
        }
    
    def cleanup_old_sessions(self, days_old: int = 7):
        """清理旧的会话文件"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(days=days_old)
            
            for session_file in self.user_sessions_dir.glob("*.json"):
                if session_file.stat().st_mtime < cutoff_time.timestamp():
                    session_file.unlink()
        
        except Exception as e:
            self.add_notification(f"清理旧会话失败: {str(e)}", "warning")
    
    def export_session_data(self) -> Dict:
        """导出当前会话数据"""
        return {
            'session_info': self.get_session_info(),
            'user_preferences': self.get_user_preferences(),
            'notifications': self.get_notifications(),
            'export_time': datetime.now().isoformat()
        }
    
    def debug_session_state(self) -> Dict:
        """调试：获取所有会话状态（开发用）"""
        return dict(self.session_state)